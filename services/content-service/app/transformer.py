"""Transform zhihu-adapter items into WorthReadingCard format.

Supports two modes:
- Single item → single card (legacy)
- Multi-source aggregation: 2-3 related items → 1 card with multiple sources
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("kanshan.content.transformer")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authority_to_score(level: str | None) -> int:
    mapping = {"high": 90, "medium": 70, "low": 50}
    return mapping.get(level or "", 60)


def _clean_text(value: str | None, limit: int = 220) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _source_summary(source: dict[str, Any]) -> str:
    return _clean_text(source.get("fullContent") or source.get("rawExcerpt") or source.get("title"), 260)


def _default_summary(title: str, sources: list[dict[str, Any]]) -> str:
    snippets = [_source_summary(source) for source in sources if _source_summary(source)]
    if not snippets:
        return title
    if len(snippets) == 1:
        return snippets[0]
    return "；".join(snippets[:2])


def _default_recommendation(category_id: str, sources: list[dict[str, Any]]) -> str:
    source_types = [source.get("sourceType", "来源") for source in sources]
    unique_types = list(dict.fromkeys(source_types))
    if category_id == "following":
        return "来自关注流的真实动态，适合观察你关注作者近期在讨论什么。"
    if category_id == "serendipity":
        return "来自知乎实时热点，可作为打破既有兴趣边界的偶遇输入。"
    return f"来自 {' / '.join(unique_types[:3])} 的真实内容，适合作为该兴趣方向的阅读输入。"


def _default_controversies(title: str, sources: list[dict[str, Any]]) -> list[str]:
    source_titles = [source.get("title", "") for source in sources if source.get("title")]
    if len(source_titles) >= 2:
        return [
            f"不同来源对“{title}”的关注重点是否一致？",
            "这些材料能否支撑一个明确立场，还是只适合作为事实背景？",
        ]
    return [
        f"围绕“{title}”最需要先分清事实判断和价值判断。",
        "这条内容是否有足够证据支撑后续写作？",
    ]


def _default_angles(title: str, category_id: str) -> list[str]:
    if category_id == "following":
        return [f"从关注作者动态看：{title}", f"我为什么认同或反对这条关注流观点？"]
    if category_id == "serendipity":
        return [f"从热点偶遇切入：{title}", f"这个热点和我的长期兴趣有什么关系？"]
    return [f"我对“{title}”的核心判断", f"把“{title}”写成一篇有证据的知乎回答"]


def _extract_tags(items: list[dict[str, Any]]) -> list[str]:
    tags: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        ct = item.get("contentType", "")
        if ct and ct not in seen:
            tags.append({"label": ct, "tone": "blue"})
            seen.add(ct)
        al = item.get("authorityLevel", "")
        authority_label = f"权威度:{al}" if al else ""
        if authority_label and authority_label not in seen:
            tags.append({"label": authority_label, "tone": "green"})
            seen.add(authority_label)
    if not tags:
        tags.append({"label": "高质量输入", "tone": "blue"})
    return tags[:5]


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
        "rawExcerpt": _clean_text(item.get("summary", ""), 500),
        "fullContent": item.get("fullContent") or item.get("summary", ""),
        "contribution": contribution or "提供核心观点和讨论基础",
    }


def aggregate_items_to_card(items: list[dict[str, Any]], category_id: str) -> dict[str, Any]:
    """Aggregate 2-3 related zhihu items into one WorthReadingCard with multiple sources.

    The first item is the primary source; subsequent items provide additional perspectives.
    """
    if not items:
        raise ValueError("Cannot aggregate empty items list")

    primary = items[0]
    logger.debug("aggregate_items", extra={
        "categoryId": category_id,
        "itemCount": len(items),
        "primaryTitle": primary.get("title", "")[:40],
    })
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

    title = primary.get("title", "未知标题")
    return {
        "id": f"agg-{primary.get('sourceId', uuid4().hex[:8])}",
        "categoryId": category_id,
        "tags": _extract_tags(items),
        "title": title,
        "recommendationReason": _default_recommendation(category_id, sources),
        "contentSummary": _default_summary(title, sources),
        "controversies": _default_controversies(title, sources),
        "writingAngles": _default_angles(title, category_id),
        "originalSources": sources,
        "relevanceScore": round(avg_relevance),
        "authorityScore": _authority_to_score(best_authority.get("authorityLevel")),
        "popularityScore": max_likes,
        "controversyScore": 0,
        "createdAt": primary.get("publishedAt", _now_iso()),
    }


def transform_hot_to_card(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a hot list item to WorthReadingCard for serendipity category."""
    logger.debug("transform_hot", extra={"title": item.get("title", "")[:40]})
    source = {
        "sourceId": item.get("sourceId", f"hot-{uuid4().hex[:8]}"),
        "sourceType": "hot_list",
        "sourceUrl": item.get("url", ""),
        "title": item.get("title", ""),
        "author": "",
        "publishedAt": "",
        "authorityMeta": "热榜",
        "meta": [],
        "rawExcerpt": _clean_text(item.get("summary", ""), 500),
        "fullContent": item.get("fullContent") or item.get("summary", ""),
        "contribution": "知乎热榜热门讨论",
    }
    title = item.get("title", "未知标题")
    return {
        "id": f"hot-{item.get('sourceId', uuid4().hex[:8])}",
        "categoryId": "serendipity",
        "tags": [{"label": "热榜", "tone": "orange"}, {"label": "偶遇", "tone": "blue"}],
        "title": title,
        "recommendationReason": _default_recommendation("serendipity", [source]),
        "contentSummary": _default_summary(title, [source]),
        "controversies": _default_controversies(title, [source]),
        "writingAngles": _default_angles(title, "serendipity"),
        "originalSources": [source],
        "relevanceScore": min(95, 50 + (item.get("heatScore", 0) // 1000)),
        "authorityScore": 60,
        "popularityScore": item.get("heatScore", 0),
        "controversyScore": 0,
        "createdAt": _now_iso(),
    }


def transform_following_to_card(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a following feed item to WorthReadingCard."""
    actor = item.get("actor", "")
    action_text = item.get("contentType", "")
    meta = [value for value in [f"{actor}{action_text}" if actor and action_text else action_text, item.get("publishedAt", "")] if value]
    source = {
        "sourceId": item.get("sourceId", f"fol-{uuid4().hex[:8]}"),
        "sourceType": "following",
        "sourceUrl": item.get("url", ""),
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "publishedAt": item.get("publishedAt", ""),
        "authorityMeta": "关注作者",
        "meta": meta,
        "rawExcerpt": _clean_text(item.get("summary", ""), 500),
        "fullContent": item.get("fullContent") or item.get("summary", ""),
        "contribution": f"关注流动态：{meta[0]}" if meta else "关注作者动态",
    }
    title = item.get("title", "未知标题")
    return {
        "id": f"fol-{item.get('sourceId', uuid4().hex[:8])}",
        "categoryId": "following",
        "tags": [{"label": "关注流", "tone": "green"}, {"label": "社交输入", "tone": "blue"}],
        "title": title,
        "recommendationReason": _default_recommendation("following", [source]),
        "contentSummary": _default_summary(title, [source]),
        "controversies": _default_controversies(title, [source]),
        "writingAngles": _default_angles(title, "following"),
        "originalSources": [source],
        "relevanceScore": 75,
        "authorityScore": 70,
        "popularityScore": item.get("likeCount", 0),
        "controversyScore": 0,
        "createdAt": item.get("publishedAt", _now_iso()),
    }
