"""Transform zhihu-adapter items into WorthReadingCard format.

Supports two modes:
- Single item → single card (legacy)
- Multi-source aggregation: 2-3 related items → 1 card with multiple sources
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authority_to_score(level: str | None) -> int:
    mapping = {"high": 90, "medium": 70, "low": 50}
    return mapping.get(level or "", 60)


def _extract_tags(items: list[dict[str, Any]]) -> list[str]:
    tags: set[str] = set()
    for item in items:
        ct = item.get("contentType", "")
        if ct:
            tags.add(ct)
        al = item.get("authorityLevel", "")
        if al:
            tags.add(f"权威度:{al}")
    return list(tags)[:5]


def transform_source(item: dict[str, Any], contribution: str = "") -> dict[str, Any]:
    """Convert a zhihu item to ContentSource format."""
    return {
        "sourceId": item.get("sourceId", f"src-{uuid4().hex[:8]}"),
        "sourceType": item.get("sourceType", "zhihu_search"),
        "sourceUrl": item.get("url", ""),
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "publishedAt": item.get("publishedAt", ""),
        "authorityMeta": item.get("authorityLevel", ""),
        "meta": [],
        "rawExcerpt": item.get("summary", "")[:500],
        "fullContent": item.get("summary", ""),
        "contribution": contribution or "提供核心观点和讨论基础",
    }


def aggregate_items_to_card(items: list[dict[str, Any]], category_id: str) -> dict[str, Any]:
    """Aggregate 2-3 related zhihu items into one WorthReadingCard with multiple sources.

    The first item is the primary source; subsequent items provide additional perspectives.
    """
    if not items:
        raise ValueError("Cannot aggregate empty items list")

    primary = items[0]
    sources = []

    # Primary source: provides main topic
    sources.append(transform_source(primary, "提供核心话题和主要讨论背景"))

    # Additional sources: provide different perspectives
    contributions = [
        "提供补充论据或反方视角",
        "提供行业案例或数据支撑",
    ]
    for i, item in enumerate(items[1:3]):  # Max 2 additional sources
        sources.append(transform_source(item, contributions[min(i, len(contributions) - 1)]))

    # Compute aggregate scores
    avg_relevance = sum(it.get("relevanceScore", 70) for it in items) / len(items)
    max_likes = max(it.get("likeCount", 0) for it in items)
    max_comments = max(it.get("commentCount", 0) for it in items)
    best_authority = max(items, key=lambda it: _authority_to_score(it.get("authorityLevel")))

    return {
        "id": f"agg-{primary.get('sourceId', uuid4().hex[:8])}",
        "categoryId": category_id,
        "tags": _extract_tags(items),
        "title": primary.get("title", "未知标题"),
        "recommendationReason": "",   # LLM enricher fills this
        "contentSummary": "",          # LLM enricher fills this
        "controversies": [],           # LLM enricher fills this
        "writingAngles": [],           # LLM enricher fills this
        "originalSources": sources,
        "relevanceScore": round(avg_relevance),
        "authorityScore": _authority_to_score(best_authority.get("authorityLevel")),
        "popularityScore": max_likes,
        "controversyScore": 0,
        "createdAt": primary.get("publishedAt", _now_iso()),
    }


def transform_hot_to_card(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a hot list item to WorthReadingCard for serendipity category."""
    source = {
        "sourceId": item.get("sourceId", f"hot-{uuid4().hex[:8]}"),
        "sourceType": "hot_list",
        "sourceUrl": item.get("url", ""),
        "title": item.get("title", ""),
        "author": "",
        "publishedAt": "",
        "authorityMeta": "热榜",
        "meta": [],
        "rawExcerpt": item.get("summary", "")[:500],
        "fullContent": item.get("summary", ""),
        "contribution": "知乎热榜热门讨论",
    }
    return {
        "id": f"hot-{item.get('sourceId', uuid4().hex[:8])}",
        "categoryId": "serendipity",
        "tags": ["热榜", "偶遇"],
        "title": item.get("title", "未知标题"),
        "recommendationReason": "",  # LLM enricher fills this
        "contentSummary": "",         # LLM enricher fills this
        "controversies": [],          # LLM enricher fills this
        "writingAngles": [],          # LLM enricher fills this
        "originalSources": [source],
        "relevanceScore": min(95, 50 + (item.get("heatScore", 0) // 1000)),
        "authorityScore": 60,
        "popularityScore": item.get("heatScore", 0),
        "controversyScore": 0,
        "createdAt": _now_iso(),
    }
