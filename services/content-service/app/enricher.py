"""LLM enrichment for content cards.

Calls llm-service to generate personalized summary, controversies,
writing angles, and recommendation reason for each card.
Uses per-interest Memory to personalize the output.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.content.enricher")


class LlmEnricher:
    def __init__(self, llm_base_url: str = "http://127.0.0.1:8080") -> None:
        self.llm_base_url = llm_base_url.rstrip("/")

    def _call_llm(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call llm-service POST /llm/tasks/{task_type}."""
        url = f"{self.llm_base_url}/llm/tasks/{task_type}"
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
                return result.get("data", result)
        except Exception as e:
            logger.warning("llm_call_failed", extra={"taskType": task_type, "error": str(e)})
            return {}

    def enrich_card(
        self,
        card: dict[str, Any],
        interest_memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enrich a card with LLM-generated content.

        Args:
            card: The WorthReadingCard to enrich
            interest_memory: Per-interest memory for personalization

        Returns:
            The enriched card (modified in place and returned)
        """
        sources = card.get("originalSources", [])
        if not sources:
            return card

        # Build context from sources
        source_texts = []
        for i, src in enumerate(sources[:3], 1):
            source_texts.append(
                f"来源{i}: {src.get('title', '')}\n"
                f"类型: {src.get('sourceType', '')}\n"
                f"作者: {src.get('author', '未知')}\n"
                f"摘要: {src.get('rawExcerpt', '')[:300]}"
            )
        sources_context = "\n\n".join(source_texts)

        # Build memory context
        memory_context = ""
        if interest_memory:
            memory_context = (
                f"\n用户画像:\n"
                f"- 兴趣领域: {interest_memory.get('interestName', '')}\n"
                f"- 知识水平: {interest_memory.get('knowledgeLevel', '')}\n"
                f"- 偏好视角: {', '.join(interest_memory.get('preferredPerspective', []))}\n"
                f"- 证据偏好: {interest_memory.get('evidencePreference', '')}\n"
                f"- 写作提醒: {interest_memory.get('writingReminder', '')}"
            )

        # Call LLM for content summary
        summary_result = self._call_llm("summarize-content", {
            "taskType": "summarize-content",
            "input": {
                "title": card.get("title", ""),
                "sources": sources_context,
                "memory": memory_context,
            },
        })

        # Call LLM for controversies
        controversy_result = self._call_llm("extract-controversies", {
            "taskType": "extract-controversies",
            "input": {
                "title": card.get("title", ""),
                "sources": sources_context,
            },
        })

        # Call LLM for writing angles
        angles_result = self._call_llm("generate-writing-angles", {
            "taskType": "generate-writing-angles",
            "input": {
                "title": card.get("title", ""),
                "sources": sources_context,
                "memory": memory_context,
            },
        })

        # Apply summary
        summary_output = summary_result.get("output", {})
        if isinstance(summary_output, str):
            try:
                summary_output = json.loads(summary_output)
            except (json.JSONDecodeError, TypeError):
                summary_output = {}

        card["contentSummary"] = summary_output.get("summary", card.get("contentSummary", ""))
        card["recommendationReason"] = (
            f"来自知乎 {'·'.join(summary_output.get('keyPoints', [])[:2])}"
            if summary_output.get("keyPoints")
            else card.get("recommendationReason", "")
        )

        # Apply controversies
        controversy_output = controversy_result.get("output", {})
        if isinstance(controversy_output, str):
            try:
                controversy_output = json.loads(controversy_output)
            except (json.JSONDecodeError, TypeError):
                controversy_output = {}

        raw_controversies = controversy_output.get("controversies", [])
        if raw_controversies and isinstance(raw_controversies[0], dict):
            card["controversies"] = [c.get("claim", str(c)) for c in raw_controversies[:3]]
        elif raw_controversies:
            card["controversies"] = raw_controversies[:3]

        # Apply writing angles
        angles_output = angles_result.get("output", {})
        if isinstance(angles_output, str):
            try:
                angles_output = json.loads(angles_output)
            except (json.JSONDecodeError, TypeError):
                angles_output = {}

        raw_angles = angles_output.get("angles", [])
        if raw_angles and isinstance(raw_angles[0], dict):
            card["writingAngles"] = [a.get("angle", str(a)) for a in raw_angles[:3]]
        elif raw_angles:
            card["writingAngles"] = raw_angles[:3]

        return card

    def enrich_cards_batch(
        self,
        cards: list[dict[str, Any]],
        interest_memory: dict[str, Any] | None = None,
        max_cards: int = 5,
    ) -> list[dict[str, Any]]:
        """Enrich a batch of cards, limited to max_cards for cost control."""
        enriched = []
        for card in cards[:max_cards]:
            try:
                self.enrich_card(card, interest_memory)
            except Exception as e:
                logger.warning("enrich_card_failed", extra={"cardId": card.get("id", ""), "error": str(e)})
            enriched.append(card)
        return enriched
