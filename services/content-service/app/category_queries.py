"""Dynamic category-to-search-query mapping from user profile."""

from __future__ import annotations

from typing import Any

from kanshan_shared.categories import CATEGORY_MAP, SPECIAL_CATEGORIES


def extract_queries_from_profile(
    profile: dict[str, Any],
    categories: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Build category_id -> search_queries mapping from user profile.

    Uses interestMemories to derive search terms for each category.
    Falls back to shared defaults when profile data is missing.
    """
    result: dict[str, list[str]] = {}
    interest_memories = profile.get("interestMemories", [])

    # Build a lookup: interestName -> preferredPerspective
    memory_by_name: dict[str, dict[str, Any]] = {}
    for mem in interest_memories:
        memory_by_name[mem.get("interestName", "")] = mem

    for cat in categories:
        cat_id = cat["id"]
        if cat_id in SPECIAL_CATEGORIES:
            continue

        cat_name = cat.get("name", "")
        queries: list[str] = []

        # Try to find matching interest memory
        memory = memory_by_name.get(cat_name)
        if memory:
            # Use interest name as primary query
            queries.append(memory["interestName"])
            # Use first preferred perspective as secondary query
            perspectives = memory.get("preferredPerspective", [])
            if perspectives:
                queries.append(perspectives[0])
        else:
            # Fall back to shared defaults
            cat_def = CATEGORY_MAP.get(cat_id)
            queries = cat_def.default_queries if cat_def else [cat_name]

        if queries:
            result[cat_id] = queries

    return result
