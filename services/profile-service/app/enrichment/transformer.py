"""Transformers for LLM input/output conversion."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from .models import ProfileSignalBundle, ProfileSignalSourceItem

from kanshan_shared.categories import INTEREST_CATEGORIES, CategoryDef


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _truncate_excerpt(text: str, max_len: int = 240) -> str:
    """Truncate excerpt to max_len characters."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _interest_id(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("interestId") or item.get("id") or item.get("name") or "")
    return str(item or "")


def _interest_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("interestName") or item.get("id") or item.get("interestId") or "")
    return str(item or "")


def _signal_to_interaction(signal: ProfileSignalSourceItem) -> dict[str, Any] | None:
    """Convert a signal to an interaction entry for LLM input."""
    if signal.source_type == "onboarding":
        return None  # Onboarding data is handled separately

    if signal.source_type in ("followed", "followers"):
        # Followed/followers are weak signals, include as context
        return {
            "type": "social_connection",
            "source": signal.source_type,
            "name": signal.author_name or signal.title,
            "headline": signal.headline,
            "confidence": signal.confidence_hint,
        }

    if signal.source_type == "moments":
        # Moments are content interactions
        return {
            "type": "content_interaction",
            "title": signal.title,
            "excerpt": _truncate_excerpt(signal.excerpt or ""),
            "author": signal.author_name,
            "action": signal.action_text,
            "publishedAt": signal.published_at,
            "confidence": signal.confidence_hint,
        }

    if signal.source_type == "zhihu_user":
        # User profile info
        return {
            "type": "user_profile",
            "name": signal.author_name,
            "headline": signal.headline,
            "description": _truncate_excerpt(signal.excerpt or ""),
        }

    return None


def _signal_text(signal: ProfileSignalSourceItem) -> str:
    return " ".join(
        str(part)
        for part in [
            signal.author_name,
            signal.headline,
            signal.title,
            signal.excerpt,
            signal.action_text,
        ]
        if part
    ).strip()


def _category_keywords(cat: CategoryDef) -> set[str]:
    words = {cat.name, cat.id, cat.description, *cat.preferred_perspective, *cat.default_queries}
    return {word.strip().lower() for word in words if str(word).strip()}


def _catalog_categories(interest_catalog: list[dict[str, Any]] | list[str]) -> list[CategoryDef]:
    selected_ids = {_interest_id(item) for item in interest_catalog if _interest_id(item)}
    selected_names = {_interest_name(item) for item in interest_catalog if _interest_name(item)}
    if not selected_ids and not selected_names:
        return INTEREST_CATEGORIES
    matched = [
        cat
        for cat in INTEREST_CATEGORIES
        if cat.id in selected_ids or cat.name in selected_names
    ]
    return matched or INTEREST_CATEGORIES


def _social_signal_summary(
    signals: list[ProfileSignalSourceItem],
    interest_catalog: list[dict[str, Any]] | list[str],
) -> dict[str, Any]:
    """Extract weak Memory signals from followed/follower lists.

    Following is a stronger preference signal than followers. Followers still
    matter, but they mainly describe the audience that may read the user.
    """
    categories = _catalog_categories(interest_catalog)
    keyword_map = {cat.id: _category_keywords(cat) for cat in categories}
    by_category: dict[str, dict[str, Any]] = {}
    source_counts = {"followed": 0, "followers": 0}
    total_social = 0

    for signal in signals:
        if signal.source_type not in {"followed", "followers"}:
            continue
        total_social += 1
        source_counts[signal.source_type] += 1
        text = _signal_text(signal)
        lowered = text.lower()
        if not lowered:
            continue

        weight = 1.0 if signal.source_type == "followed" else 0.45
        for cat in categories:
            matched = [keyword for keyword in keyword_map[cat.id] if keyword and keyword in lowered]
            if not matched:
                continue
            bucket = by_category.setdefault(
                cat.id,
                {
                    "interestId": cat.id,
                    "interestName": cat.name,
                    "score": 0.0,
                    "followed": 0,
                    "followers": 0,
                    "keywords": defaultdict(float),
                    "examples": [],
                },
            )
            bucket["score"] += weight * max(1, len(matched))
            bucket[signal.source_type] += 1
            for keyword in matched[:5]:
                bucket["keywords"][keyword] += weight
            if len(bucket["examples"]) < 4:
                bucket["examples"].append(
                    {
                        "source": signal.source_type,
                        "name": signal.author_name or signal.title or signal.source_id,
                        "headline": signal.headline or signal.excerpt or "",
                    }
                )

    categories_summary = []
    for item in by_category.values():
        keywords = sorted(item["keywords"].items(), key=lambda pair: pair[1], reverse=True)
        categories_summary.append({
            "interestId": item["interestId"],
            "interestName": item["interestName"],
            "score": round(item["score"], 2),
            "followedCount": item["followed"],
            "followersCount": item["followers"],
            "topKeywords": [keyword for keyword, _ in keywords[:6]],
            "examples": item["examples"],
        })
    categories_summary.sort(key=lambda item: item["score"], reverse=True)

    return {
        "totalSocialConnections": total_social,
        "sourceCounts": source_counts,
        "categories": categories_summary,
    }


def transform_bundle_to_llm_input(
    bundle: ProfileSignalBundle,
    existing_memory: dict[str, Any],
    interest_catalog: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Transform ProfileSignalBundle to llm-service expected input format.

    Args:
        bundle: The signal bundle with onboarding and OAuth signals
        existing_memory: Current globalMemory and interestMemories
        interest_catalog: Available interest categories
        profile: User profile data (nickname, interests, writing style)

    Returns:
        LLM input dict with user, interactions, and currentMemory
    """
    # Extract onboarding data
    onboarding = bundle.onboarding or {}
    selected_interest_ids = onboarding.get("selectedInterestIds", [])
    writing_style_answers = onboarding.get("writingStyleAnswers", {})

    # Build user info
    nickname = profile.get("nickname", "用户")
    selected_set = {str(item) for item in selected_interest_ids if item}
    interests = [
        _interest_name(cat)
        for cat in interest_catalog
        if not selected_set or _interest_id(cat) in selected_set or _interest_name(cat) in selected_set
    ]
    writing_style = profile.get("writingStyle", {})

    # Build interactions from signals
    seed_reactions = []
    questions = []
    writing_history = []
    social_connections = []
    content_interactions = []

    for signal in bundle.signals:
        interaction = _signal_to_interaction(signal)
        if interaction is None:
            continue

        if interaction["type"] == "social_connection":
            social_connections.append(interaction)
        elif interaction["type"] == "content_interaction":
            content_interactions.append(interaction)
            # Convert to seed reaction format
            seed_reactions.append({
                "seedTitle": interaction.get("title", ""),
                "reaction": "agree",  # Default, could be refined
                "categoryId": "",
            })
        elif interaction["type"] == "user_profile":
            # User profile info enriches the user section
            pass

    # Build current memory
    current_memory = existing_memory or {}
    global_memory = current_memory.get("globalMemory", {
        "longTermBackground": "",
        "contentPreference": "",
        "writingStyle": "",
    })
    interest_memories = current_memory.get("interestMemories", [])

    social_summary = _social_signal_summary(bundle.signals, interest_catalog)

    return {
        "user": {
            "nickname": nickname,
            "interests": interests,
            "writingStyle": writing_style,
            "selfDescription": onboarding.get("selfDescription", ""),
        },
        "interactions": {
            "seedReactions": seed_reactions[:20],  # Limit to top 20
            "questions": questions,
            "writingHistory": writing_history,
            "socialConnections": social_connections[:30],  # Limit to top 30
            "contentInteractions": content_interactions[:20],  # Limit to top 20
            "socialSignalSummary": social_summary,
        },
        "currentMemory": {
            "globalMemory": global_memory,
            "interestMemories": interest_memories,
        },
    }


def build_social_memory_requests(
    bundle: ProfileSignalBundle,
    user_id: str,
    existing_memory: dict[str, Any],
    interest_catalog: list[dict[str, Any]] | list[str],
    max_interest_requests: int = 3,
) -> list[dict[str, Any]]:
    """Build pending Memory update requests from followed/follower lists.

    These requests are deliberately conservative: they only surface social
    graph evidence and still require user confirmation before changing Memory.
    """
    social_summary = _social_signal_summary(bundle.signals, interest_catalog)
    categories = social_summary.get("categories", [])
    if not categories:
        return []

    now = _now_iso()
    requests: list[dict[str, Any]] = []
    existing_global = existing_memory.get("globalMemory", {}) if existing_memory else {}

    top_names = [item["interestName"] for item in categories[:3]]
    source_counts = social_summary.get("sourceCounts", {})
    global_value = (
        "知乎关注/粉丝关系显示，用户的社交输入集中在"
        f"{'、'.join(top_names)}等方向；推荐和写作时应优先保留这些圈层的热点、争议和读者视角。"
    )
    if global_value != existing_global.get("contentPreference"):
        requests.append({
            "id": _create_id("memreq"),
            "userId": user_id,
            "scope": "global",
            "interestId": "global",
            "targetField": "contentPreference",
            "suggestedValue": global_value,
            "reason": (
                "基于知乎关注列表和粉丝列表提取的社交输入信号："
                f"关注 {source_counts.get('followed', 0)} 人，粉丝 {source_counts.get('followers', 0)} 人。"
            ),
            "evidenceRefs": [example.get("name", "") for item in categories[:3] for example in item.get("examples", [])][:8],
            "status": "pending",
            "createdAt": now,
        })

    existing_interests = {
        im.get("interestId"): im
        for im in existing_memory.get("interestMemories", [])
    } if existing_memory else {}

    for item in categories[:max_interest_requests]:
        interest_id = item["interestId"]
        keywords = item.get("topKeywords", [])
        examples = item.get("examples", [])
        example_names = [example.get("name", "") for example in examples if example.get("name")]
        reminder = (
            f"该兴趣下的知乎社交关系集中出现 {', '.join(keywords[:4]) or item['interestName']}。"
            "写作时可优先观察关注对象的专业视角，同时把粉丝侧问题作为读者追问处理。"
        )
        existing = existing_interests.get(interest_id, {})
        if reminder and reminder != existing.get("writingReminder"):
            requests.append({
                "id": _create_id("memreq"),
                "userId": user_id,
                "scope": "interest",
                "interestId": interest_id,
                "targetField": "writingReminder",
                "suggestedValue": reminder,
                "reason": (
                    f"知乎社交关系中有 {item.get('followedCount', 0)} 个关注对象、"
                    f"{item.get('followersCount', 0)} 个粉丝与「{item['interestName']}」相关；"
                    f"代表样本：{'、'.join(example_names[:3]) or '暂无名称'}。"
                ),
                "evidenceRefs": example_names[:6],
                "status": "pending",
                "createdAt": now,
            })

    return requests


def dedupe_memory_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for request in requests:
        key = (
            str(request.get("interestId", "")),
            str(request.get("targetField", "")),
            str(request.get("suggestedValue", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(request)
    return deduped


def transform_llm_output_to_requests(
    llm_output: dict[str, Any],
    user_id: str,
    existing_memory: dict[str, Any],
) -> list[dict[str, Any]]:
    """Transform LLM output to MemoryUpdateRequest list.

    Args:
        llm_output: LLM response with globalMemory and interestMemories
        user_id: User ID
        existing_memory: Current memory for comparison

    Returns:
        List of MemoryUpdateRequest dicts
    """
    requests = []
    now = _now_iso()

    # Process global memory updates
    global_memory = llm_output.get("globalMemory", {})
    existing_global = existing_memory.get("globalMemory", {})

    for field in ("longTermBackground", "contentPreference", "writingStyle", "recommendationStrategy", "riskReminder"):
        new_value = global_memory.get(field, "")
        old_value = existing_global.get(field, "")

        if new_value and new_value != old_value:
            requests.append({
                "id": _create_id("memreq"),
                "userId": user_id,
                "scope": "global",
                "interestId": None,
                "targetField": field,
                "suggestedValue": new_value,
                "reason": f"基于 OAuth 数据和 onboarding 信息生成的 {field} 建议",
                "evidenceRefs": [],  # Could be enriched with signal evidence IDs
                "status": "pending",
                "createdAt": now,
            })

    # Process interest memory updates
    interest_memories = llm_output.get("interestMemories", [])
    existing_interests = {
        im.get("interestId"): im
        for im in existing_memory.get("interestMemories", [])
    }

    for interest_memory in interest_memories:
        interest_id = interest_memory.get("interestId", "")
        if not interest_id:
            continue

        existing_im = existing_interests.get(interest_id, {})

        # Check each field for changes
        for field in ("knowledgeLevel", "preferredPerspective", "evidencePreference", "writingReminder", "feedbackSummary"):
            new_value = interest_memory.get(field)
            old_value = existing_im.get(field)

            if new_value and new_value != old_value:
                requests.append({
                    "id": _create_id("memreq"),
                    "userId": user_id,
                    "scope": "interest",
                    "interestId": interest_id,
                    "targetField": field,
                    "suggestedValue": new_value if isinstance(new_value, str) else str(new_value),
                    "reason": f"基于 OAuth 数据生成的 {interest_memory.get('interestName', interest_id)} 兴趣 {field} 建议",
                    "evidenceRefs": [],
                    "status": "pending",
                    "createdAt": now,
                })

    return requests


def build_fallback_requests(
    user_id: str,
    profile: dict[str, Any],
    interest_catalog: list[dict[str, Any]],
    signal_bundle: ProfileSignalBundle | None = None,
    existing_memory: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build fallback memory update requests when LLM fails.

    Uses simple rule-based approach to generate basic memory from onboarding data.
    """
    requests = []
    now = _now_iso()
    selected_interests = profile.get("interests", [])

    # Generate basic global memory
    nickname = profile.get("nickname", "用户")
    selected_ids = {_interest_id(item) for item in selected_interests}
    selected_names = {_interest_name(item) for item in selected_interests}
    interest_names = [
        _interest_name(cat)
        for cat in interest_catalog
        if _interest_id(cat) in selected_ids or _interest_name(cat) in selected_names
    ]

    if interest_names:
        requests.append({
            "id": _create_id("memreq"),
            "userId": user_id,
            "scope": "global",
            "interestId": None,
            "targetField": "longTermBackground",
            "suggestedValue": f"用户 {nickname}，关注{'、'.join(interest_names)}领域",
            "reason": "基于 onboarding 数据生成的基础画像（LLM 调用失败回退）",
            "evidenceRefs": [],
            "status": "pending",
            "createdAt": now,
        })

    if signal_bundle is not None:
        requests.extend(build_social_memory_requests(
            signal_bundle,
            user_id=user_id,
            existing_memory=existing_memory or {},
            interest_catalog=interest_catalog,
        ))

    return dedupe_memory_requests(requests)
