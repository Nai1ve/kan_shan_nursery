"""LLM client for feedback-service.

Wraps llm-service HTTP API with typed methods for feedback-specific tasks.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.feedback.llm_client")


class FeedbackLlmClient:
    """Client that calls llm-service for feedback-related Agent tasks."""

    def __init__(self, base_url: str | None = None) -> None:
        if base_url is None:
            base_url = os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:8080")
        self.base_url = base_url.rstrip("/")

    def _call(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/llm/tasks/{task_type}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
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
            logger.warning("llm_call_failed", extra={"taskType": task_type, "error": str(e)})
            raise

    def feedback_summary(
        self,
        article: dict[str, Any],
        metrics: dict[str, Any],
        comments: list[dict[str, Any]],
        memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._call(
            "feedback-summary",
            {
                "taskType": "feedback-summary",
                "input": {
                    "article": article,
                    "metrics": metrics,
                    "comments": comments,
                    "memory": memory or {},
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )
