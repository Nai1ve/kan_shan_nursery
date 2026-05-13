from __future__ import annotations

from typing import Any

from kanshan_shared.categories import INTEREST_CATEGORIES, CATEGORY_MAP, CategoryDef

from .defaults import interest_memory, now_iso
from .repository import ProfileRepository


PROFILE_FIELDS = {"nickname", "accountStatus", "role", "interests", "avoidances", "globalMemory", "interestMemories"}


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    def _normalize_interest_ids(self, selected_interests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in selected_interests:
            interest_id = item.get("interestId", "")
            cat = CATEGORY_MAP.get(interest_id)
            if not cat or cat.kind != "interest":
                continue
            normalized.append({
                "interestId": cat.id,
                "selected": bool(item.get("selected", True)),
                "selfRatedLevel": item.get("selfRatedLevel", "intermediate"),
                "intent": item.get("intent", "both"),
            })
        return normalized

    def get_profile(self, user_id: str | None = None) -> dict[str, Any]:
        return self.repository.get_profile(user_id=user_id)

    def update_profile(self, payload: dict[str, Any], reason: str = "update_profile") -> dict[str, Any]:
        unknown = set(payload.keys()) - PROFILE_FIELDS
        if unknown:
            raise ValueError(f"unsupported profile fields: {sorted(unknown)}")
        profile = self.repository.get_profile()
        next_profile = {**profile, **payload}
        return self.repository.save_profile(next_profile, reason)

    def save_onboarding(self, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        """Save onboarding data and construct a full profile.

        The frontend sends:
        {
            "nickname": "...",
            "selectedInterests": [{ "interestId": "...", "selected": true, "selfRatedLevel": "...", "intent": "..." }],
            "writingStyle": { ... }
        }

        We need to construct a full ProfileData from this.
        """
        nickname = payload.get("nickname", "用户")
        selected_interests = self._normalize_interest_ids(payload.get("selectedInterests", []))
        writing_style = payload.get("writingStyle", {})

        # Build interest list from selected interests
        interests = []
        interest_memories = []

        for si in selected_interests:
            if not si.get("selected", True):
                continue
            interest_id = si.get("interestId", "")
            cat = CATEGORY_MAP.get(interest_id)
            if cat and cat.kind == "interest":
                interests.append(cat.name)
                knowledge_level = si.get("selfRatedLevel", "intermediate")
                level_map = {"beginner": "入门", "intermediate": "中级", "advanced": "进阶"}
                interest_memories.append(interest_memory(
                    cat,
                ))

        # If no interests selected, use defaults
        if not interests:
            interests = [cat.name for cat in INTEREST_CATEGORIES]
            interest_memories = [interest_memory(cat) for cat in INTEREST_CATEGORIES]

        # Build global memory from writing style
        global_memory = {
            "longTermBackground": f"用户 {nickname}，刚完成注册和兴趣选择。",
            "contentPreference": "偏好真实经历、问题拆解、反方质疑。更重视'为什么这样想'而不是单纯罗列信息。",
            "writingStyle": "清晰、克制；允许有观点锋芒，但避免标题党和情绪煽动。",
            "recommendationStrategy": "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看。",
            "riskReminder": "容易写成逻辑完整但缺少个人经历的文章；需要在写作阶段主动补充真实案例。",
        }

        # Construct full profile
        profile = {
            "nickname": nickname,
            "accountStatus": "已注册",
            "role": "内容创作者",
            "interests": interests,
            "avoidances": "不要替我决定立场；不要生成空泛、油滑、过度平衡的 AI 味文章。",
            "globalMemory": global_memory,
            "interestMemories": interest_memories,
            "userId": user_id,
        }

        # Save directly (bypass update_profile validation)
        saved_profile = self.repository.save_profile(profile, "onboarding", user_id=user_id)
        return {
            "profile": saved_profile,
            "profileStatus": "provisional",
            "enrichmentJob": None,
        }

    def update_interests(self, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        selected_interests = self._normalize_interest_ids(payload.get("interests", []))
        if not selected_interests:
            raise ValueError("at least one valid interest is required")

        profile = self.repository.get_profile(user_id)
        selected = [item for item in selected_interests if item.get("selected", True)]
        if not selected:
            raise ValueError("at least one selected interest is required")

        selected_ids = [item["interestId"] for item in selected]
        existing_by_id = {
            memory.get("interestId"): memory
            for memory in profile.get("interestMemories", [])
            if memory.get("interestId")
        }

        next_interest_memories = []
        next_interests = []
        for interest_id in selected_ids:
            cat = CATEGORY_MAP[interest_id]
            next_interests.append(cat.name)
            existing = existing_by_id.get(interest_id)
            next_interest_memories.append(existing if existing else interest_memory(cat))

        profile["interests"] = next_interests
        profile["interestMemories"] = next_interest_memories
        return self.repository.save_profile(profile, "update_interests", user_id=user_id)

    def update_basic_profile(self, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        """Update basic profile fields (nickname, role, avoidances)."""
        allowed_fields = {"nickname", "role", "avoidances"}
        unknown = set(payload.keys()) - allowed_fields
        if unknown:
            raise ValueError(f"unsupported fields for basic update: {sorted(unknown)}")
        profile = self.repository.get_profile(user_id)
        next_profile = {**profile, **payload}
        return self.repository.save_profile(next_profile, "update_basic_profile", user_id=user_id)

    def get_writing_style(self) -> dict[str, Any]:
        """Get user's writing style configuration."""
        # Try to get from dedicated table first (if pg_repository)
        if hasattr(self.repository, 'get_writing_style'):
            style = self.repository.get_writing_style("default")
            if style:
                return style
        # Fall back to profile data
        profile = self.repository.get_profile()
        return profile.get("writingStyle", {})

    def update_writing_style(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update user's writing style configuration."""
        # Save to dedicated table if available
        if hasattr(self.repository, 'save_writing_style'):
            return self.repository.save_writing_style("default", payload)
        # Fall back to profile data
        profile = self.repository.get_profile()
        profile["writingStyle"] = payload
        return self.repository.save_profile(profile, "update_writing_style")

    def get_llm_config(self) -> dict[str, Any]:
        """Get user's LLM configuration."""
        # Try to get from dedicated table first (if pg_repository)
        if hasattr(self.repository, 'get_llm_config'):
            config = self.repository.get_llm_config("default")
            if config:
                return config
        # Return default config
        return {
            "provider": "openai_compat",
            "model": "gpt-5.5",
            "baseUrl": "",
            "apiKey": "",
        }

    def update_llm_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update user's LLM configuration."""
        # Save to dedicated table if available
        if hasattr(self.repository, 'save_llm_config'):
            return self.repository.save_llm_config("default", payload)
        # LLM config is not stored in profile data for security
        return payload
