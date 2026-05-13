"""HTTP clients for calling seed-service and profile-service."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.feedback.service_clients")


class _BaseClient:
    def __init__(self, base_url: str | None = None, env_var: str = "", default: str = "http://127.0.0.1:8080") -> None:
        if base_url is None:
            base_url = os.getenv(env_var, default)
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning("service_call_failed", extra={"url": url, "error": str(e)})
            raise


class SeedServiceClient(_BaseClient):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(base_url=base_url, env_var="SEED_SERVICE_URL", default="http://127.0.0.1:8080")

    def create_from_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create an IdeaSeed from feedback candidate. Uses /seeds/from-card pattern."""
        return self._post("/seeds/from-card", {
            "cardId": payload.get("sourceArticleId", ""),
            "reaction": "inspired",
            "userNote": payload.get("userNote", ""),
            "card": {
                "id": payload.get("sourceArticleId", ""),
                "title": payload.get("title", ""),
                "contentSummary": payload.get("coreClaim", ""),
                "writingAngles": payload.get("possibleAngles", []),
                "controversies": payload.get("counterArguments", []),
                "originalSources": [{
                    "sourceType": payload.get("sourceType", "feedback_comment"),
                    "sourceUrl": "",
                    "rawExcerpt": payload.get("coreClaim", ""),
                }],
                "tags": [payload.get("source", "历史反馈")],
            },
        })


class ProfileServiceClient(_BaseClient):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(base_url=base_url, env_var="PROFILE_SERVICE_URL", default="http://127.0.0.1:8080")

    def create_memory_update_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a memory update request in profile-service."""
        return self._post("/memory/update-requests", {
            "interestId": payload.get("interestId"),
            "targetField": payload.get("targetField", "writingReminder"),
            "suggestedValue": payload.get("suggestedValue", ""),
            "reason": payload.get("reason", ""),
        })
