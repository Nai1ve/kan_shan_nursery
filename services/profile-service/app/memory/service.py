from __future__ import annotations

from typing import Any

from app.profile.defaults import clone, create_id, now_iso
from app.profile.repository import ProfileRepository


GLOBAL_MEMORY_FIELDS = {"longTermBackground", "contentPreference", "writingStyle", "recommendationStrategy", "riskReminder"}
INTEREST_MEMORY_FIELDS = {
    "interestName",
    "knowledgeLevel",
    "preferredPerspective",
    "evidencePreference",
    "writingReminder",
    "feedbackSummary",
}


class MemoryNotFound(Exception):
    pass


class MemoryService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    def get_full_memory(self) -> dict[str, Any]:
        return self.repository.get_profile()

    def get_global_memory(self) -> dict[str, Any]:
        return self.repository.get_profile()["globalMemory"]

    def update_global_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_fields(payload, GLOBAL_MEMORY_FIELDS, "global memory")
        profile = self.repository.get_profile()
        profile["globalMemory"] = {**profile["globalMemory"], **payload}
        return self.repository.save_profile(profile, "update_global_memory")["globalMemory"]

    def list_interest_memories(self) -> list[dict[str, Any]]:
        return self.repository.get_profile()["interestMemories"]

    def get_interest_memory(self, interest_id: str) -> dict[str, Any]:
        profile = self.repository.get_profile()
        memory = next((item for item in profile["interestMemories"] if item["interestId"] == interest_id), None)
        if not memory:
            raise MemoryNotFound(interest_id)
        return memory

    def update_interest_memory(self, interest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_fields(payload, INTEREST_MEMORY_FIELDS | {"interestId"}, "interest memory")
        profile = self.repository.get_profile()
        updated: dict[str, Any] | None = None
        memories = []
        for memory in profile["interestMemories"]:
            if memory["interestId"] == interest_id:
                updated = self._normalize_interest_memory({**memory, **payload, "interestId": interest_id})
                memories.append(updated)
            else:
                memories.append(memory)
        if updated is None:
            updated = self._normalize_interest_memory({"interestId": interest_id, **payload})
            memories.append(updated)
        profile["interestMemories"] = memories
        self.repository.save_profile(profile, f"update_interest_memory:{interest_id}")
        return clone(updated)

    def build_injection_summary(self, interest_id: str) -> dict[str, Any]:
        profile = self.repository.get_profile()
        memory = self.get_interest_memory(interest_id)
        global_memory = profile["globalMemory"]
        display_summary = (
            f"已匹配兴趣分类画像：{memory['interestName']}。"
            f"偏好视角：{'、'.join(memory['preferredPerspective'])}；"
            f"证据偏好：{memory['evidencePreference']}；"
            f"写作提醒：{memory['writingReminder']}；"
            f"全局风格：{global_memory['writingStyle']}"
        )
        return {
            "interestId": interest_id,
            "interestMemory": memory,
            "globalMemory": global_memory,
            "displaySummary": display_summary,
            "editable": True,
        }

    def create_update_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = {"interestId", "targetField", "suggestedValue", "reason"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"missing required fields: {sorted(missing)}")
        request = {
            "id": payload.get("id") or create_id("memory-request"),
            "interestId": payload["interestId"],
            "targetField": payload["targetField"],
            "suggestedValue": payload["suggestedValue"],
            "reason": payload["reason"],
            "status": "pending",
            "createdAt": now_iso(),
        }
        return self.repository.save_update_request(request)

    def list_update_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_update_requests(status)

    def apply_update_request(self, request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        request = self._get_request_or_raise(request_id)
        suggested_value = (payload or {}).get("suggestedValue", request["suggestedValue"])
        target_field = (payload or {}).get("targetField", request["targetField"])
        interest_id = request["interestId"]
        if interest_id in {"global", "globalMemory"} or target_field.startswith("globalMemory."):
            field = target_field.split(".", 1)[-1]
            if field not in GLOBAL_MEMORY_FIELDS:
                raise ValueError(f"unsupported global memory field: {field}")
            self.update_global_memory({field: suggested_value})
        else:
            field = target_field.split(".", 1)[-1]
            if field not in INTEREST_MEMORY_FIELDS:
                raise ValueError(f"unsupported interest memory field: {field}")
            self.update_interest_memory(interest_id, {field: self._coerce_interest_value(field, suggested_value)})

        applied = {**request, "targetField": target_field, "suggestedValue": suggested_value, "status": "applied"}
        self.repository.save_update_request(applied)
        return {"request": applied, "profile": self.repository.get_profile()}

    def reject_update_request(self, request_id: str) -> dict[str, Any]:
        request = self._get_request_or_raise(request_id)
        rejected = {**request, "status": "rejected"}
        self.repository.save_update_request(rejected)
        return rejected

    def _get_request_or_raise(self, request_id: str) -> dict[str, Any]:
        request = self.repository.get_update_request(request_id)
        if not request:
            raise MemoryNotFound(request_id)
        return request

    def _normalize_interest_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        required_defaults = {
            "interestName": payload.get("interestId", "未命名兴趣"),
            "knowledgeLevel": "入门",
            "preferredPerspective": [],
            "evidencePreference": "balanced",
            "writingReminder": "",
            "feedbackSummary": "",
        }
        memory = {**required_defaults, **payload}
        if not isinstance(memory["preferredPerspective"], list):
            memory["preferredPerspective"] = [str(memory["preferredPerspective"])]
        return memory

    def _coerce_interest_value(self, field: str, value: str) -> Any:
        if field == "preferredPerspective":
            return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
        return value

    def _validate_fields(self, payload: dict[str, Any], allowed: set[str], label: str) -> None:
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ValueError(f"unsupported {label} fields: {sorted(unknown)}")
