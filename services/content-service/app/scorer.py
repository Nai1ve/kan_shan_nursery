"""Card scoring and selection.

Implements the 7-dimension card scoring formula from the product spec,
and selects top N cards per category for display.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kanshan.content.scorer")


def _tag_label(tag: Any) -> str:
    if isinstance(tag, dict):
        return str(tag.get("label", ""))
    return str(tag or "")


def score_card(card: dict[str, Any], interest_memory: dict[str, Any] | None = None) -> float:
    """Score a card across multiple dimensions.

    Formula:
        relevanceScore =
            interestFit: 35%
          + sourceQuality: 20%
          + freshness: 15%
          + controversy: 10%
          + writingPotential: 10%
          + memoryFit: 5%
          + diversityGain: 5%

    Returns a score between 0-100.
    """
    # Interest fit: based on relevanceScore from search
    interest_fit = min(100, card.get("relevanceScore", 50)) * 0.35

    # Source quality: based on authority score and number of sources
    authority = card.get("authorityScore", 60)
    source_count = len(card.get("originalSources", []))
    source_quality = (authority * 0.7 + min(100, source_count * 30) * 0.3) * 0.20

    # Freshness: based on popularity (likes, comments)
    popularity = card.get("popularityScore", 0)
    freshness = min(100, 50 + popularity // 100) * 0.15

    # Controversy: higher controversy = more writable
    controversy = card.get("controversyScore", 0)
    controversies = card.get("controversies", [])
    controversy_score = min(100, controversy + len(controversies) * 20) * 0.10

    # Writing potential: based on number of writing angles
    angles = card.get("writingAngles", [])
    writing_potential = min(100, len(angles) * 25) * 0.10

    # Memory fit: how well the card matches user's per-interest memory
    memory_fit = 50.0  # Default neutral
    if interest_memory:
        # Boost if card tags match preferred perspectives
        perspectives = set(interest_memory.get("preferredPerspective", []))
        tags = {_tag_label(tag) for tag in card.get("tags", [])}
        overlap = len(perspectives & tags)
        memory_fit = min(100, 50 + overlap * 20)
    memory_fit *= 0.05

    # Diversity gain: slight boost for cards with unique source types
    source_types = set(src.get("sourceType", "") for src in card.get("originalSources", []))
    diversity = min(100, len(source_types) * 40) * 0.05

    total = interest_fit + source_quality + freshness + controversy_score + writing_potential + memory_fit + diversity
    return round(total, 1)


def select_top_cards(
    cards: list[dict[str, Any]],
    interest_memory: dict[str, Any] | None = None,
    max_cards: int = 5,
) -> list[dict[str, Any]]:
    """Score and select top N cards for display."""
    logger.info("scorer_select_top", extra={
        "inputCount": len(cards),
        "maxCards": max_cards,
        "hasMemory": interest_memory is not None,
    })

    for card in cards:
        card["_score"] = score_card(card, interest_memory)

    # Sort by score descending
    ranked = sorted(cards, key=lambda c: c.get("_score", 0), reverse=True)

    # Deduplicate by sourceId
    seen_sources: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for card in ranked:
        card_sources = set()
        for src in card.get("originalSources", []):
            sid = src.get("sourceId", "")
            if sid:
                card_sources.add(sid)
        # Skip if all sources already seen
        if card_sources and card_sources.issubset(seen_sources):
            continue
        seen_sources.update(card_sources)
        deduped.append(card)

    # Remove internal score field and return top N
    result = deduped[:max_cards]
    for card in result:
        card.pop("_score", None)

    logger.info("scorer_select_done", extra={
        "inputCount": len(cards),
        "dedupedCount": len(deduped),
        "outputCount": len(result),
        "topScores": [round(c.get("_score", 0), 1) for c in ranked[:max_cards]],
        "topTitles": [c.get("title", "")[:30] for c in ranked[:max_cards]],
    })

    return result
