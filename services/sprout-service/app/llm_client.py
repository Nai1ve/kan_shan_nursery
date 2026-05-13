"""LLM client for sprout-service.

Wraps llm-service HTTP API with typed methods for sprout-specific tasks.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.sprout.llm_client")


class SproutLlmClient:
    """Client that calls llm-service for sprout-related Agent tasks."""

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

    def sprout_opportunities(
        self,
        candidates: list[dict[str, Any]],
        memory: dict[str, Any] | None = None,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """Call sprout-opportunities Agent with batched candidates.

        Each candidate: {seed, triggerCards, scoreSignals}
        Returns list of normalized SproutOpportunity dicts.
        """
        try:
            result = self._call(
                "sprout-opportunities",
                {
                    "taskType": "sprout-opportunities",
                    "input": {
                        "candidates": [
                            {
                                "seed": c.get("seed", {}),
                                "triggerCards": c.get("triggerCards", []),
                                "scoreSignals": c.get("scoreSignals", {}),
                            }
                            for c in candidates
                        ],
                        "memory": memory or {},
                        "limit": limit,
                    },
                    "promptVersion": "v1",
                    "schemaVersion": "v1",
                },
            )
            return result.get("opportunities", [])
        except Exception as e:
            logger.warning("sprout_opportunities_batch_failed", extra={"error": str(e)})
            return []

    def supplement_material(
        self,
        seed: dict[str, Any],
        material_type: str = "evidence",
        existing_materials: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call supplement-material Agent to generate evidence or counterargument."""
        try:
            result = self._call(
                "supplement-material",
                {
                    "taskType": "supplement-material",
                    "input": {
                        "seed": seed,
                        "materialType": material_type,
                        "existingMaterials": existing_materials or [],
                    },
                    "promptVersion": "v1",
                    "schemaVersion": "v1",
                },
            )
            return result.get("material", {})
        except Exception as e:
            logger.warning("supplement_material_failed", extra={"error": str(e)})
            return {}

    def switch_angle(
        self,
        opportunity: dict[str, Any],
    ) -> dict[str, Any]:
        """Call switch-sprout-angle Agent to generate a new writing angle."""
        try:
            result = self._call(
                "switch-sprout-angle",
                {
                    "taskType": "switch-sprout-angle",
                    "input": {
                        "seed": opportunity,
                    },
                    "promptVersion": "v1",
                    "schemaVersion": "v1",
                },
            )
            return result
        except Exception as e:
            logger.warning("switch_angle_failed", extra={"error": str(e)})
            return {}
