from __future__ import annotations

from typing import Any

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
        return self.update_profile(payload, "onboarding")
