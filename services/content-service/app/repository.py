from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .mock_data import build_categories, build_card, build_initial_cards, _CARD_SPECS
from . import scheduler as content_scheduler


class CardNotFound(Exception):
    pass


class SourceNotFound(Exception):
    pass


class CategoryNotFound(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContentRepository:
    def __init__(self, enricher: Any = None, profile_service_url: str = "") -> None:
        self._cards: dict[str, dict[str, Any]] = {card["id"]: card for card in build_initial_cards()}
        self._refresh_state: dict[str, dict[str, Any]] = {}
        self._enricher = enricher
        self._profile_service_url = profile_service_url
        self._enriched_cache: dict[str, list[dict[str, Any]]] = {}

    def list_categories(self) -> list[dict[str, Any]]:
        categories = build_categories()
        cached = content_scheduler.get_cached_cards()
        if cached:
            counts: dict[str, int] = {}
            for card in cached:
                cid = card.get("categoryId", "")
                counts[cid] = counts.get(cid, 0) + 1
            for cat in categories:
                cid = cat["id"]
                count = counts.get(cid, 0)
                if cid == "following":
                    cat["meta"] = "需知乎关联"
                elif count > 0:
                    cat["meta"] = f"{count} 张卡"
        return categories

    def list_cards(self, category_id: str | None = None) -> list[dict[str, Any]]:
        # Try enriched cache first
        if category_id and category_id in self._enriched_cache:
            return self._enriched_cache[category_id]

        # Try raw cache
        cached = content_scheduler.get_cached_cards(category_id)
        if cached:
            # Score and select top cards
            from .scorer import select_top_cards
            top = select_top_cards(cached, max_cards=5)

            # Enrich with LLM if available
            if self._enricher and top:
                interest_memory = self._get_interest_memory(category_id)
                try:
                    self._enricher.enrich_cards_batch(top, interest_memory, max_cards=5)
                except Exception:
                    pass
                # Cache enriched results
                if category_id:
                    self._enriched_cache[category_id] = top

            return top

        # Fall back to mock data (no card limit for mock)
        cards = list(self._cards.values())
        if category_id:
            cards = [card for card in cards if card["categoryId"] == category_id]
        return sorted(cards, key=lambda card: (-(card.get("relevanceScore") or 0), card["id"]))

    def _get_interest_memory(self, category_id: str | None) -> dict[str, Any] | None:
        """Get per-interest memory from profile-service."""
        if not category_id or not self._profile_service_url:
            return None
        import json
        import urllib.request
        try:
            url = f"{self._profile_service_url}/memory/me/interests/{category_id}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def clear_enriched_cache(self, category_id: str | None = None) -> None:
        """Clear enriched cache for a category or all."""
        if category_id:
            self._enriched_cache.pop(category_id, None)
        else:
            self._enriched_cache.clear()

    def get_card(self, card_id: str) -> dict[str, Any]:
        # Try cache first
        cached = content_scheduler.get_cached_cards()
        for card in cached:
            if card["id"] == card_id:
                return card
        # Fall back to mock
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

        # Try to get unshown cached cards
        unshown = content_scheduler.get_unshown_cards(category_id)
        if unshown:
            # Mark as shown and return
            for card in unshown:
                content_scheduler.mark_card_shown(card["id"])
            return {
                "categoryId": category_id,
                "refreshState": {
                    "refreshCount": 1,
                    "refreshedAt": _now_iso(),
                    "source": "cache",
                },
                "cards": unshown,
            }

        # Fall back to mock data refresh
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
