from __future__ import annotations

from typing import Any

from . import seed_logic
from .repository import SeedRepository


QUESTION_STATUSES = {"answered", "resolved", "needs_material"}
MATERIAL_TYPES = {"evidence", "counterargument", "personal_experience", "open_question"}


class SeedNotFound(Exception):
    pass


class SeedService:
    def __init__(self, repository: SeedRepository | None = None, llm_client=None) -> None:
        self.repository = repository or SeedRepository()
        self.llm_client = llm_client

    def list_seeds(self, user_id: str | None = None) -> list[dict[str, Any]]:
        items = self.repository.list()
        if user_id is None:
            return items
        # Keep seeds with no userId (fixtures / legacy) visible to everyone.
        return [seed for seed in items if not seed.get("userId") or seed.get("userId") == user_id]

    def get_seed(self, seed_id: str) -> dict[str, Any]:
        seed = self.repository.get(seed_id)
        if not seed:
            raise SeedNotFound(seed_id)
        return seed

    def create_manual_seed(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repository.save(seed_logic.build_manual_seed(payload))

    def update_seed(self, seed_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        seed = self.get_seed(seed_id)
        next_seed = seed_logic.recalc_seed({**seed, **patch, "updatedAt": seed_logic.now_iso()})
        return self.repository.save(next_seed)

    def from_card(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "cardId" not in payload or "reaction" not in payload:
            raise ValueError("cardId and reaction are required")
        card_id = payload["cardId"]
        user_id = payload.get("userId")
        seed_id_hint = payload.get("seedId") or payload.get("id")
        existing = self.repository.find_by_card_id(card_id)
        if existing:
            next_seed = seed_logic.recalc_seed(
                {
                    **existing,
                    "userId": user_id or existing.get("userId"),
                    "userReaction": payload["reaction"],
                    "userNote": payload.get("userNote", existing.get("userNote", "")),
                    "updatedAt": seed_logic.now_iso(),
                }
            )
            return self.repository.save(next_seed)

        card = payload.get("card") or self._fallback_card(card_id)
        seed = seed_logic.build_seed_from_card(
            card,
            payload["reaction"],
            payload.get("userNote"),
            seed_id=seed_id_hint,
            user_id=user_id,
        )
        return self.repository.save(seed)

    def add_question(self, seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("question"):
            raise ValueError("question is required")
        seed = self.get_seed(seed_id)
        next_seed = seed_logic.answer_question(seed, payload["question"], payload.get("parentQuestionId"), llm_client=self.llm_client)
        return self.repository.save(next_seed)

    def mark_question(self, seed_id: str, question_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("status") not in QUESTION_STATUSES:
            raise ValueError(f"status must be one of {sorted(QUESTION_STATUSES)}")
        seed = self.get_seed(seed_id)
        next_seed = seed_logic.mark_question(seed, question_id, payload["status"])
        return self.repository.save(next_seed)

    def add_material(self, seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("type") not in MATERIAL_TYPES:
            raise ValueError(f"type must be one of {sorted(MATERIAL_TYPES)}")
        seed = self.get_seed(seed_id)
        material = seed_logic.build_material(
            payload["type"],
            payload["title"],
            payload["content"],
            payload.get("sourceLabel", "手动补充"),
            payload.get("adopted", False),
        )
        next_seed = seed_logic.recalc_seed({**seed, "wateringMaterials": [material, *seed.get("wateringMaterials", [])], "updatedAt": seed_logic.now_iso()})
        return self.repository.save(next_seed)

    def update_material(self, seed_id: str, material_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        seed = self.get_seed(seed_id)
        if not any(item.get("id") == material_id for item in seed.get("wateringMaterials", [])):
            raise ValueError(f"material not found: {material_id}")
        if "type" in patch and patch["type"] not in MATERIAL_TYPES:
            raise ValueError(f"type must be one of {sorted(MATERIAL_TYPES)}")
        next_seed = {
            **seed,
            "wateringMaterials": [
                {**item, **patch} if item.get("id") == material_id else item
                for item in seed.get("wateringMaterials", [])
            ],
            "updatedAt": seed_logic.now_iso(),
        }
        return self.repository.save(seed_logic.recalc_seed(next_seed))

    def delete_material(self, seed_id: str, material_id: str) -> dict[str, Any]:
        seed = self.get_seed(seed_id)
        if not any(item.get("id") == material_id for item in seed.get("wateringMaterials", [])):
            raise ValueError(f"material not found: {material_id}")
        next_seed = {
            **seed,
            "wateringMaterials": [item for item in seed.get("wateringMaterials", []) if item.get("id") != material_id],
            "updatedAt": seed_logic.now_iso(),
        }
        return self.repository.save(seed_logic.recalc_seed(next_seed))

    def agent_supplement(self, seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        seed = self.get_seed(seed_id)
        material_type = payload.get("type", "evidence")
        if material_type not in {"evidence", "counterargument"}:
            raise ValueError("Agent supplement only supports evidence or counterargument")
        return self.repository.save(seed_logic.agent_supplement(seed, material_type, llm_client=self.llm_client))

    def merge(self, target_seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        target = self.get_seed(target_seed_id)
        source = self.get_seed(payload["sourceSeedId"])
        merged = seed_logic.recalc_seed(
            {
                **target,
                "possibleAngles": list(dict.fromkeys([*target.get("possibleAngles", []), *source.get("possibleAngles", [])])),
                "counterArguments": list(dict.fromkeys([*target.get("counterArguments", []), *source.get("counterArguments", [])])),
                "requiredMaterials": list(dict.fromkeys([*target.get("requiredMaterials", []), *source.get("requiredMaterials", [])])),
                "wateringMaterials": [*target.get("wateringMaterials", []), *source.get("wateringMaterials", [])],
                "questions": [*target.get("questions", []), *source.get("questions", [])],
                "userNote": f"{target.get('userNote', '')}\n合并补充：{source.get('userNote', '')}",
                "updatedAt": seed_logic.now_iso(),
            }
        )
        self.repository.delete(source["id"])
        return self.repository.save(merged)

    def _fallback_card(self, card_id: str) -> dict[str, Any]:
        return {
            "id": card_id,
            "categoryId": "manual",
            "tags": [{"label": "fallback", "tone": "blue"}],
            "title": f"内容卡片 {card_id}",
            "contentSummary": "调用方未传入完整 card payload，seed-service 使用 fallback card。",
            "controversies": ["需要补充反方观点"],
            "writingAngles": [f"围绕 {card_id} 形成一个可写观点"],
            "originalSources": [],
        }
