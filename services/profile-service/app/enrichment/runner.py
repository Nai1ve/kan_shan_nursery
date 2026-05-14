"""Runner for enrichment jobs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .repository import EnrichmentRepository
from .service import EnrichmentService

logger = logging.getLogger(__name__)


class EnrichmentRunner:
    """Runner that polls and executes enrichment jobs."""

    def __init__(
        self,
        repo: EnrichmentRepository,
        enrichment_service: EnrichmentService,
        profile_repo: Any,
        auth_repo: Any,
        poll_interval: float = 10.0,
    ) -> None:
        self._repo = repo
        self._service = enrichment_service
        self._profile_repo = profile_repo
        self._auth_repo = auth_repo
        self._poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the poller."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("enrichment_runner_started")

    async def stop(self) -> None:
        """Stop the poller."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("enrichment_runner_stopped")

    async def _poll_loop(self) -> None:
        """Main poll loop."""
        while self._running:
            try:
                await self._process_queued_jobs()
            except Exception as e:
                logger.error(f"enrichment_poll_error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _process_queued_jobs(self) -> None:
        """Process all queued jobs."""
        jobs = await self._repo.get_queued_jobs()
        for job in jobs:
            try:
                await self._execute_job(job.job_id)
            except Exception as e:
                logger.error(f"enrichment_job_execute_error: {job.job_id} {e}")

    async def _execute_job(self, job_id: str) -> None:
        """Execute a single enrichment job."""
        job = await self._repo.get_job(job_id)
        if not job or job.status != "queued":
            return

        logger.info(f"executing_enrichment_job: {job_id}")

        # Get access token from zhihu bindings
        access_token = await self._get_access_token(job.user_id)
        if not access_token:
            logger.warning(f"no_access_token_for_user: {job.user_id}")
            # Mark as fallback - can still use onboarding data
            job.status = "fallback"
            job.error_message = "No zhihu access token found"
            from datetime import datetime, timezone
            job.updated_at = datetime.now(timezone.utc).isoformat()
            await self._repo.update_job(job)
            return

        # Get profile and memory
        profile = self._profile_repo.get_profile(job.user_id)
        existing_memory = {
            "globalMemory": profile.get("globalMemory", {}),
            "interestMemories": profile.get("interestMemories", []),
        }
        interest_catalog = profile.get("interests", [])

        # Run enrichment
        await self._service.run_enrichment(
            job_id=job_id,
            access_token=access_token,
            profile=profile,
            existing_memory=existing_memory,
            interest_catalog=interest_catalog,
        )

    async def _get_access_token(self, user_id: str) -> str | None:
        """Get zhihu access token for user."""
        try:
            # Try to get from auth repository
            binding = self._auth_repo.get_zhihu_binding(user_id)
            if not binding:
                return None
            if isinstance(binding, dict):
                return binding.get("access_token") or binding.get("accessToken")
            return getattr(binding, "access_token", None)
        except Exception as e:
            logger.error(f"get_access_token_error: {e}")
        return None
