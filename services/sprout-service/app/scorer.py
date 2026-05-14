"""Activation scoring algorithm for Today's Sprout.

Pure functions — no external dependencies.
Each factor returns a float in [0.0, 1.0]. Total is clamped to [0, 100].
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone

# Weight constants
WEIGHT_MATURITY = 0.25
WEIGHT_RELATEDNESS = 0.25
WEIGHT_FRESHNESS = 0.20
WEIGHT_INFO_GAIN = 0.15
WEIGHT_MEMORY_FIT = 0.10
WEIGHT_CONTROVERSY = 0.05


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Individual factor scorers
# ---------------------------------------------------------------------------

def score_seed_maturity(seed: dict) -> float:
    """maturityScore / 100, clamped to [0, 1]."""
    try:
        return _clamp(int(seed.get("maturityScore", 0)) / 100)
    except (ValueError, TypeError):
        return 0.0


def _extract_bigrams(text: str) -> set[str]:
    """Extract Chinese character bigrams from text for similarity comparison."""
    # Remove punctuation, whitespace, and non-CJK characters
    cleaned = re.sub(r"[^一-鿿㐀-䶿]", "", text)
    if len(cleaned) < 2:
        return set(cleaned) if cleaned else set()
    return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)} | set(cleaned)


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def score_topic_relatedness(
    seed: dict,
    hot_cards: list[dict],
    today_cards: list[dict],
) -> tuple[float, list[str], str]:
    """Keyword overlap between seed and card titles using bigram Jaccard.

    Returns (score, bestTriggerCards, triggerType).
    """
    seed_parts = [
        seed.get("title", ""),
        seed.get("coreClaim", ""),
        seed.get("sourceTitle", ""),
    ]
    for m in (seed.get("wateringMaterials") or []):
        seed_parts.append(m.get("title", ""))
    seed_text = "".join(seed_parts)
    seed_bigrams = _extract_bigrams(seed_text)

    if not seed_bigrams:
        return 0.0, [], "hot"

    best_score = 0.0
    best_cards: list[str] = []
    best_type = "hot"

    for card in hot_cards:
        card_bigrams = _extract_bigrams(card.get("title", ""))
        sim = _jaccard(seed_bigrams, card_bigrams)
        if sim > best_score:
            best_score = sim
            best_cards = [card.get("id", "")]
            best_type = "hot"
        elif sim == best_score and sim > 0:
            best_cards.append(card.get("id", ""))

    for card in today_cards:
        card_bigrams = _extract_bigrams(card.get("title", ""))
        sim = _jaccard(seed_bigrams, card_bigrams)
        if sim > best_score:
            best_score = sim
            best_cards = [card.get("id", "") for _ in [1]]  # reset
            best_type = "today_card"
        elif sim == best_score and sim > 0:
            best_cards.append(card.get("id", ""))

    return _clamp(best_score), best_cards, best_type


def score_freshness(cards: list[dict]) -> float:
    """Freshness based on card timestamps. Hot/today cards default to high."""
    if not cards:
        return 0.5
    now = datetime.now(timezone.utc)
    max_score = 0.0
    for card in cards:
        created = card.get("createdAt")
        if not created:
            max_score = max(max_score, 0.7)
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (now - dt).total_seconds() / 86400
            if age_days <= 1:
                s = 1.0
            elif age_days <= 3:
                s = 0.9
            elif age_days <= 7:
                s = 0.7
            else:
                s = max(0.3, 1.0 - age_days / 30)
            max_score = max(max_score, s)
        except (ValueError, TypeError):
            max_score = max(max_score, 0.7)
    return _clamp(max_score)


def score_new_info_gain(seed: dict, today_cards: list[dict]) -> float:
    """Check if today cards can supplement seed's missing materials."""
    required = seed.get("requiredMaterials") or []
    open_questions = [q for q in (seed.get("questions") or []) if q.get("status") == "needs_material"]
    total_needs = len(required) + len(open_questions)
    if total_needs == 0:
        return 0.3  # neutral — no clear needs

    # Build text corpus from today cards
    card_text = " ".join(
        f"{c.get('title', '')} {c.get('contentSummary', '')} "
        + " ".join(c.get("controversies", []))
        + " ".join(c.get("writingAngles", []))
        for c in today_cards
    )
    card_bigrams = _extract_bigrams(card_text)

    addressed = 0
    for need in required:
        need_bigrams = _extract_bigrams(str(need))
        if need_bigrams and _jaccard(need_bigrams, card_bigrams) > 0.1:
            addressed += 1
    for q in open_questions:
        q_bigrams = _extract_bigrams(q.get("question", ""))
        if q_bigrams and _jaccard(q_bigrams, card_bigrams) > 0.1:
            addressed += 1

    return _clamp(addressed / total_needs)


def score_memory_fit(seed: dict, memory: dict) -> float:
    """Check if seed.interestId matches user interest memories."""
    interest_id = seed.get("interestId", "")
    if not interest_id:
        return 0.3  # neutral

    interest_memories = memory.get("interestMemories") or []
    for im in interest_memories:
        if im.get("interestId") == interest_id:
            return 1.0
    # Partial: check if any memory interest name overlaps with seed tags
    seed_tags = set()
    for t in (seed.get("tags") or []):
        if isinstance(t, dict):
            seed_tags.add(t.get("label", ""))
        elif isinstance(t, str):
            seed_tags.add(t)
    for im in interest_memories:
        name = im.get("interestName", "")
        if name and name in seed.get("title", ""):
            return 0.7
    return 0.3


def score_controversy_potential(seed: dict, today_cards: list[dict]) -> float:
    """Count seed counter-arguments + card controversies."""
    seed_count = len(seed.get("counterArguments") or [])
    card_count = sum(len(c.get("controversies") or []) for c in today_cards)
    total = seed_count + card_count
    return _clamp(total / 5)


# ---------------------------------------------------------------------------
# Penalties
# ---------------------------------------------------------------------------

def compute_penalties(
    seed: dict,
    dismissed_pairs: set[tuple[str, str]] | None = None,
    published_topics: set[str] | None = None,
) -> tuple[float, list[str]]:
    """Returns (penalty_total, penalty_reasons). Penalty values are negative."""
    penalty = 0.0
    reasons: list[str] = []

    materials = seed.get("wateringMaterials") or []
    if not materials:
        penalty -= 0.25
        reasons.append("evidence_empty")
    else:
        has_source = any(
            (m.get("sourceLabel") or m.get("sourceUrl") or "").strip()
            for m in materials
        )
        if not has_source:
            penalty -= 0.15
            reasons.append("no_source")

    # Recently dismissed
    if dismissed_pairs:
        seed_id = seed.get("id", "")
        for ds_id, _ in dismissed_pairs:
            if ds_id == seed_id:
                penalty -= 0.30
                reasons.append("recently_dismissed")
                break

    # Same topic published
    if published_topics:
        seed_topic = (seed.get("title") or seed.get("coreClaim") or "").strip()
        if seed_topic and seed_topic in published_topics:
            penalty -= 0.20
            reasons.append("topic_already_published")

    return penalty, reasons


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_activation_score(
    seed: dict,
    hot_cards: list[dict],
    today_cards: list[dict],
    memory: dict,
    dismissed_pairs: set[tuple[str, str]] | None = None,
    published_topics: set[str] | None = None,
) -> dict:
    """Compute the full activation score for a seed.

    Returns dict with total (0-100), factors, penalties, penaltyReasons,
    bestTriggerCards, and triggerType.
    """
    all_cards = (hot_cards or []) + (today_cards or [])
    maturity = score_seed_maturity(seed)
    relatedness, trigger_cards, trigger_type = score_topic_relatedness(
        seed, hot_cards or [], today_cards or []
    )
    freshness = score_freshness(all_cards)
    info_gain = score_new_info_gain(seed, today_cards or [])
    memory_fit = score_memory_fit(seed, memory or {})
    controversy = score_controversy_potential(seed, today_cards or [])

    penalty, penalty_reasons = compute_penalties(
        seed, dismissed_pairs, published_topics
    )

    weighted = (
        maturity * WEIGHT_MATURITY
        + relatedness * WEIGHT_RELATEDNESS
        + freshness * WEIGHT_FRESHNESS
        + info_gain * WEIGHT_INFO_GAIN
        + memory_fit * WEIGHT_MEMORY_FIT
        + controversy * WEIGHT_CONTROVERSY
        + penalty
    )
    total = _clamp(weighted * 100, 0, 100)

    return {
        "total": round(total, 1),
        "factors": {
            "seedMaturity": round(maturity, 3),
            "topicRelatedness": round(relatedness, 3),
            "freshness": round(freshness, 3),
            "newInfoGain": round(info_gain, 3),
            "memoryFit": round(memory_fit, 3),
            "controversyPotential": round(controversy, 3),
        },
        "penalties": round(penalty, 3),
        "penaltyReasons": penalty_reasons,
        "bestTriggerCards": trigger_cards,
        "triggerType": trigger_type,
    }
