"""Rule-based candidate filtering for Today's Sprout.

Pure functions — no external dependencies.
"""

from __future__ import annotations


_EXCLUDED_STATUSES = frozenset({"published", "writing"})
_MIN_MATURITY_SCORE = 45


def filter_candidates(
    seeds: list[dict],
    dismissed_pairs: set[tuple[str, str]] | None = None,
    active_writing_seed_ids: set[str] | None = None,
) -> list[dict]:
    """Return seeds that pass all inclusion criteria and no exclusion criteria.

    Args:
        seeds: Full seed dicts from seed-service.
        dismissed_pairs: (seedId, triggerCardId) pairs dismissed within 7 days.
        active_writing_seed_ids: Seed IDs with active writing sessions.
    """
    dismissed = dismissed_pairs or set()
    writing_ids = active_writing_seed_ids or set()
    result = []
    for seed in seeds:
        if not _passes_inclusion(seed):
            continue
        if _matches_exclusion(seed, dismissed, writing_ids):
            continue
        result.append(seed)
    return result


def _passes_inclusion(seed: dict) -> bool:
    """All inclusion criteria must be satisfied."""
    status = seed.get("status", "")
    if status in _EXCLUDED_STATUSES:
        return False
    try:
        maturity = int(seed.get("maturityScore", 0))
    except (ValueError, TypeError):
        maturity = 0
    if maturity < _MIN_MATURITY_SCORE:
        return False
    materials = seed.get("wateringMaterials") or []
    if len(materials) < 1:
        return False
    return True


def _matches_exclusion(
    seed: dict,
    dismissed_pairs: set[tuple[str, str]],
    active_writing_seed_ids: set[str],
) -> bool:
    """Any exclusion criterion causes rejection."""
    seed_id = seed.get("id", "")
    # Active writing session
    if seed_id in active_writing_seed_ids:
        return True
    # Empty seed — no viewpoint content
    has_claim = bool((seed.get("coreClaim") or "").strip())
    has_title = bool((seed.get("title") or "").strip())
    if not has_claim and not has_title:
        return True
    # Recently dismissed — check if any of this seed's trigger cards were dismissed
    for dismissed_seed_id, _trigger_card_id in dismissed_pairs:
        if dismissed_seed_id == seed_id:
            return True
    return False


def build_dismissed_pairs_from_opportunities(
    opportunities: list[dict],
    days: int = 7,
) -> set[tuple[str, str]]:
    """Scan dismissed opportunities and extract (seedId, triggerCardId) pairs
    within the given time window."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pairs: set[tuple[str, str]] = set()
    for opp in opportunities:
        if opp.get("status") != "dismissed":
            continue
        dismissed_at = opp.get("dismissedAt")
        if dismissed_at:
            try:
                dt = datetime.fromisoformat(dismissed_at.replace("Z", "+00:00"))
                if dt < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        seed_id = opp.get("seedId", "")
        trigger_card_ids = opp.get("triggerCardIds") or []
        for card_id in trigger_card_ids:
            pairs.add((seed_id, card_id))
        # Also match without specific card (seed-level dismissal)
        if not trigger_card_ids:
            pairs.add((seed_id, ""))
    return pairs
