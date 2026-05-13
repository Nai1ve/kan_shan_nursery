from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .mock_data import build_categories
from . import scheduler as content_scheduler

logger = logging.getLogger("kanshan.content.repository")


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
        self._enricher = enricher
        self._profile_service_url = profile_service_url
        self._enriched_cache: dict[str, list[dict[str, Any]]] = {}

    def list_categories(self) -> list[dict[str, Any]]:
        categories = build_categories()
        cached = content_scheduler.get_cached_cards()
        if cached:
            counts: dict[str, int] = {}
            if isinstance(cached, dict):
                for cards in cached.values():
                    for card in cards:
                        cid = card.get("categoryId", "")
                        counts[cid] = counts.get(cid, 0) + 1
            else:
                for card in cached:
                    cid = card.get("categoryId", "")
                    counts[cid] = counts.get(cid, 0) + 1
            for cat in categories:
                cid = cat["id"]
                count = counts.get(cid, 0)
                if count > 0:
                    cat["meta"] = f"{count} 张卡"
        else:
            for cat in categories:
                if cat["id"] not in ("serendipity",):
                    cat["meta"] = "暂无动态" if cat["id"] == "following" else "暂无数据"
        return categories

    def list_cards(
        self,
        category_id: str | None = None,
        interest_memories: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        logger.info("repo_list_cards", extra={"categoryId": category_id, "userId": user_id})

        # Request-time card listing must not wait on LLM. The scheduler and
        # on-demand enrichment endpoint update the shared cache asynchronously.
        cached = content_scheduler.get_cached_cards(category_id)
        if cached:
            logger.info("repo_list_cards_raw_cache_hit", extra={"categoryId": category_id, "count": len(cached)})
            from .scorer import select_top_cards

            interest_memory = None
            if interest_memories and category_id:
                for mem in interest_memories:
                    if mem.get("interestId") == category_id:
                        interest_memory = mem
                        break

            if interest_memory:
                logger.info("repo_list_cards_using_memory", extra={
                    "categoryId": category_id,
                    "interestName": interest_memory.get("interestName", ""),
                })

            top = select_top_cards(cached, interest_memory=interest_memory, max_cards=5)
            logger.info("repo_list_cards_selected_top", extra={
                "categoryId": category_id,
                "topCount": len(top),
                "topIds": [c["id"] for c in top],
            })
            return top

        # No cached data - return empty list
        logger.info("repo_list_cards_empty", extra={"categoryId": category_id})
        return []

    def clear_enriched_cache(self, category_id: str | None = None) -> None:
        """Clear enriched cache for a category or all."""
        if category_id:
            self._enriched_cache.pop(category_id, None)
        else:
            self._enriched_cache.clear()

    def get_card(self, card_id: str) -> dict[str, Any]:
        cached = content_scheduler.get_cached_cards()
        if isinstance(cached, dict):
            all_cards = []
            for cards in cached.values():
                all_cards.extend(cards)
            cached = all_cards
        for card in cached:
            if card["id"] == card_id:
                return card
        raise CardNotFound(card_id)

    def get_source(self, card_id: str, source_id: str) -> dict[str, Any]:
        card = self.get_card(card_id)
        for source in card.get("originalSources", []):
            if source.get("sourceId") == source_id:
                return source
        raise SourceNotFound(source_id)

    def update_card(self, card_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        card = self.get_card(card_id)
        next_card = {**card, **patch}
        return next_card

    def _fetch_new_content_for_category(self, category_id: str) -> list[dict[str, Any]]:
        """Fetch new content for a specific category from zhihu-adapter."""
        try:
            from .scheduler import fetch_and_cache_content
            from kanshan_shared import load_config

            config = load_config()

            logger.info("repo_fetch_new_content", extra={"categoryId": category_id})
            cards_by_category = fetch_and_cache_content(
                zhihu_base_url=config.service_urls.zhihu,
                profile_base_url=config.service_urls.profile,
            )

            new_cards = cards_by_category.get(category_id, [])
            logger.info("repo_fetch_new_content_result", extra={
                "categoryId": category_id,
                "newCardCount": len(new_cards),
            })
            if new_cards:
                for card in new_cards:
                    content_scheduler.mark_card_shown(card["id"])
                logger.info("repo_fetch_new_content_marked", extra={
                    "categoryId": category_id,
                    "count": len(new_cards),
                })

            return new_cards
        except Exception as e:
            logger.error("repo_fetch_new_content_failed", extra={"categoryId": category_id, "error": str(e)})
            return []


CATEGORIES_BY_ID = {item["id"]: item for item in build_categories()}
