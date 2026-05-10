import re
from datetime import datetime, timezone
from typing import Any

from .security import stable_hash


TAG_RE = re.compile(r"<[^>]+>")


def unix_to_iso(value: int | float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def strip_html(value: str) -> str:
    return TAG_RE.sub("", value or "")


def infer_content_type(url: str) -> str:
    if "/question/" in url:
        return "Question"
    if "zhuanlan.zhihu.com" in url or "/p/" in url:
        return "Article"
    if "/answer/" in url:
        return "Answer"
    return "Unknown"


def selected_comments(items: list[dict[str, Any]] | None) -> list[str]:
    return [str(item.get("Content", "")) for item in (items or []) if item.get("Content")]


def map_hot_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
    items = raw.get("Data", {}).get("Items", [])
    mapped: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        url = item.get("Url", "")
        mapped.append(
            {
                "sourceType": "hot_list",
                "sourceId": stable_hash(url),
                "contentType": infer_content_type(url),
                "title": item.get("Title", ""),
                "url": url,
                "summary": item.get("Summary", ""),
                "thumbnailUrl": item.get("ThumbnailUrl", ""),
                "heatScore": max(1, 100 - index * 2),
                "raw": item,
            }
        )
    return mapped


def map_search(raw: dict[str, Any], source_type: str) -> list[dict[str, Any]]:
    data = raw.get("Data", {})
    search_hash_id = data.get("SearchHashId")
    mapped: list[dict[str, Any]] = []
    for item in data.get("Items", []):
        content_text = item.get("ContentText", "")
        summary = strip_html(content_text) if source_type == "global_search" else content_text
        mapped.append(
            {
                "sourceType": source_type,
                "sourceId": str(item.get("ContentID", "")),
                "contentType": item.get("ContentType", ""),
                "title": item.get("Title", ""),
                "url": item.get("Url", ""),
                "author": item.get("AuthorName", ""),
                "authorAvatar": item.get("AuthorAvatar", ""),
                "authorBadgeText": item.get("AuthorBadgeText", ""),
                "publishedAt": unix_to_iso(item.get("EditTime")),
                "summary": summary,
                "rawExcerptHtml": content_text if source_type == "global_search" else None,
                "commentCount": item.get("CommentCount", 0),
                "likeCount": item.get("VoteUpCount", 0),
                "authorityLevel": item.get("AuthorityLevel", ""),
                "rankingScore": item.get("RankingScore"),
                "relevanceScore": item.get("RankingScore"),
                "selectedComments": selected_comments(item.get("CommentInfoList")),
                "searchHashId": search_hash_id,
                "raw": item,
            }
        )
    return mapped


def map_ring_detail(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data", {})
    ring_info = data.get("ring_info", {})
    contents = []
    for item in data.get("contents", []):
        comments = [comment.get("content", "") for comment in item.get("comments", []) if comment.get("content")]
        contents.append(
            {
                "sourceType": "ring",
                "sourceId": str(item.get("pin_id", "")),
                "contentType": "Pin",
                "title": item.get("title") or item.get("content", "")[:32],
                "author": item.get("author_name", ""),
                "publishedAt": unix_to_iso(item.get("publish_time")),
                "summary": strip_html(item.get("content", ""))[:240],
                "fullContent": item.get("content", ""),
                "likeCount": item.get("like_num", 0),
                "commentCount": item.get("comment_num", 0),
                "favoriteCount": item.get("fav_num", 0),
                "shareCount": item.get("share_num", 0),
                "selectedComments": comments,
                "raw": item,
            }
        )
    return {
        "ring": {
            "ringId": str(ring_info.get("ring_id", "")),
            "name": ring_info.get("ring_name", ""),
            "description": ring_info.get("ring_desc", ""),
            "avatarUrl": ring_info.get("ring_avatar", ""),
            "memberCount": ring_info.get("membership_num", 0),
            "discussionCount": ring_info.get("discussion_num", 0),
        },
        "items": contents,
    }


def map_story_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "sourceType": "story",
            "sourceId": str(item.get("work_id", "")),
            "contentType": "Story",
            "title": item.get("title", ""),
            "summary": item.get("description", ""),
            "thumbnailUrl": item.get("artwork", ""),
            "tags": item.get("labels", []),
            "usageNotice": "Only for this hackathon. Credit the original Zhihu Yan story and author.",
            "raw": item,
        }
        for item in raw.get("data", [])
    ]


def map_story_detail(raw: dict[str, Any]) -> dict[str, Any]:
    item = raw.get("data", {}) or {}
    return {
        "sourceType": "story",
        "sourceId": str(item.get("work_id", "")),
        "contentType": "Story",
        "title": item.get("chapter_name", ""),
        "author": item.get("author_name", ""),
        "summary": item.get("introduction", ""),
        "fullContent": item.get("content", ""),
        "tags": item.get("labels", []),
        "usageNotice": f"改编自知乎盐言故事《{item.get('chapter_name', '')}》，作者：{item.get('author_name', '')}",
        "raw": item,
    }


def map_following_feed(raw: dict[str, Any]) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for item in raw.get("data", []):
        target = item.get("target", {})
        author = target.get("author", {})
        mapped.append(
            {
                "sourceType": "following",
                "sourceId": stable_hash(f"{target.get('title', '')}:{item.get('action_time', '')}"),
                "contentType": item.get("action_text", ""),
                "title": target.get("title", ""),
                "author": author.get("name", ""),
                "publishedAt": unix_to_iso(item.get("action_time")),
                "summary": target.get("excerpt", ""),
                "raw": item,
            }
        )
    return mapped


def map_direct_answer(raw: dict[str, Any]) -> dict[str, Any]:
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message", {})
    return {
        "taskId": raw.get("id", ""),
        "model": raw.get("model", ""),
        "content": message.get("content", ""),
        "reasoningContent": message.get("reasoning_content", ""),
        "finishReason": choice.get("finish_reason", ""),
    }
