"""Transformers for LLM input/output conversion."""

from __future__ import annotations

import uuid
from typing import Any

from .models import ProfileSignalBundle, ProfileSignalSourceItem


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
        },
        "currentMemory": {
            "globalMemory": global_memory,
            "interestMemories": interest_memories,
        },
    }


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

    return requests
