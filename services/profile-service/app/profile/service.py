from __future__ import annotations

from typing import Any

from .defaults import INTERESTS, interest_memory, now_iso
from .repository import ProfileRepository


PROFILE_FIELDS = {"nickname", "accountStatus", "role", "interests", "avoidances", "globalMemory", "interestMemories"}


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    def get_profile(self) -> dict[str, Any]:
        return self.repository.get_profile()

    def update_profile(self, payload: dict[str, Any], reason: str = "update_profile") -> dict[str, Any]:
        unknown = set(payload.keys()) - PROFILE_FIELDS
        if unknown:
            raise ValueError(f"unsupported profile fields: {sorted(unknown)}")
        profile = self.repository.get_profile()
        next_profile = {**profile, **payload}
        return self.repository.save_profile(next_profile, reason)

    def save_onboarding(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        selected_interests = payload.get("selectedInterests", [])
        writing_style = payload.get("writingStyle", {})

        # Build interest list from selected interests
        interest_map = {item[0]: item for item in INTERESTS}
        interests = []
        interest_memories = []

        for si in selected_interests:
            if not si.get("selected", True):
                continue
            interest_id = si.get("interestId", "")
            interest_info = interest_map.get(interest_id)
            if interest_info:
                interests.append(interest_info[1])  # interest name
                knowledge_level = si.get("selfRatedLevel", "intermediate")
                level_map = {"beginner": "入门", "intermediate": "中级", "advanced": "进阶"}
                interest_memories.append(interest_memory(
                    interest_id=interest_id,
                    interest_name=interest_info[1],
                    knowledge_level=level_map.get(knowledge_level, "中级"),
                    preferred_perspective=interest_info[3],  # default perspectives
                    evidence_preference=interest_info[4],  # default evidence preference
                    writing_reminder=interest_info[5],  # default writing reminder
                ))

        # If no interests selected, use defaults
        if not interests:
            interests = [item[1] for item in INTERESTS if item[0] not in {"following", "serendipity"}]
            interest_memories = [interest_memory(*item) for item in INTERESTS if item[0] not in {"following", "serendipity"}]

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
        }

        # Save directly (bypass update_profile validation)
        saved_profile = self.repository.save_profile(profile, "onboarding")
        return {
            "profile": saved_profile,
            "profileStatus": "provisional",
            "enrichmentJob": None,
        }
