"""Enrichment service for OAuth-based profile enhancement."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .models import EnrichmentJob, ProfileSignalBundle, ProfileSignalSourceItem
from .repository import EnrichmentRepository
from .transformer import (
    build_fallback_requests,
    transform_bundle_to_llm_input,
    transform_llm_output_to_requests,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _truncate_excerpt(text: str, max_len: int = 240) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


class OAuthFetchError(Exception):
    """Raised when OAuth data fetch fails."""
    pass


class LLMCallError(Exception):
    """Raised when LLM call fails."""
    pass


class EnrichmentService:
    """Service for managing profile enrichment jobs."""

    def __init__(
        self,
        repo: EnrichmentRepository,
        zhihu_adapter_url: str,
        llm_service_url: str,
        profile_service_url: str = "",
        memory_service: Any | None = None,
    ) -> None:
        self._repo = repo
        self._zhihu_adapter_url = zhihu_adapter_url.rstrip("/")
        self._llm_service_url = llm_service_url.rstrip("/")
        self._profile_service_url = profile_service_url.rstrip("/")
        self._memory_service = memory_service

    async def create_job(
        self,
        user_id: str,
        trigger: str = "oauth_bound",
        include_sources: list[str] | None = None,
    ) -> EnrichmentJob:
        """Create a new enrichment job."""
        if include_sources is None:
            include_sources = ["zhihu_user", "followed", "followers", "moments"]

        job = EnrichmentJob(
            job_id=_create_id("enrich"),
            user_id=user_id,
            status="queued",
            trigger=trigger,
            include_sources=include_sources,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        return await self._repo.create_job(job)

    async def get_latest_job(self, user_id: str) -> Optional[EnrichmentJob]:
        """Get the latest enrichment job for a user."""
        return await self._repo.get_latest_job(user_id)

    async def get_job(self, job_id: str) -> Optional[EnrichmentJob]:
        """Get a job by ID."""
        return await self._repo.get_job(job_id)

    async def run_enrichment(
        self,
        job_id: str,
        access_token: str,
        profile: dict[str, Any],
        existing_memory: dict[str, Any],
        interest_catalog: list[dict[str, Any]],
    ) -> EnrichmentJob:
        """Execute the enrichment job.

        Args:
            job_id: The job ID to execute
            access_token: Zhihu OAuth access token
            profile: User profile data
            existing_memory: Current globalMemory and interestMemories
            interest_catalog: Available interest categories

        Returns:
            Updated job
        """
        job = await self._repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Update status to running
        job.status = "running"
        job.updated_at = _now_iso()
        await self._repo.update_job(job)

        try:
            # Step 1: Collect OAuth signals
            oauth_signals = await self._collect_oauth_signals(
                access_token, job.include_sources
            )
            job.signal_counts = {
                source: len([s for s in oauth_signals if s.source_type == source])
                for source in job.include_sources
            }

            # Step 2: Build signal bundle
            bundle = self._build_signal_bundle(
                job.user_id, profile, oauth_signals
            )

            # Step 3: Call LLM synthesis
            try:
                llm_output = await self._call_llm_synthesis(
                    bundle, existing_memory, interest_catalog, profile
                )
            except LLMCallError:
                # Fallback: use rule-based approach
                logger.warning(f"LLM call failed for job {job_id}, using fallback")
                llm_output = None

            # Step 4: Create memory update requests
            if llm_output:
                requests = transform_llm_output_to_requests(
                    llm_output, job.user_id, existing_memory
                )
            else:
                # Fallback: generate basic requests
                requests = build_fallback_requests(
                    job.user_id, profile, interest_catalog
                )
                job.status = "fallback"

            # Step 5: Save requests (via API call to profile-service)
            request_ids = []
            for req in requests:
                try:
                    req_id = await self._save_memory_update_request(req)
                    request_ids.append(req_id)
                except Exception as e:
                    logger.error(f"Failed to save request: {e}")

            job.memory_update_request_ids = request_ids
            if job.status != "fallback":
                job.status = "completed"
            job.updated_at = _now_iso()
            await self._repo.update_job(job)

        except OAuthFetchError as e:
            logger.error(f"OAuth fetch failed for job {job_id}: {e}")
            job.status = "fallback"
            job.error_message = str(e)
            job.updated_at = _now_iso()
            await self._repo.update_job(job)

        except Exception as e:
            logger.error(f"Enrichment job {job_id} failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = _now_iso()
            await self._repo.update_job(job)

        return job

    async def _collect_oauth_signals(
        self,
        access_token: str,
        include_sources: list[str],
    ) -> list[ProfileSignalSourceItem]:
        """Collect signals from zhihu-adapter OAuth APIs."""
        signals = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch user info
            if "zhihu_user" in include_sources:
                try:
                    user_info = await self._fetch_zhihu_user(client, access_token)
                    if user_info:
                        signals.append(user_info)
                except Exception as e:
                    logger.error(f"Failed to fetch zhihu user: {e}")

            # Fetch followed users
            if "followed" in include_sources:
                try:
                    followed = await self._fetch_zhihu_followed(client, access_token)
                    signals.extend(followed)
                except Exception as e:
                    logger.error(f"Failed to fetch followed: {e}")

            # Fetch followers
            if "followers" in include_sources:
                try:
                    followers = await self._fetch_zhihu_followers(client, access_token)
                    signals.extend(followers)
                except Exception as e:
                    logger.error(f"Failed to fetch followers: {e}")

            # Fetch moments
            if "moments" in include_sources:
                try:
                    moments = await self._fetch_zhihu_moments(client, access_token)
                    signals.extend(moments)
                except Exception as e:
                    logger.error(f"Failed to fetch moments: {e}")

        return signals

    async def _fetch_zhihu_user(
        self, client: httpx.AsyncClient, access_token: str
    ) -> Optional[ProfileSignalSourceItem]:
        """Fetch zhihu user info."""
        resp = await client.get(
            f"{self._zhihu_adapter_url}/zhihu/user",
            params={"access_token": access_token},
        )
        if resp.status_code != 200:
            raise OAuthFetchError(f"Failed to fetch user: {resp.status_code}")

        data = resp.json()
        data = self._unwrap_adapter_single(data)
        return ProfileSignalSourceItem(
            evidence_id=_create_id("ev"),
            source_type="zhihu_user",
            source_id=data.get("uid", ""),
            author_name=data.get("fullname", ""),
            headline=data.get("headline", ""),
            excerpt=_truncate_excerpt(data.get("description", "")),
            confidence_hint=0.9,
        )

    async def _fetch_zhihu_followed(
        self, client: httpx.AsyncClient, access_token: str, limit: int = 30
    ) -> list[ProfileSignalSourceItem]:
        """Fetch zhihu followed users."""
        resp = await client.get(
            f"{self._zhihu_adapter_url}/zhihu/user-followed",
            params={"access_token": access_token, "per_page": limit},
        )
        if resp.status_code != 200:
            raise OAuthFetchError(f"Failed to fetch followed: {resp.status_code}")

        data = resp.json()
        items = self._unwrap_adapter_items(data)
        return [
            ProfileSignalSourceItem(
                evidence_id=_create_id("ev"),
                source_type="followed",
                source_id=item.get("uid", ""),
                author_name=item.get("fullname", ""),
                headline=item.get("headline", ""),
                excerpt=_truncate_excerpt(item.get("description", "")),
                confidence_hint=0.5,
            )
            for item in items[:limit]
        ]

    async def _fetch_zhihu_followers(
        self, client: httpx.AsyncClient, access_token: str, limit: int = 30
    ) -> list[ProfileSignalSourceItem]:
        """Fetch zhihu followers."""
        resp = await client.get(
            f"{self._zhihu_adapter_url}/zhihu/user-followers",
            params={"access_token": access_token, "per_page": limit},
        )
        if resp.status_code != 200:
            raise OAuthFetchError(f"Failed to fetch followers: {resp.status_code}")

        data = resp.json()
        items = self._unwrap_adapter_items(data)
        return [
            ProfileSignalSourceItem(
                evidence_id=_create_id("ev"),
                source_type="followers",
                source_id=item.get("uid", ""),
                author_name=item.get("fullname", ""),
                headline=item.get("headline", ""),
                excerpt=_truncate_excerpt(item.get("description", "")),
                confidence_hint=0.3,
            )
            for item in items[:limit]
        ]

    async def _fetch_zhihu_moments(
        self, client: httpx.AsyncClient, access_token: str, limit: int = 20
    ) -> list[ProfileSignalSourceItem]:
        """Fetch zhihu moments (following feed)."""
        resp = await client.get(
            f"{self._zhihu_adapter_url}/zhihu/following-feed",
            params={"access_token": access_token},
        )
        if resp.status_code != 200:
            raise OAuthFetchError(f"Failed to fetch moments: {resp.status_code}")

        data = resp.json()
        items = self._unwrap_adapter_items(data)
        return [
            ProfileSignalSourceItem(
                evidence_id=_create_id("ev"),
                source_type="moments",
                source_id=item.get("sourceId", ""),
                title=item.get("title", ""),
                excerpt=_truncate_excerpt(item.get("summary", "")),
                author_name=item.get("author", ""),
                action_text=item.get("contentType", ""),
                published_at=item.get("publishedAt", ""),
                confidence_hint=0.7,
            )
            for item in items[:limit]
        ]

    def _build_signal_bundle(
        self,
        user_id: str,
        profile: dict[str, Any],
        oauth_signals: list[ProfileSignalSourceItem],
    ) -> ProfileSignalBundle:
        """Build signal bundle from profile and OAuth signals."""
        # Extract onboarding data from profile
        interests = profile.get("interests", [])
        selected_interest_ids = [
            i.get("interestId", "") if isinstance(i, dict) else i
            for i in interests
        ]

        onboarding = {
            "selectedInterestIds": selected_interest_ids,
            "writingStyleAnswers": profile.get("writingStyle", {}),
            "selfDescription": profile.get("role", ""),
        }

        return ProfileSignalBundle(
            user_id=user_id,
            generated_at=_now_iso(),
            onboarding=onboarding,
            signals=oauth_signals,
        )

    async def _call_llm_synthesis(
        self,
        bundle: ProfileSignalBundle,
        existing_memory: dict[str, Any],
        interest_catalog: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        """Call llm-service for profile memory synthesis."""
        # Transform bundle to LLM input format
        llm_input = transform_bundle_to_llm_input(
            bundle, existing_memory, interest_catalog, profile
        )

        # Call llm-service
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._llm_service_url}/llm/tasks/profile-memory-synthesis",
                json={
                    "taskType": "profile-memory-synthesis",
                    "input": llm_input,
                    "promptVersion": "v1",
                    "schemaVersion": "v1",
                },
            )

            if resp.status_code != 200:
                raise LLMCallError(f"LLM call failed: {resp.status_code} {resp.text}")

            data = resp.json()
            result = data.get("output") or data.get("result") or data

            # Validate output
            if "globalMemory" not in result or "interestMemories" not in result:
                raise LLMCallError("LLM output missing required fields")

            return result

    async def _save_memory_update_request(self, request: dict[str, Any]) -> str:
        """Save a memory update request via profile-service API."""
        if self._memory_service is not None:
            saved = self._memory_service.create_update_request(
                request,
                user_id=request.get("userId"),
            )
            return saved.get("id", request["id"])

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._profile_service_url}/memory/update-requests",
                json=request,
            )
            if resp.status_code != 200:
                raise Exception(f"Failed to save request: {resp.status_code}")

            data = resp.json()
            return data.get("id", request["id"])

    def _unwrap_adapter_items(self, data: Any) -> list[dict[str, Any]]:
        """Normalize zhihu-adapter list envelopes.

        zhihu-adapter consistently returns {"items": [...], "cache": ..., "quota": ...},
        while older experiments used raw arrays or {"data": [...]}. Supporting all
        three keeps enrichment compatible with both mock tests and live adapter.
        """
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []
        items = data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        legacy = data.get("data")
        if isinstance(legacy, list):
            return [item for item in legacy if isinstance(item, dict)]
        return []

    def _unwrap_adapter_single(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list) and items:
                first = items[0]
                return first if isinstance(first, dict) else {}
            return data
        return {}
