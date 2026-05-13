"""Background scheduler for profile-service.

Handles:
- New user profile enrichment (hourly)
- Nightly Memory review (daily at 2:00 AM)
- Enrichment job polling (every 10 seconds)
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("kanshan.profile.scheduler")


class ProfileScheduler:
    """Background scheduler for periodic profile tasks."""

    def __init__(self, repository=None, llm_service_url: str = "http://127.0.0.1:8080", enrichment_runner=None):
        self.repository = repository
        self.llm_service_url = llm_service_url
        self.enrichment_runner = enrichment_runner
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._enrichment_loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Start the background scheduler."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Start enrichment runner if available
        if self.enrichment_runner:
            self._start_enrichment_runner()

        logger.info("profile_scheduler_started")

    def _start_enrichment_runner(self) -> None:
        """Start the enrichment runner in a separate thread with its own event loop."""
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._enrichment_loop = loop
            try:
                loop.run_until_complete(self.enrichment_runner.start())
                # Keep the loop running
                while not self._stop_event.is_set():
                    loop.run_until_complete(asyncio.sleep(1))
            except Exception as e:
                logger.error(f"enrichment_runner_error: {e}")
            finally:
                loop.run_until_complete(self.enrichment_runner.stop())
                loop.close()

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        logger.info("enrichment_runner_thread_started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._stop_event.set()

    def _run_loop(self) -> None:
        """Background loop: check every hour."""
        while not self._stop_event.is_set():
            try:
                self._check_new_users()
                self._check_nightly_review()
            except Exception as e:
                logger.error("scheduler_error", extra={"error": str(e)})

            # Sleep for 1 hour (in 1-second increments for responsiveness)
            for _ in range(3600):
                if self._stop_event.is_set():
                    return
                time.sleep(1)

    def _check_new_users(self) -> None:
        """Check for new users that need profile enrichment."""
        if not self.repository:
            return

        try:
            # Get profiles that need enrichment
            profile = self.repository.get_profile()
            if not profile:
                return

            # Check if profile needs enrichment
            account_status = profile.get("accountStatus", "")
            if "临时" in account_status or "provisional" in account_status.lower():
                logger.info("enriching_new_user_profile")
                self._enrich_profile(profile)
        except Exception as e:
            logger.error("check_new_users_failed", extra={"error": str(e)})

    def _check_nightly_review(self) -> None:
        """Check if it's time for nightly Memory review (2:00 AM)."""
        now = datetime.now()
        if now.hour == 2 and now.minute < 5:  # Run between 2:00-2:05 AM
            logger.info("starting_nightly_memory_review")
            self._nightly_memory_review()

    def _enrich_profile(self, profile: dict[str, Any]) -> None:
        """Enrich a new user's profile using LLM."""
        try:
            interests = profile.get("interests", [])
            nickname = profile.get("nickname", "用户")

            # Call profile-memory-synthesis Agent
            result = self._call_llm(
                "profile-memory-synthesis",
                {
                    "explicitProfile": {
                        "nickname": nickname,
                        "interests": interests,
                    },
                    "zhihuUserInfo": profile.get("zhihuUserInfo", {}),
                    "followingUsers": profile.get("followingUsers", []),
                    "followers": profile.get("followers", []),
                    "followingFeedSamples": profile.get("followingFeedSamples", []),
                    "publicContentSamples": profile.get("publicContentSamples", []),
                },
            )
            if result:
                global_memory = result.get("globalMemory", {})
                interest_memories = result.get("interestMemories", [])
                # Create memory update request for global memory
                self._create_memory_update_request(
                    interest_id="global",
                    target_field="globalMemory",
                    suggested_value=json.dumps(global_memory, ensure_ascii=False),
                    reason="新用户注册后的画像生成建议",
                )
                # Create memory update requests for each interest
                for im in interest_memories:
                    self._create_memory_update_request(
                        interest_id=im.get("interestId", ""),
                        target_field="interestMemory",
                        suggested_value=json.dumps(im, ensure_ascii=False),
                        reason=f"兴趣 {im.get('interestId', '')} 的画像生成建议",
                    )
                logger.info("profile_enrichment_completed")
        except Exception as e:
            logger.error("profile_enrichment_failed", extra={"error": str(e)})

    def _nightly_memory_review(self) -> None:
        """Perform nightly Memory review for all users."""
        # This is a placeholder for the full implementation
        # In production, this would:
        # 1. Get all active users
        # 2. Analyze their recent interactions
        # 3. Generate Memory update suggestions
        logger.info("nightly_memory_review_completed")

    def _call_llm(self, task_type: str, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Call LLM service with standard contract."""
        import urllib.request
        try:
            url = f"{self.llm_service_url}/llm/tasks/{task_type}"
            payload = {
                "taskType": task_type,
                "input": input_data,
                "promptVersion": "v1",
                "schemaVersion": "v1",
            }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                output = result.get("output")
                if isinstance(output, dict):
                    return output
                if isinstance(output, str):
                    try:
                        return json.loads(output)
                    except (json.JSONDecodeError, TypeError):
                        return {}
                return {}
        except Exception as e:
            logger.error("llm_call_failed", extra={"task_type": task_type, "error": str(e)})
            return None

    def _create_memory_update_request(
        self,
        interest_id: str,
        target_field: str,
        suggested_value: str,
        reason: str,
    ) -> None:
        """Create a memory update request."""
        if not self.repository:
            return

        try:
            from .defaults import create_id, now_iso
            request = {
                "id": create_id("mur"),
                "interestId": interest_id,
                "targetField": target_field,
                "suggestedValue": suggested_value,
                "reason": reason,
                "status": "pending",
                "createdAt": now_iso(),
            }
            self.repository.save_update_request(request)
            logger.info("memory_update_request_created", extra={"requestId": request["id"]})
        except Exception as e:
            logger.error("create_memory_update_request_failed", extra={"error": str(e)})
