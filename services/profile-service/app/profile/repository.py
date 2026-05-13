from __future__ import annotations

from typing import Any

from .defaults import clone, default_profile, default_update_requests, now_iso


class ProfileRepository:
    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}
        self._update_requests: dict[str, dict[str, dict[str, Any]]] = {}
        self._versions: list[dict[str, Any]] = []
        self._llm_configs: dict[str, dict[str, Any]] = {}

    def _profile_key(self, user_id: str | None) -> str:
        return user_id or "default"

    def _get_or_create_profile(self, user_id: str | None) -> dict[str, Any]:
        key = self._profile_key(user_id)
        if key not in self._profiles:
            self._profiles[key] = default_profile()
        return clone(self._profiles[key])

    def get_profile(self, user_id: str | None = None) -> dict[str, Any]:
        return self._get_or_create_profile(user_id)

    def save_profile(self, profile: dict[str, Any], reason: str, user_id: str | None = None) -> dict[str, Any]:
        key = self._profile_key(user_id or profile.get("userId"))
        self._versions.append({"target": key, "snapshot": clone(self._profiles.get(key, {})), "reason": reason, "createdAt": now_iso()})
        self._profiles[key] = clone(profile)
        return clone(profile)

    def list_versions(self) -> list[dict[str, Any]]:
        return clone(self._versions)

    def list_update_requests(self, status: str | None = None, user_id: str | None = None) -> list[dict[str, Any]]:
        user_requests = self._update_requests.get(user_id or "default", {})
        values = list(user_requests.values())
        if status:
            values = [item for item in values if item.get("status") == status]
        return clone(values)

    def get_update_request(self, request_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        user_requests = self._update_requests.get(user_id or "default", {})
        item = user_requests.get(request_id)
        return clone(item) if item else None

    def save_update_request(self, request: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        target_user_id = user_id or request.get("userId") or "default"
        if target_user_id not in self._update_requests:
            self._update_requests[target_user_id] = {}
        self._update_requests[target_user_id][request["id"]] = clone(request)
        return clone(request)

    def get_llm_config(self, user_id: str | None = None) -> dict[str, Any] | None:
        config = self._llm_configs.get(self._profile_key(user_id))
        return clone(config) if config else None

    def save_llm_config(self, user_id: str | None, config: dict[str, Any]) -> dict[str, Any]:
        key = self._profile_key(user_id)
        self._llm_configs[key] = clone(config)
        return clone(config)
