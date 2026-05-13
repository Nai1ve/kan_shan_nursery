from __future__ import annotations

from typing import Any

from kanshan_shared.categories import INTEREST_CATEGORIES, CATEGORY_MAP, CategoryDef

from .defaults import interest_memory, now_iso
from .repository import ProfileRepository


PROFILE_FIELDS = {"nickname", "accountStatus", "role", "interests", "avoidances", "globalMemory", "interestMemories"}


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


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

    def get_llm_config(self, user_id: str | None = None, *, include_secret: bool = False) -> dict[str, Any]:
        """Get user's LLM configuration."""
        config = None
        if hasattr(self.repository, "get_llm_config"):
            config = self.repository.get_llm_config(user_id or "default")

        if not config:
            config = {
                "status": "platform_free",
                "activeProvider": "platform_free",
                "provider": "openai_compat",
                "displayName": "平台免费额度",
                "model": "知乎直答 / 平台托管模型",
                "baseUrl": "",
                "apiKey": "",
            }

        normalized = self._normalize_llm_config(config)
        if include_secret:
            return normalized
        public = {key: value for key, value in normalized.items() if key != "apiKey"}
        public["maskedKey"] = _mask_api_key(normalized.get("apiKey"))
        return public

    def update_llm_config(self, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        """Update user's LLM configuration."""
        existing = self.get_llm_config(user_id, include_secret=True)
        config = self._normalize_llm_config(payload, existing=existing)
        if hasattr(self.repository, "save_llm_config"):
            self.repository.save_llm_config(user_id or "default", config)
        public = {key: value for key, value in config.items() if key != "apiKey"}
        public["maskedKey"] = _mask_api_key(config.get("apiKey"))
        return public

    def _normalize_llm_config(self, payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
        explicit_active_provider = (
            payload.get("activeProvider")
            or payload.get("active_provider")
            or payload.get("status")
        )

        existing = existing or {}
        base_url = payload.get("baseUrl") or payload.get("base_url") or existing.get("baseUrl") or existing.get("base_url") or ""
        model = payload.get("model") or existing.get("model") or ""
        api_key = payload.get("apiKey") or payload.get("api_key")

        active_provider = explicit_active_provider
        if active_provider == "user_configured":
            active_provider = "user_provider"
        elif active_provider == "not_configured":
            active_provider = "none"
        if active_provider not in {"platform_free", "user_provider", "none"}:
            active_provider = "user_provider" if base_url and (api_key or existing.get("apiKey") or existing.get("api_key")) else "platform_free"
        if not api_key and active_provider == "user_provider":
            api_key = existing.get("apiKey") or existing.get("api_key") or ""

        if active_provider == "user_provider":
            status = "user_configured"
            display_name = payload.get("displayName") or existing.get("displayName") or payload.get("provider") or "自有 LLM"
            model = model or "gpt-4o-mini"
        elif active_provider == "none":
            status = "not_configured"
            display_name = payload.get("displayName") or "稍后配置"
        else:
            status = "platform_free"
            display_name = payload.get("displayName") or "平台免费额度"

        return {
            "status": status,
            "activeProvider": active_provider,
            "provider": "openai_compat",
            "displayName": display_name,
            "model": model,
            "baseUrl": base_url,
            "apiKey": api_key or "",
        }
