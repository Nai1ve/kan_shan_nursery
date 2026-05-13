"""Background content fetcher and cache manager.

Runs on startup and every 24 hours to pre-compute content cards
from zhihu-adapter. Results are stored in Redis (if available)
or in-memory cache as fallback.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from kanshan_shared import load_config

logger = logging.getLogger("kanshan.content.scheduler")
_config = load_config()

# In-memory cache fallback when Redis is not available
_memory_cache: dict[str, Any] = {
    "cards": {},           # category_id -> [card_dict, ...]
    "categories": [],
    "last_refresh": None,
    "shown_ids": set(),
}

_redis_client = None


def _get_redis():
    """Try to connect to Redis, return None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = _config.cache.redis_url
    if not redis_url:
        return None
    try:
        import redis
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def _cache_set(key: str, value: Any, ttl: int = 86400) -> None:
    """Store value in Redis or memory cache."""
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return
        except Exception:
            pass
    _memory_cache[key] = value


def _cache_get(key: str) -> Any:
    """Get value from Redis or memory cache."""
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    return _memory_cache.get(key)


def _cache_add_shown(card_id: str) -> None:
    """Mark a card as shown."""
    r = _get_redis()
    if r:
        try:
            r.sadd("kanshan:content:shown", card_id)
            return
        except Exception:
            pass
    _memory_cache["shown_ids"].add(card_id)


def _cache_get_shown() -> set[str]:
    """Get set of shown card IDs."""
    r = _get_redis()
    if r:
        try:
            return r.smembers("kanshan:content:shown")
        except Exception:
            pass
    return _memory_cache.get("shown_ids", set())


def get_cached_cards(category_id: str | None = None) -> list[dict[str, Any]]:
    """Get cached cards, optionally filtered by category."""
    cards_by_cat = _cache_get("kanshan:content:cards") or {}
    if not cards_by_cat:
        return []

    if category_id:
        return cards_by_cat.get(category_id, [])

    all_cards = []
    for cards in cards_by_cat.values():
        all_cards.extend(cards)
    return all_cards


def get_unshown_cards(category_id: str) -> list[dict[str, Any]]:
    """Get cards for a category that haven't been shown yet."""
    cards = get_cached_cards(category_id)
    shown = _cache_get_shown()
    return [c for c in cards if c["id"] not in shown]


def mark_card_shown(card_id: str) -> None:
    """Mark a card as shown."""
    _cache_add_shown(card_id)


def is_cache_populated() -> bool:
    """Check if the cache has been populated."""
    cards = _cache_get("kanshan:content:cards")
    return bool(cards)


def fetch_and_cache_content(
    zhihu_base_url: str = "http://127.0.0.1:8070",
    profile_base_url: str = "http://127.0.0.1:8010",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch content from zhihu-adapter, aggregate into multi-source cards, cache results.

    Returns: { category_id: [card_dict, ...] }
    """
    from .zhihu_client import ZhihuClient
    from .category_queries import extract_queries_from_profile, SPECIAL_CATEGORIES
    from .transformer import aggregate_items_to_card, transform_hot_to_card
    from .mock_data import build_categories

    logger.info("content_fetch_started")

    zhihu = ZhihuClient(zhihu_base_url)
    categories = build_categories()

    # Try to get user profile for dynamic queries
    profile = _fetch_profile(profile_base_url)
    queries = extract_queries_from_profile(profile, categories)

    cards_by_category: dict[str, list[dict[str, Any]]] = {}

    # Fetch hot list for serendipity
    logger.info("content_fetch_hot_list")
    hot_items = zhihu.hot_list(limit=20)
    if hot_items:
        hot_cards = [transform_hot_to_card(item) for item in hot_items[:10]]
        cards_by_category["serendipity"] = hot_cards
        logger.info("content_fetch_hot_list_done", extra={"count": len(hot_cards)})

    # Fetch search results for each category with multi-source aggregation
    for cat in categories:
        cat_id = cat["id"]
        if cat_id in SPECIAL_CATEGORIES:
            if cat_id == "following":
                cards_by_category[cat_id] = []
            continue

        cat_queries = queries.get(cat_id, [cat.get("name", cat_id)])
        all_items: list[dict[str, Any]] = []

        for query in cat_queries[:2]:  # Max 2 queries per category
            logger.info("content_fetch_search", extra={"categoryId": cat_id, "query": query})
            items = zhihu.search(query, count=10)
            # Deduplicate by sourceId
            seen_ids = {it.get("sourceId") for it in all_items}
            for item in items:
                if item.get("sourceId") not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item.get("sourceId"))

        # Aggregate items into multi-source cards (2-3 sources per card)
        aggregated_cards: list[dict[str, Any]] = []
        for i in range(0, len(all_items), 3):
            group = all_items[i:i + 3]
            if group:
                try:
                    card = aggregate_items_to_card(group, cat_id)
                    aggregated_cards.append(card)
                except Exception:
                    pass

        cards_by_category[cat_id] = aggregated_cards
        logger.info("content_fetch_category_done", extra={"categoryId": cat_id, "count": len(aggregated_cards)})

    # Cache the raw results first
    _cache_set("kanshan:content:cards", cards_by_category)
    _cache_set("kanshan:content:last_refresh", datetime.now(timezone.utc).isoformat())

    # Clear shown set on full refresh
    r = _get_redis()
    if r:
        try:
            r.delete("kanshan:content:shown")
        except Exception:
            pass
    _memory_cache["shown_ids"] = set()

    # Enrich top cards per category with LLM (async, non-blocking)
    _enrich_cached_cards(zhihu_base_url)

    total = sum(len(v) for v in cards_by_category.values())
    logger.info("content_fetch_completed", extra={"totalCards": total})
    return cards_by_category


def _enrich_cached_cards(zhihu_base_url: str = "http://127.0.0.1:8070") -> None:
    """Enrich top cached cards with LLM-generated content."""
    from .enricher import LlmEnricher
    from .scorer import select_top_cards

    llm_url = _config.service_urls.llm
    enricher = LlmEnricher(llm_base_url=llm_url)

    cards_by_cat = _cache_get("kanshan:content:cards") or {}
    for cat_id, cards in cards_by_cat.items():
        if cat_id in ("following",) or not cards:
            continue
        # Select top 5 for enrichment
        top = select_top_cards(cards, max_cards=5)
        try:
            enricher.enrich_cards_batch(top, max_cards=5)
            # Replace the category's cards with enriched top cards + remaining raw
            remaining = [c for c in cards if c["id"] not in {t["id"] for t in top}]
            cards_by_cat[cat_id] = top + remaining
        except Exception as e:
            logger.warning("enrich_failed", extra={"categoryId": cat_id, "error": str(e)})

    _cache_set("kanshan:content:cards", cards_by_cat)


def _fetch_profile(base_url: str) -> dict[str, Any]:
    """Fetch user profile from profile-service."""
    import urllib.request
    try:
        url = f"{base_url}/profiles/me"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


class ContentScheduler:
    """Background scheduler for periodic content fetching."""

    def __init__(
        self,
        zhihu_base_url: str = "http://127.0.0.1:8070",
        profile_base_url: str = "http://127.0.0.1:8010",
        interval_hours: int = 24,
    ) -> None:
        self.zhihu_base_url = zhihu_base_url
        self.profile_base_url = profile_base_url
        self.interval_hours = interval_hours
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the background scheduler."""
        # Start periodic thread (includes initial fetch after delay)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("content_scheduler_started", extra={"interval_hours": self.interval_hours})

    def stop(self) -> None:
        """Stop the scheduler."""
        self._stop_event.set()

    def _run_loop(self) -> None:
        """Background loop: initial fetch after 3s delay, then every interval_hours."""
        # Wait for other services to start
        for _ in range(3):
            if self._stop_event.is_set():
                return
            time.sleep(1)
        self._run_fetch()

        while not self._stop_event.is_set():
            for _ in range(self.interval_hours * 3600):
                if self._stop_event.is_set():
                    return
                time.sleep(1)
            self._run_fetch()

    def _run_fetch(self) -> None:
        """Execute a content fetch."""
        try:
            fetch_and_cache_content(self.zhihu_base_url, self.profile_base_url)
        except Exception as e:
            logger.error("content_fetch_error", extra={"error": str(e)})
