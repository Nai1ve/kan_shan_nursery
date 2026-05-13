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
        seeds: list[dict[str, Any]],
        memory: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Call sprout-opportunities Agent and return normalized opportunity list."""
        opportunities: list[dict[str, Any]] = []
        for seed in seeds:
            try:
                result = self._call(
                    "sprout-opportunities",
                    {
                        "taskType": "sprout-opportunities",
                        "input": {
                            "seed": seed,
                            "seedMaterials": seed.get("wateringMaterials", []),
                            "questions": seed.get("questions", []),
                            "memory": memory or {},
                            "triggerTopics": seed.get("triggerTopics", []),
                            "deterministicScores": {
                                "maturityScore": seed.get("maturityScore", 0),
                                "adoptedMaterials": len(
                                    [m for m in seed.get("wateringMaterials", []) if m.get("adopted")]
                                ),
                            },
                        },
                        "promptVersion": "v1",
                        "schemaVersion": "v1",
                    },
                )
                for opp in result.get("opportunities", []):
                    opportunities.append({
                        "id": f"sprout-{seed.get('id', 'unknown')}-{len(opportunities)}",
                        "seedId": seed.get("id", ""),
                        "interestId": seed.get("interestId", ""),
                        "score": opp.get("fitScore", 70),
                        "tags": [
                            {"label": f"发芽指数 {opp.get('fitScore', 70)}", "tone": "blue"},
                        ],
                        "activatedSeed": opp.get("triggerTopic", seed.get("coreClaim", "")),
                        "triggerTopic": opp.get("triggerTopic", ""),
                        "whyWorthWriting": opp.get("whyWorthWriting", ""),
                        "suggestedTitle": opp.get("suggestedTitle", ""),
                        "suggestedAngle": opp.get("suggestedAngle", ""),
                        "suggestedMaterials": opp.get("suggestedMaterials", ""),
                        "materialGaps": opp.get("materialGaps", []),
                        "riskWarnings": opp.get("riskWarnings", []),
                        "status": "new",
                    })
            except Exception as e:
                logger.warning("sprout_opportunity_failed", extra={"seedId": seed.get("id"), "error": str(e)})
        return opportunities
