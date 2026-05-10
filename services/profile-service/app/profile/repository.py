from __future__ import annotations

from typing import Any

from .defaults import clone, default_profile, default_update_requests, now_iso


class ProfileRepository:
    def __init__(self) -> None:
        self._profile: dict[str, Any] = default_profile()
        self._update_requests: dict[str, dict[str, Any]] = {
            item["id"]: item for item in default_update_requests()
        }
        self._versions: list[dict[str, Any]] = []

    def get_profile(self) -> dict[str, Any]:
        return clone(self._profile)

    def save_profile(self, profile: dict[str, Any], reason: str) -> dict[str, Any]:
        self._versions.append({"target": "profile", "snapshot": clone(self._profile), "reason": reason, "createdAt": now_iso()})
        self._profile = clone(profile)
        return self.get_profile()

    def list_versions(self) -> list[dict[str, Any]]:
        return clone(self._versions)

    def list_update_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        values = list(self._update_requests.values())
        if status:
            values = [item for item in values if item.get("status") == status]
        return clone(values)

    def get_update_request(self, request_id: str) -> dict[str, Any] | None:
        item = self._update_requests.get(request_id)
        return clone(item) if item else None

    def save_update_request(self, request: dict[str, Any]) -> dict[str, Any]:
        self._update_requests[request["id"]] = clone(request)
        return clone(request)
