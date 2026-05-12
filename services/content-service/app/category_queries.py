"""Dynamic category-to-search-query mapping from user profile."""

from __future__ import annotations

from typing import Any

# Default mapping when profile is unavailable
DEFAULT_CATEGORY_QUERIES: dict[str, list[str]] = {
    "agent": ["AI Agent 开发", "Agent 工程化"],
    "ai-coding": ["AI 编程", "AI Coding"],
    "rag": ["RAG 检索增强生成"],
    "backend": ["后端架构", "微服务设计"],
    "growth": ["程序员成长"],
}

# Categories that don't use search
SPECIAL_CATEGORIES = {
    "following",   # requires OAuth
    "serendipity", # uses hot list
}


def extract_queries_from_profile(
    profile: dict[str, Any],
    categories: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Build category_id -> search_queries mapping from user profile.

    Uses interestMemories to derive search terms for each category.
    Falls back to defaults when profile data is missing.
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
            # Fall back to defaults
            queries = DEFAULT_CATEGORY_QUERIES.get(cat_id, [cat_name])

        if queries:
            result[cat_id] = queries

    return result
