"""HTTP client for calling feedback-service from writing-service."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.writing.feedback_client")


class FeedbackServiceClient:
    def __init__(self, base_url: str | None = None) -> None:
        if base_url is None:
            base_url = os.getenv("FEEDBACK_SERVICE_URL", "http://127.0.0.1:8080")
        self.base_url = base_url.rstrip("/")

    def create_from_writing_session(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.base_url}/feedback/articles/from-writing-session"
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
            logger.warning("feedback_service_call_failed", extra={"error": str(e)})
            return None
