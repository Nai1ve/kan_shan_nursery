"""Category-to-search-query mapping for the system content pool."""

from __future__ import annotations

from typing import Any

from kanshan_shared.categories import CATEGORY_MAP, SPECIAL_CATEGORIES


def build_system_queries(
    categories: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Build user-independent category_id -> search_queries mapping.

    The content cache must be independent of any user. User interests and
    Memory are applied later in ``content-service`` request-time scoring.
    """
    result: dict[str, list[str]] = {}

    for cat in categories:
        cat_id = cat["id"]
        if cat_id in SPECIAL_CATEGORIES:
            continue

        cat_name = cat.get("name", "")
        cat_def = CATEGORY_MAP.get(cat_id)
        queries = list(cat_def.default_queries if cat_def else [cat_name])

        if queries:
            result[cat_id] = queries

    return result


def extract_queries_from_profile(
    profile: dict[str, Any],
    categories: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Backward-compatible alias.

    Older code called this function while building the global cache. Keep the
    name but deliberately ignore profile so the cache stays user-independent.
    """
    _ = profile
    return build_system_queries(categories)
