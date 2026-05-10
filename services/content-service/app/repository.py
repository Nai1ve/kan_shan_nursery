from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .mock_data import build_categories, build_card, build_initial_cards, _CARD_SPECS


class CardNotFound(Exception):
    pass


class SourceNotFound(Exception):
    pass


class CategoryNotFound(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContentRepository:
    def __init__(self) -> None:
        self._cards: dict[str, dict[str, Any]] = {card["id"]: card for card in build_initial_cards()}
        self._refresh_state: dict[str, dict[str, Any]] = {}

    def list_categories(self) -> list[dict[str, Any]]:
        return build_categories()

    def list_cards(self, category_id: str | None = None) -> list[dict[str, Any]]:
        cards = list(self._cards.values())
        if category_id:
            cards = [card for card in cards if card["categoryId"] == category_id]
        return sorted(cards, key=lambda card: (-(card.get("relevanceScore") or 0), card["id"]))

    def get_card(self, card_id: str) -> dict[str, Any]:
        card = self._cards.get(card_id)
        if not card:
            raise CardNotFound(card_id)
        return card

    def get_source(self, card_id: str, source_id: str) -> dict[str, Any]:
        card = self.get_card(card_id)
        for source in card.get("originalSources", []):
            if source.get("sourceId") == source_id:
                return source
        raise SourceNotFound(source_id)

    def update_card(self, card_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        card = self.get_card(card_id)
        next_card = {**card, **patch}
        self._cards[card_id] = next_card
        return next_card

    def refresh_category(self, category_id: str) -> dict[str, Any]:
        if category_id not in CATEGORIES_BY_ID:
            raise CategoryNotFound(category_id)
        category_specs = [spec for spec in _CARD_SPECS if spec["categoryId"] == category_id]
        if not category_specs:
            raise CategoryNotFound(category_id)
        state = self._refresh_state.get(category_id, {"refreshCount": 0})
        next_count = state.get("refreshCount", 0) + 1
        existing_ids = [card["id"] for card in self._cards.values() if card["categoryId"] == category_id]
        for card_id in existing_ids:
            self._cards.pop(card_id, None)
        rotated_cards = []
        for offset, base_spec in enumerate(category_specs):
            new_card = build_card(base_spec, offset + next_count * 7)
            new_card["id"] = f"{base_spec['id']}-r{next_count}"
            new_card["createdAt"] = _now_iso()
            self._cards[new_card["id"]] = new_card
            rotated_cards.append(new_card)
        new_state = {
            "refreshCount": next_count,
            "refreshedAt": _now_iso(),
            "visibleCardIds": [card["id"] for card in rotated_cards],
        }
        self._refresh_state[category_id] = new_state
        return {"categoryId": category_id, "refreshState": new_state, "cards": rotated_cards}


CATEGORIES_BY_ID = {item["id"]: item for item in build_categories()}
