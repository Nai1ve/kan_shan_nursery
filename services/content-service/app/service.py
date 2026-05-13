from __future__ import annotations

from typing import Any

from kanshan_shared.categories import SPECIAL_CATEGORIES

from .repository import (
    CardNotFound,
    CategoryNotFound,
    ContentRepository,
    SourceNotFound,
)


def _filter_categories(categories: list[dict[str, Any]], interest_ids: list[str] | None) -> list[dict[str, Any]]:
    if not interest_ids:
        return categories
    allowed = set(interest_ids) | SPECIAL_CATEGORIES
    filtered = [cat for cat in categories if cat["id"] in allowed]
    return filtered if filtered else [c for c in categories if c["id"] in SPECIAL_CATEGORIES]


def _filter_cards(cards: list[dict[str, Any]], interest_ids: list[str] | None) -> list[dict[str, Any]]:
    if not interest_ids:
        return cards
    allowed = set(interest_ids) | SPECIAL_CATEGORIES
    return [card for card in cards if card.get("categoryId") in allowed]


class ContentService:
    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository or ContentRepository()

    def bootstrap(self, interest_ids: list[str] | None = None) -> dict[str, Any]:
        # Return all cards for bootstrap (frontend filters by category)
        # Don't apply top-N selection here; that's for per-category views
        from . import scheduler as content_scheduler
        cached = content_scheduler.get_cached_cards()
        if cached:
            cards = sorted(cached, key=lambda c: (-(c.get("relevanceScore") or 0), c["id"]))
        else:
            # No cached data - trigger synchronous fetch if scheduler hasn't populated yet
            cards = self._fetch_and_wait()
        return {
            "categories": _filter_categories(self.repository.list_categories(), interest_ids),
            "cards": _filter_cards(cards, interest_ids),
        }

    def _fetch_and_wait(self) -> list[dict[str, Any]]:
        """Trigger synchronous content fetch if cache is empty."""
        from . import scheduler as content_scheduler
        from .scheduler import fetch_and_cache_content
        import logging
        logger = logging.getLogger("kanshan.content.service")

        # Check if scheduler is running and cache is still empty
        if not content_scheduler.is_cache_populated():
            logger.info("cache_empty_triggering_sync_fetch")
            try:
                # Use default URLs from config
                from kanshan_shared import load_config
                config = load_config()
                fetch_and_cache_content(
                    zhihu_base_url=config.service_urls.zhihu,
                    profile_base_url=config.service_urls.profile,
                )
            except Exception as e:
                logger.error("sync_fetch_failed", extra={"error": str(e)})

        # Return whatever we have (could still be empty if fetch failed)
        return content_scheduler.get_cached_cards()

    def list_cards(self, category_id: str | None = None, interest_ids: list[str] | None = None) -> dict[str, Any]:
        items = self.repository.list_cards(category_id)
        if not category_id:
            items = _filter_cards(items, interest_ids)
        return {"items": items}

    def get_card(self, card_id: str) -> dict[str, Any]:
        return self.repository.get_card(card_id)

    def get_source(self, card_id: str, source_id: str) -> dict[str, Any]:
        return self.repository.get_source(card_id, source_id)

    def refresh_category(self, category_id: str) -> dict[str, Any]:
        return self.repository.refresh_category(category_id)

    def summarize_card(self, card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        card = self.repository.get_card(card_id)
        focus = (payload or {}).get("focus")
        summary_text = card.get("contentSummary", "")
        if focus:
            summary_text = f"[focus={focus}] {summary_text}"
        controversies = card.get("controversies", [])
        writing_angles = card.get("writingAngles", [])
        next_card = self.repository.update_card(
            card_id,
            {
                "contentSummary": summary_text,
                "controversies": controversies or ["mock 摘要：暂未识别明显争议"],
                "writingAngles": writing_angles or ["mock 摘要：暂未生成可写角度"],
            },
        )
        return {
            "cardId": card_id,
            "summary": next_card["contentSummary"],
            "controversies": next_card["controversies"],
            "writingAngles": next_card["writingAngles"],
            "schemaVersion": "content.summarize.v1",
        }
