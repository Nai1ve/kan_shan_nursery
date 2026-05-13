"""LLM client for seed-service.

Wraps llm-service HTTP API with typed methods for seed-specific tasks.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.seed.llm_client")


class SeedLlmClient:
    """Client that calls llm-service for seed-related Agent tasks."""

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

    def answer_seed_question(
        self,
        seed: dict[str, Any],
        question: str,
        materials: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        result = self._call(
            "answer-seed-question",
            {
                "taskType": "answer-seed-question",
                "input": {
                    "seed": seed,
                    "question": question,
                    "materials": materials or [],
                    "sources": seed.get("originalSources", []),
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )
        return {
            "answer": result.get("answer", ""),
            "materialType": result.get("materials", [{}])[0].get("type", "evidence") if result.get("materials") else "evidence",
            "followUpQuestions": result.get("followUpQuestions", []),
        }

    def supplement_material(
        self,
        seed: dict[str, Any],
        material_type: str,
        existing_materials: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        result = self._call(
            "supplement-material",
            {
                "taskType": "supplement-material",
                "input": {
                    "seed": seed,
                    "materialType": material_type,
                    "existingMaterials": existing_materials or [],
                    "sources": seed.get("originalSources", []),
                },
                "promptVersion": "v1",
                "schemaVersion": "v1",
            },
        )
        return {
            "material": result.get("material", {}),
        }
