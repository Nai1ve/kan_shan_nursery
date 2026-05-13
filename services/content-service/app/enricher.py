"""LLM enrichment for content cards.

Calls llm-service to generate personalized summary, controversies,
writing angles, and recommendation reason for each card.
Uses per-interest Memory to personalize the output.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.content.enricher")


def _build_sources_payload(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Build structured sources array matching llm-service prompt format."""
    sources = []
    for src in card.get("originalSources", [])[:3]:
        sources.append({
            "sourceId": src.get("sourceId", ""),
            "sourceType": src.get("sourceType", ""),
            "title": src.get("title", ""),
            "author": src.get("author", ""),
            "rawExcerpt": src.get("rawExcerpt", "")[:500],
            "fullContent": src.get("fullContent", "")[:1200],
            "content": (src.get("fullContent") or src.get("rawExcerpt") or "")[:1200],
        })
    return sources


def _build_card_content(card: dict[str, Any]) -> str:
    parts: list[str] = []
    for source in card.get("originalSources", [])[:3]:
        text = source.get("fullContent") or source.get("rawExcerpt") or source.get("title") or ""
        if text:
            parts.append(str(text)[:1200])
    return "\n\n".join(parts)


def _build_user_profile(interest_memory: dict[str, Any] | None) -> dict[str, Any]:
    """Build userProfile object matching llm-service prompt format."""
    if not interest_memory:
        return {}
    return {
        "interests": [interest_memory.get("interestName", "")],
        "knowledgeLevel": interest_memory.get("knowledgeLevel", ""),
        "preferredPerspective": interest_memory.get("preferredPerspective", []),
        "evidencePreference": interest_memory.get("evidencePreference", ""),
        "writingStyle": interest_memory.get("writingReminder", ""),
    }


class LlmEnricher:
    def __init__(self, llm_base_url: str = "http://127.0.0.1:8080") -> None:
        self.llm_base_url = llm_base_url.rstrip("/")

    def _call_llm(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call llm-service POST /llm/tasks/{task_type}."""
        url = f"{self.llm_base_url}/llm/tasks/{task_type}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        logger.info("llm_call_start", extra={"taskType": task_type, "url": url})
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                output = result.get("data", result)
                logger.info("llm_call_ok", extra={
                    "taskType": task_type,
                    "hasOutput": bool(output),
                    "outputKeys": list(output.keys()) if isinstance(output, dict) else "non-dict",
                })
                return output
        except Exception as e:
            logger.warning("llm_call_failed", extra={"taskType": task_type, "error": str(e)})
            return {}

    def enrich_card(
        self,
        card: dict[str, Any],
        interest_memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enrich a card with LLM-generated content."""
        card_id = card.get("id", "")
        sources = card.get("originalSources", [])
        if not sources:
            logger.info("enrich_card_skip_no_sources", extra={"cardId": card_id})
            return card

        logger.info("enrich_card_start", extra={
            "cardId": card_id,
            "title": card.get("title", "")[:40],
            "sourceCount": len(sources),
            "hasMemory": interest_memory is not None,
        })

        # Build structured payloads matching llm-service prompt format
        sources_payload = _build_sources_payload(card)
        user_profile = _build_user_profile(interest_memory)

        # 1. summarize-content
        summary_result = self._call_llm("summarize-content", {
            "taskType": "summarize-content",
            "input": {
                "title": card.get("title", ""),
                "content": _build_card_content(card),
                "sources": sources_payload,
            },
        })

        # Apply summary
        summary_output = summary_result.get("output", {})
        if isinstance(summary_output, str):
            try:
                summary_output = json.loads(summary_output)
            except (json.JSONDecodeError, TypeError):
                summary_output = {}

        if summary_output.get("summary"):
            card["contentSummary"] = summary_output.get("summary")
        key_points = summary_output.get("keyPoints", [])
        if key_points:
            card["recommendationReason"] = f"来自知乎真实内容 · {'·'.join(key_points[:2])}"
            self._apply_key_points_to_sources(card, key_points)

        # 2. extract-controversies
        controversy_result = self._call_llm("extract-controversies", {
            "taskType": "extract-controversies",
            "input": {
                "title": card.get("title", ""),
                "sources": sources_payload,
            },
        })

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

        # 3. generate-writing-angles (uses controversies + userProfile)
        angles_result = self._call_llm("generate-writing-angles", {
            "taskType": "generate-writing-angles",
            "input": {
                "title": card.get("title", ""),
                "controversies": card.get("controversies", []),
                "userProfile": user_profile,
            },
        })

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

        self._ensure_real_content_fallbacks(card)

        logger.info("enrich_card_done", extra={
            "cardId": card_id,
            "summaryLen": len(card.get("contentSummary", "")),
            "controversyCount": len(card.get("controversies", [])),
            "angleCount": len(card.get("writingAngles", [])),
        })

        return card

    @staticmethod
    def _ensure_real_content_fallbacks(card: dict[str, Any]) -> None:
        sources = card.get("originalSources", [])
        snippets = []
        for source in sources[:2]:
            snippet = (
                source.get("rawExcerpt")
                or source.get("fullContent")
                or source.get("title")
                or ""
            ).strip()
            if snippet:
                snippets.append(snippet[:180])
        if not card.get("contentSummary"):
            card["contentSummary"] = "；".join(snippets) or card.get("title", "")
        if not card.get("recommendationReason"):
            source_types = [source.get("sourceType", "来源") for source in sources]
            source_label = " / ".join(list(dict.fromkeys(source_types))[:3]) or "真实来源"
            card["recommendationReason"] = f"来自 {source_label} 的真实内容，适合继续阅读和沉淀观点。"
        if not card.get("controversies"):
            title = card.get("title", "这个话题")
            card["controversies"] = [
                f"围绕“{title}”最需要先区分事实、判断和立场。",
                "这些来源是否足以支撑后续写作，仍需要用户确认。",
            ]
        if not card.get("writingAngles"):
            title = card.get("title", "这个话题")
            card["writingAngles"] = [
                f"我对“{title}”的核心判断",
                f"把“{title}”写成一篇有证据的知乎回答",
            ]

    @staticmethod
    def _apply_key_points_to_sources(card: dict[str, Any], key_points: list[Any]) -> None:
        clean_points = [str(item).strip() for item in key_points if str(item).strip()]
        if not clean_points:
            return
        sources = card.get("originalSources", [])
        summary = card.get("contentSummary") or clean_points[0]
        for index, source in enumerate(sources):
            original_excerpt = source.get("rawExcerpt", "")
            if original_excerpt and not source.get("originalExcerpt"):
                source["originalExcerpt"] = original_excerpt
            point = clean_points[index] if index < len(clean_points) else summary
            source["rawExcerpt"] = point[:220]

    def enrich_cards_batch(
        self,
        cards: list[dict[str, Any]],
        interest_memory: dict[str, Any] | None = None,
        max_cards: int = 5,
    ) -> list[dict[str, Any]]:
        """Enrich a batch of cards, limited to max_cards for cost control."""
        logger.info("enrich_batch_start", extra={"totalCards": len(cards), "maxCards": max_cards})
        enriched = []
        for card in cards[:max_cards]:
            try:
                self.enrich_card(card, interest_memory)
            except Exception as e:
                logger.warning("enrich_card_failed", extra={"cardId": card.get("id", ""), "error": str(e)})
            enriched.append(card)
        logger.info("enrich_batch_done", extra={"enrichedCount": len(enriched)})
        return enriched
