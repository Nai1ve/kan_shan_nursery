from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .mock_data import build_categories
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
        else:
            # No cached data - show empty state
            for cat in categories:
                if cat["id"] not in ("following", "serendipity"):
                    cat["meta"] = "暂无数据"
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

        # No cached data - return empty list (no mock fallback)
        return []

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
        # No cached data - card not found
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
        # Note: This only updates the in-memory representation for the current request
        # The cache in scheduler is not updated (would need cache invalidation)
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

        # No more unshown cards - try to fetch new content
        new_cards = self._fetch_new_content_for_category(category_id)
        if new_cards:
            return {
                "categoryId": category_id,
                "refreshState": {
                    "refreshCount": 1,
                    "refreshedAt": _now_iso(),
                    "source": "fresh",
                },
                "cards": new_cards,
            }

        # Still no cards - return empty
        return {
            "categoryId": category_id,
            "refreshState": {
                "refreshCount": 0,
                "refreshedAt": _now_iso(),
                "source": "cache",
            },
            "cards": [],
        }

    def _fetch_new_content_for_category(self, category_id: str) -> list[dict[str, Any]]:
        """Fetch new content for a specific category from zhihu-adapter."""
        import logging
        logger = logging.getLogger("kanshan.content.repository")

        try:
            from .scheduler import fetch_and_cache_content
            from kanshan_shared import load_config
            config = load_config()

            # Fetch new content (this will update the cache)
            logger.info("fetching_new_content", extra={"categoryId": category_id})
            cards_by_category = fetch_and_cache_content(
                zhihu_base_url=config.service_urls.zhihu,
                profile_base_url=config.service_urls.profile,
            )

            # Return cards for the requested category
            new_cards = cards_by_category.get(category_id, [])
            if new_cards:
                # Mark these as shown
                for card in new_cards:
                    content_scheduler.mark_card_shown(card["id"])
                logger.info("new_content_fetched", extra={"categoryId": category_id, "count": len(new_cards)})

            return new_cards
        except Exception as e:
            logger.error("fetch_new_content_failed", extra={"categoryId": category_id, "error": str(e)})
            return []


CATEGORIES_BY_ID = {item["id"]: item for item in build_categories()}
