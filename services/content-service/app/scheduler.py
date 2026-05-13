"""Background content fetcher and cache manager.

Runs on startup and every 24 hours to pre-compute content cards
from zhihu-adapter. Results are stored in Redis (if available)
or in-memory cache as fallback.
"""

from __future__ import annotations

import json
import logging
import hashlib
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

FOLLOWING_CARDS_TTL_SECONDS = 10 * 60
FOLLOWING_REFRESH_LOCK_TTL_SECONDS = 30
FOLLOWING_ENRICH_LOCK_TTL_SECONDS = 2 * 60
FOLLOWING_RAW_LIMIT = 50
FOLLOWING_CARD_LIMIT = 30


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
            logger.debug("cache_set_redis", extra={"key": key, "ttl": ttl})
            return
        except Exception as e:
            logger.debug("cache_set_redis_error", extra={"key": key, "error": str(e)})
    _memory_cache[key] = value
    logger.debug("cache_set_memory", extra={"key": key})


def _cache_setnx(key: str, value: Any, ttl: int = 60) -> bool:
    """Store value only if the key does not exist."""
    r = _get_redis()
    if r:
        try:
            return bool(r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl, nx=True))
        except Exception as e:
            logger.debug("cache_setnx_redis_error", extra={"key": key, "error": str(e)})
    existing = _memory_cache.get(key)
    if isinstance(existing, dict) and "__expiresAt" in existing:
        if existing["__expiresAt"] <= time.time():
            _memory_cache.pop(key, None)
            existing = None
    if existing is not None:
        return False
    _memory_cache[key] = {
        "__value": value,
        "__expiresAt": time.time() + max(1, ttl),
    }
    return True


def _cache_get(key: str) -> Any:
    """Get value from Redis or memory cache."""
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                logger.debug("cache_get_redis_hit", extra={"key": key})
                return json.loads(raw)
            logger.debug("cache_get_redis_miss", extra={"key": key})
        except Exception as e:
            logger.debug("cache_get_redis_error", extra={"key": key, "error": str(e)})
    result = _memory_cache.get(key)
    if isinstance(result, dict) and "__expiresAt" in result:
        if result["__expiresAt"] <= time.time():
            _memory_cache.pop(key, None)
            return None
        result = result.get("__value")
    if result:
        logger.debug("cache_get_memory_hit", extra={"key": key})
    return result


def _token_hash(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()[:16]


def _following_cards_key(user_id: str, access_token: str) -> str:
    return f"following:cards:{user_id}:{_token_hash(access_token)}"


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
        logger.info("get_cached_cards_empty")
        return []

    if category_id:
        result = cards_by_cat.get(category_id, [])
        logger.info("get_cached_cards_by_category", extra={"categoryId": category_id, "count": len(result)})
        return result

    all_cards = []
    for cards in cards_by_cat.values():
        all_cards.extend(cards)
    logger.info("get_cached_cards_all", extra={
        "categoryCount": len(cards_by_cat),
        "totalCards": len(all_cards),
    })
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


def sync_user_snapshots(profile_base_url: str = "http://127.0.0.1:8010") -> None:
    """Fetch user profiles from profile-service and update local snapshots."""
    from .snapshot import build_snapshot_from_profile, compute_source_hash
    from .snapshot_repository import SnapshotRepository

    logger.info("snapshot_sync_started", extra={"profileBaseUrl": profile_base_url})
    repo = SnapshotRepository()

    # Fetch profile data from profile-service
    logger.info("snapshot_sync_fetching_profile", extra={"url": f"{profile_base_url}/profiles/me"})
    profile_data = _fetch_profile(profile_base_url)
    if not profile_data:
        logger.warning("snapshot_sync_no_profile_data", extra={
            "hint": "profile-service 可能未启动或返回空数据",
        })
        return

    logger.info("snapshot_sync_profile_fetched", extra={
        "hasInterests": bool(profile_data.get("interests")),
        "hasInterestMemories": bool(profile_data.get("interestMemories")),
        "hasGlobalMemory": bool(profile_data.get("globalMemory")),
        "interestCount": len(profile_data.get("interests", [])),
        "memoryCount": len(profile_data.get("interestMemories", [])),
    })

    # Determine user_id (profile-service returns it in the response, or use default)
    user_id = profile_data.get("userId") or profile_data.get("user_id") or "default"
    logger.info("snapshot_sync_user_resolved", extra={"userId": user_id})

    # Get existing shown card IDs
    existing = repo.get_snapshot(user_id)
    shown_ids = existing.shown_card_ids if existing else set()
    logger.info("snapshot_sync_existing", extra={
        "userId": user_id,
        "hasExisting": existing is not None,
        "existingShownCount": len(shown_ids),
    })

    # Check if profile changed
    new_hash = compute_source_hash(profile_data)
    if existing and existing.source_hash == new_hash:
        logger.info("snapshot_sync_unchanged", extra={
            "userId": user_id,
            "hash": new_hash[:8],
        })
        return

    logger.info("snapshot_sync_changed", extra={
        "userId": user_id,
        "oldHash": (existing.source_hash[:8] if existing else "none"),
        "newHash": new_hash[:8],
    })

    # Build and save new snapshot
    snapshot = build_snapshot_from_profile(profile_data, user_id, shown_ids)
    repo.save_snapshot(snapshot)
    logger.info("snapshot_sync_saved", extra={
        "userId": user_id,
        "interestIds": snapshot.interest_ids,
        "interests": snapshot.interests,
        "shownCount": len(snapshot.shown_card_ids),
    })


def fetch_and_cache_content(
    zhihu_base_url: str = "http://127.0.0.1:8070",
    profile_base_url: str = "http://127.0.0.1:8010",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch content from zhihu-adapter, aggregate into multi-source cards, cache results.

    Returns: { category_id: [card_dict, ...] }
    """
    from .zhihu_client import ZhihuClient
    from .category_queries import build_system_queries, SPECIAL_CATEGORIES
    from .transformer import aggregate_items_to_card, transform_hot_to_card
    from .mock_data import build_categories

    logger.info("content_fetch_started", extra={"zhihuBaseUrl": zhihu_base_url})

    zhihu = ZhihuClient(zhihu_base_url)
    categories = build_categories()
    logger.info("content_fetch_categories", extra={"count": len(categories), "ids": [c["id"] for c in categories]})

    queries = build_system_queries(categories)
    logger.info("content_fetch_queries_built", extra={
        "categoryCount": len(queries),
        "queries": {k: v[:2] for k, v in queries.items()},
        "userIndependent": True,
    })

    cards_by_category: dict[str, list[dict[str, Any]]] = {}

    # Fetch hot list for serendipity
    logger.info("content_fetch_hot_list_calling")
    hot_items = zhihu.hot_list(limit=20)
    logger.info("content_fetch_hot_list_result", extra={"itemCount": len(hot_items)})
    if hot_items:
        hot_cards = [transform_hot_to_card(item) for item in hot_items[:10]]
        cards_by_category["serendipity"] = hot_cards
        logger.info("content_fetch_hot_list_done", extra={
            "count": len(hot_cards),
            "titles": [c.get("title", "")[:30] for c in hot_cards[:3]],
        })

    # Following feed is user-specific and therefore intentionally excluded
    # from the system cache. It is loaded on demand by category requests.
    cards_by_category["following"] = []

    # Fetch search results for each category with multi-source aggregation
    for cat in categories:
        cat_id = cat["id"]
        if cat_id in SPECIAL_CATEGORIES:
            logger.info("content_fetch_skip_special", extra={"categoryId": cat_id})
            continue

        cat_queries = queries.get(cat_id, [cat.get("name", cat_id)])
        all_items: list[dict[str, Any]] = []

        logger.info("content_fetch_category_start", extra={
            "categoryId": cat_id,
            "queryCount": len(cat_queries[:2]),
            "queries": cat_queries[:2],
        })

        for query in cat_queries[:2]:  # Max 2 queries per category
            logger.info("content_fetch_search_calling", extra={"categoryId": cat_id, "query": query})
            items = zhihu.search(query, count=10)
            logger.info("content_fetch_search_result", extra={
                "categoryId": cat_id,
                "query": query,
                "resultCount": len(items),
            })
            # Deduplicate by sourceId
            seen_ids = {it.get("sourceId") for it in all_items}
            for item in items:
                if item.get("sourceId") not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item.get("sourceId"))

            global_items = zhihu.global_search(query, count=10)
            logger.info("content_fetch_global_search_result", extra={
                "categoryId": cat_id,
                "query": query,
                "resultCount": len(global_items),
            })
            seen_ids = {it.get("sourceId") for it in all_items}
            for item in global_items:
                if item.get("sourceId") not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item.get("sourceId"))

        logger.info("content_fetch_category_items", extra={
            "categoryId": cat_id,
            "totalItems": len(all_items),
        })

        # Aggregate items into multi-source cards (2-3 sources per card)
        aggregated_cards: list[dict[str, Any]] = []
        for i in range(0, len(all_items), 3):
            group = all_items[i:i + 3]
            if group:
                try:
                    card = aggregate_items_to_card(group, cat_id)
                    aggregated_cards.append(card)
                except Exception as e:
                    logger.debug("content_fetch_aggregate_error", extra={"categoryId": cat_id, "error": str(e)})

        cards_by_category[cat_id] = aggregated_cards
        logger.info("content_fetch_category_done", extra={
            "categoryId": cat_id,
            "itemCount": len(all_items),
            "cardCount": len(aggregated_cards),
        })

    # Cache the raw results first
    _cache_set("kanshan:content:cards", cards_by_category)
    _cache_set("kanshan:content:last_refresh", datetime.now(timezone.utc).isoformat())
    logger.info("content_fetch_cached", extra={"categoryCount": len(cards_by_category)})

    # Clear shown set on full refresh
    r = _get_redis()
    if r:
        try:
            r.delete("kanshan:content:shown")
            logger.info("content_fetch_cleared_shown_redis")
        except Exception:
            pass
    _memory_cache["shown_ids"] = set()

    # Enrich top cards per category while building the system cache, so card
    # summaries and source key points are ready before the frontend reads them.
    logger.info("content_fetch_enrichment_start")
    _enrich_cached_cards(zhihu_base_url)

    total = sum(len(v) for v in cards_by_category.values())
    logger.info("content_fetch_completed", extra={
        "totalCards": total,
        "categories": {k: len(v) for k, v in cards_by_category.items()},
    })
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
        # Select top 3 for enrichment. This keeps cache building bounded while
        # ensuring the first screen and prefetched cards are already complete.
        top = select_top_cards(cards, max_cards=3)
        logger.info("enrich_category_start", extra={"categoryId": cat_id, "cardCount": len(cards), "topCount": len(top)})
        try:
            enricher.enrich_cards_batch(top, max_cards=3)
            # Replace the category's cards with enriched top cards + remaining raw
            remaining = [c for c in cards if c["id"] not in {t["id"] for t in top}]
            cards_by_cat[cat_id] = top + remaining
            logger.info("enrich_category_done", extra={"categoryId": cat_id, "enrichedCount": len(top)})
        except Exception as e:
            logger.warning("enrich_failed", extra={"categoryId": cat_id, "error": str(e)})

    _cache_set("kanshan:content:cards", cards_by_cat)


def fetch_following_cards(
    zhihu_base_url: str = "http://127.0.0.1:8070",
    profile_base_url: str = "http://127.0.0.1:8010",
    user_id: str = "default",
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    return fetch_following_cards_bundle(
        zhihu_base_url=zhihu_base_url,
        profile_base_url=profile_base_url,
        user_id=user_id,
        force_refresh=force_refresh,
    ).get("cards", [])


def fetch_following_cards_bundle(
    zhihu_base_url: str = "http://127.0.0.1:8070",
    profile_base_url: str = "http://127.0.0.1:8010",
    user_id: str = "default",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetch following feed for one user.

    This path is intentionally outside the system content cache because
    following feed depends on OAuth identity. It uses live OAuth data through
    zhihu-adapter; if token/config is unavailable, returns an empty list.

    Results are cached per user + token for a short TTL. The cached payload is
    card-level data, so switching tabs or pressing refresh does not repeatedly
    parse OAuth moments or call the Zhihu endpoint.
    """
    from .zhihu_client import ZhihuClient
    from .transformer import transform_following_to_card

    token_data = _fetch_zhihu_token(profile_base_url, user_id)
    access_token = token_data.get("access_token") or None
    if not access_token:
        logger.info("following_fetch_no_token", extra={"userId": user_id})
        return {"cards": [], "cacheHit": False, "cacheKey": None, "emptyReason": "no_token"}

    cache_key = _following_cards_key(user_id, access_token)
    if not force_refresh:
        cached = _cache_get(cache_key)
        if isinstance(cached, list):
            logger.info("following_cards_cache_hit", extra={"userId": user_id, "count": len(cached)})
            return {"cards": cached, "cacheHit": True, "cacheKey": cache_key}

    lock_key = f"following:refresh_lock:{user_id}"
    lock_acquired = _cache_setnx(lock_key, {"startedAt": datetime.now(timezone.utc).isoformat()}, FOLLOWING_REFRESH_LOCK_TTL_SECONDS)
    if not lock_acquired:
        cached = _cache_get(cache_key)
        logger.info("following_refresh_locked", extra={"userId": user_id, "hasCached": isinstance(cached, list)})
        return {
            "cards": cached if isinstance(cached, list) else [],
            "cacheHit": isinstance(cached, list),
            "cacheKey": cache_key,
            "refreshLocked": True,
        }

    zhihu = ZhihuClient(zhihu_base_url)
    items = zhihu.following_feed(access_token)[:FOLLOWING_RAW_LIMIT]
    cards = [_prepare_following_card(transform_following_to_card(item), item) for item in items]
    cards = sorted(cards, key=_score_following_card, reverse=True)[:FOLLOWING_CARD_LIMIT]
    _cache_set(cache_key, cards, FOLLOWING_CARDS_TTL_SECONDS)
    logger.info("following_cards_cache_write", extra={
        "userId": user_id,
        "rawCount": len(items),
        "cardCount": len(cards),
        "cacheKey": cache_key,
    })
    return {"cards": cards, "cacheHit": False, "cacheKey": cache_key}


def queue_following_enrichment(
    user_id: str,
    cache_key: str | None,
    cards: list[dict[str, Any]],
    llm_base_url: str,
    max_cards: int = 3,
) -> None:
    """Schedule short, bounded LLM enrichment for following cards."""
    if not cache_key or not cards:
        return
    lock_key = f"following:enrich_lock:{user_id}:{hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:10]}"
    if not _cache_setnx(lock_key, {"startedAt": datetime.now(timezone.utc).isoformat()}, FOLLOWING_ENRICH_LOCK_TTL_SECONDS):
        return
    thread = threading.Thread(
        target=_enrich_following_cards,
        args=(cache_key, cards, llm_base_url, max_cards),
        daemon=True,
    )
    thread.start()
    logger.info("following_enrichment_queued", extra={"userId": user_id, "cardCount": len(cards), "maxCards": max_cards})


def _enrich_following_cards(cache_key: str, cards: list[dict[str, Any]], llm_base_url: str, max_cards: int) -> None:
    from .enricher import LlmEnricher

    cached = _cache_get(cache_key)
    current_cards = cached if isinstance(cached, list) else cards
    pending = [card for card in current_cards if not card.get("enriched")][:max_cards]
    if not pending:
        return
    try:
        enricher = LlmEnricher(llm_base_url=llm_base_url)
        enricher.enrich_cards_batch(pending, max_cards=max_cards)
        enriched_by_id = {card.get("id"): {**card, "enriched": True} for card in pending}
        next_cards = [enriched_by_id.get(card.get("id"), card) for card in current_cards]
        _cache_set(cache_key, next_cards, FOLLOWING_CARDS_TTL_SECONDS)
        logger.info("following_enrichment_done", extra={"cacheKey": cache_key, "enrichedCount": len(pending)})
    except Exception as error:
        logger.warning("following_enrichment_failed", extra={"cacheKey": cache_key, "error": str(error)})


def _prepare_following_card(card: dict[str, Any], raw_item: dict[str, Any]) -> dict[str, Any]:
    action = raw_item.get("contentType") or raw_item.get("actionText") or ""
    card["enriched"] = bool(card.get("enriched"))
    card["recommendationReason"] = f"来自你关注的人近期动态：{action or '新的内容输入'}。适合判断是否值得沉淀为观点种子。"
    source = (card.get("originalSources") or [{}])[0]
    summary = source.get("rawExcerpt") or card.get("contentSummary") or card.get("title", "")
    if summary:
        card["contentSummary"] = summary[:220]
    card["controversies"] = card.get("controversies") or [
        f"这条关注流动态是否足以支撑“{card.get('title', '当前话题')}”的判断？",
        "它代表的是作者观点、社区趋势，还是个案经验？",
    ]
    card["writingAngles"] = card.get("writingAngles") or [
        f"我为什么会被这条关注流动态触发",
        f"从关注作者的讨论看“{card.get('title', '这个话题')}”",
    ]
    card["relevanceScore"] = min(98, max(card.get("relevanceScore", 70), int(_score_following_card(card))))
    return card


def _score_following_card(card: dict[str, Any]) -> float:
    source = (card.get("originalSources") or [{}])[0]
    meta_text = " ".join(str(item) for item in source.get("meta", []))
    full_content = source.get("fullContent") or source.get("rawExcerpt") or card.get("contentSummary") or ""
    score = 35.0
    if "回答" in meta_text:
        score += 20
    elif "文章" in meta_text or "发布" in meta_text:
        score += 16
    elif "赞同" in meta_text or "收藏" in meta_text:
        score += 8
    if card.get("title"):
        score += 8
    score += min(24, len(str(full_content)) / 18)
    published_at = card.get("createdAt") or source.get("publishedAt")
    score += _recency_score(published_at)
    return min(98, score)


def _recency_score(value: Any) -> float:
    if not value:
        return 4.0
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_seconds = max(0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return 4.0
    if age_seconds <= 24 * 3600:
        return 18.0
    if age_seconds <= 3 * 24 * 3600:
        return 12.0
    if age_seconds <= 7 * 24 * 3600:
        return 7.0
    return 3.0


def _fetch_profile(base_url: str) -> dict[str, Any]:
    """Fetch user profile from profile-service."""
    import urllib.request
    url = f"{base_url}/profiles/me"
    logger.info("fetch_profile_request", extra={"url": url})
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logger.info("fetch_profile_ok", extra={
                "hasData": bool(data),
                "keys": list(data.keys()) if isinstance(data, dict) else "non-dict",
            })
            return data
    except Exception as e:
        logger.warning("fetch_profile_failed", extra={"url": url, "error": str(e)})
        return {}


def _fetch_zhihu_token(profile_base_url: str, user_id: str = "default") -> dict[str, Any]:
    """Fetch zhihu access_token from profile-service internal endpoint."""
    import urllib.request
    url = f"{profile_base_url}/internal/auth/zhihu-token?user_id={user_id}"
    logger.info("fetch_zhihu_token_request", extra={"url": url, "userId": user_id})
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            has_token = bool(data.get("access_token"))
            logger.info("fetch_zhihu_token_ok", extra={"userId": user_id, "hasToken": has_token})
            return data
    except Exception as e:
        logger.warning("fetch_zhihu_token_failed", extra={"url": url, "error": str(e)})
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
