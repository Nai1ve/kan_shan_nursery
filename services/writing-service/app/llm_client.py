"""LLM client for writing-service.

Wraps llm-service HTTP API with typed methods for writing-specific tasks.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.writing.llm_client")


class WritingLlmClient:
    """Client that calls llm-service for writing-related Agent tasks."""

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

    def argument_blueprint(
        self,
        seed: dict[str, Any],
        materials: list[dict[str, Any]],
        memory: dict[str, Any],
        article_type: str,
    ) -> dict[str, Any]:
        return self._call(
            "argument-blueprint",
            {
                "taskType": "argument-blueprint",
                "input": {
                    "seed": seed,
                    "materials": materials,
                    "memory": memory,
                    "articleType": article_type,
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )

    def generate_outline(
        self,
        blueprint: dict[str, Any],
        materials: list[dict[str, Any]],
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        return self._call(
            "generate-outline",
            {
                "taskType": "generate-outline",
                "input": {
                    "blueprint": blueprint,
                    "materials": materials,
                    "memory": memory,
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )

    def draft(
        self,
        seed: dict[str, Any],
        materials: list[dict[str, Any]],
        blueprint: dict[str, Any],
        memory: dict[str, Any],
        tone: str,
    ) -> dict[str, Any]:
        return self._call(
            "draft",
            {
                "taskType": "draft",
                "input": {
                    "seed": seed,
                    "materials": materials,
                    "blueprint": blueprint,
                    "memory": memory,
                    "tone": tone,
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )

    def roundtable_review(
        self,
        seed: dict[str, Any],
        draft: dict[str, Any],
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        return self._call(
            "roundtable-review",
            {
                "taskType": "roundtable-review",
                "input": {
                    "seed": seed,
                    "draft": draft,
                    "memory": memory,
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )
