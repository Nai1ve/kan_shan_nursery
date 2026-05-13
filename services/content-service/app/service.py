from __future__ import annotations

import logging
from typing import Any

from kanshan_shared.categories import SPECIAL_CATEGORIES

from .repository import (
    CardNotFound,
    CategoryNotFound,
    ContentRepository,
    SourceNotFound,
)
from .snapshot_repository import SnapshotRepository

logger = logging.getLogger("kanshan.content.service")


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


def _find_matching_memory(
    card: dict[str, Any],
    interest_memories: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the interest memory that best matches a card's category."""
    cat_id = card.get("categoryId", "")
    for mem in interest_memories:
        if mem.get("interestId") == cat_id:
            return mem
    return None


class ContentService:
    def __init__(
        self,
        repository: ContentRepository | None = None,
        snapshot_repo: SnapshotRepository | None = None,
    ) -> None:
        self.repository = repository or ContentRepository()
        self.snapshot_repo = snapshot_repo or SnapshotRepository()

    def bootstrap(
        self,
        user_id: str | None = None,
        interest_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        logger.info("bootstrap_start", extra={"userId": user_id, "paramInterestIds": interest_ids})

        # Resolve snapshot if user_id provided
        snapshot = self.snapshot_repo.get_snapshot(user_id) if user_id else None

        # Determine interests: prefer snapshot over query param
        if snapshot and snapshot.interest_ids:
            effective_interest_ids = snapshot.interest_ids
            logger.info("bootstrap_using_snapshot_interests", extra={
                "userId": user_id,
                "snapshotInterestIds": snapshot.interest_ids,
                "snapshotInterests": snapshot.interests,
            })
        else:
            effective_interest_ids = interest_ids
            logger.info("bootstrap_using_param_interests", extra={
                "userId": user_id,
                "paramInterestIds": interest_ids,
                "hasSnapshot": snapshot is not None,
            })

        # Get system content pool
        from . import scheduler as content_scheduler

        cached = content_scheduler.get_cached_cards()

        if cached:
            if isinstance(cached, dict):
                all_cards = []
                for cards in cached.values():
                    all_cards.extend(cards)
                cards = sorted(all_cards, key=lambda c: (-(c.get("relevanceScore") or 0), c["id"]))
            else:
                cards = sorted(cached, key=lambda c: (-(c.get("relevanceScore") or 0), c["id"]))
            logger.info("bootstrap_cache_hit", extra={"totalCards": len(cards)})
        else:
            logger.info("bootstrap_cache_empty_triggering_fetch")
            cards = self._fetch_and_wait()
            logger.info("bootstrap_fetch_done", extra={"totalCards": len(cards)})

        # Filter by user interests
        before_filter = len(cards)
        cards = _filter_cards(cards, effective_interest_ids)
        logger.info("bootstrap_filtered", extra={
            "beforeFilter": before_filter,
            "afterFilter": len(cards),
            "interestIds": effective_interest_ids,
        })

        # Score using snapshot's interest_memories
        interest_memories = snapshot.interest_memories if snapshot else []
        shown_ids = snapshot.shown_card_ids if snapshot else set()

        from .scorer import score_card

        for card in cards:
            memory = _find_matching_memory(card, interest_memories)
            card["_score"] = score_card(card, memory)

        # Sort by score, exclude shown, take current card + one prefetched card.
        ranked = sorted(cards, key=lambda c: c.get("_score", 0), reverse=True)
        top_cards = [c for c in ranked if c["id"] not in shown_ids][:2]

        logger.info("bootstrap_selected", extra={
            "rankedCount": len(ranked),
            "shownExcluded": len(shown_ids),
            "selectedCount": len(top_cards),
            "selectedIds": [c["id"] for c in top_cards],
            "selectedTitles": [c.get("title", "")[:40] for c in top_cards],
            "selectedCategories": [c.get("categoryId", "") for c in top_cards],
            "selectedScores": [round(c.get("_score", 0), 1) for c in top_cards],
        })

        # Clean internal score field and mark enrichment status
        for card in top_cards:
            card.pop("_score", None)
            card["enriched"] = False

        # Do not call LLM or mark cards shown here. Frontend displays one card
        # and prefetches one card; on-demand enrich runs in the background.

        categories = _filter_categories(self.repository.list_categories(), effective_interest_ids)
        logger.info("bootstrap_done", extra={
            "userId": user_id,
            "categoryCount": len(categories),
            "cardCount": len(top_cards),
        })

        return {
            "categories": categories,
            "cards": top_cards,
        }

    def _fetch_and_wait(self) -> list[dict[str, Any]]:
        """Trigger synchronous content fetch if cache is empty."""
        from . import scheduler as content_scheduler
        from .scheduler import fetch_and_cache_content

        if not content_scheduler.is_cache_populated():
            logger.info("cache_empty_triggering_sync_fetch")
            try:
                from kanshan_shared import load_config

                config = load_config()
                fetch_and_cache_content(
                    zhihu_base_url=config.service_urls.zhihu,
                    profile_base_url=config.service_urls.profile,
                )
            except Exception as e:
                logger.error("sync_fetch_failed", extra={"error": str(e)})

        result = content_scheduler.get_cached_cards()
        if isinstance(result, dict):
            all_cards = []
            for cards in result.values():
                all_cards.extend(cards)
            return all_cards
        return result

    def _update_card_in_cache(self, enriched_card: dict[str, Any]) -> None:
        """Write enriched card fields back to the scheduler cache."""
        from . import scheduler as content_scheduler
        try:
            cards_by_cat = content_scheduler._cache_get("kanshan:content:cards") or {}
            card_id = enriched_card.get("id", "")
            for cat_id, cards in cards_by_cat.items():
                for i, card in enumerate(cards):
                    if card.get("id") == card_id:
                        # Update only enriched fields
                        cards[i]["contentSummary"] = enriched_card.get("contentSummary", "")
                        cards[i]["recommendationReason"] = enriched_card.get("recommendationReason", "")
                        cards[i]["controversies"] = enriched_card.get("controversies", [])
                        cards[i]["writingAngles"] = enriched_card.get("writingAngles", [])
                        cards[i]["originalSources"] = enriched_card.get("originalSources", card.get("originalSources", []))
                        cards[i]["enriched"] = True
                        content_scheduler._cache_set("kanshan:content:cards", cards_by_cat)
                        logger.info("update_card_in_cache", extra={"cardId": card_id, "categoryId": cat_id})
                        return
        except Exception as e:
            logger.warning("update_card_in_cache_failed", extra={"error": str(e)})

    def enrich_card_on_demand(self, card_id: str, user_id: str | None = None) -> dict[str, Any]:
        """Enrich a single card on demand (TikTok-style progressive loading)."""
        logger.info("enrich_on_demand_start", extra={"cardId": card_id, "userId": user_id})

        # Get card from cache
        from . import scheduler as content_scheduler

        all_cards = content_scheduler.get_cached_cards()
        if isinstance(all_cards, dict):
            flat = []
            for cards in all_cards.values():
                flat.extend(cards)
            all_cards = flat

        card = None
        for c in all_cards:
            if c.get("id") == card_id:
                card = c
                break

        if not card:
            raise CardNotFound(card_id)

        # Already enriched - return immediately. Cards have source-derived
        # summaries before LLM runs, so contentSummary alone is not enough.
        if card.get("enriched"):
            logger.info("enrich_on_demand_already_enriched", extra={"cardId": card_id})
            return card

        # Get interest memory for personalization
        snapshot = self.snapshot_repo.get_snapshot(user_id) if user_id else None
        interest_memories = snapshot.interest_memories if snapshot else []
        interest_memory = _find_matching_memory(card, interest_memories)

        # Enrich with LLM
        try:
            from .enricher import LlmEnricher
            from kanshan_shared import load_config
            config = load_config()
            enricher = LlmEnricher(llm_base_url=config.service_urls.llm)
            enricher.enrich_card(card, interest_memory)
            card["enriched"] = True

            # Write back to cache
            self._update_card_in_cache(card)
            logger.info("enrich_on_demand_done", extra={
                "cardId": card_id,
                "summaryLen": len(card.get("contentSummary", "")),
                "controversyCount": len(card.get("controversies", [])),
                "angleCount": len(card.get("writingAngles", [])),
            })
        except Exception as e:
            logger.warning("enrich_on_demand_failed", extra={"cardId": card_id, "error": str(e)})

        return card

    def list_cards(
        self,
        category_id: str | None = None,
        user_id: str | None = None,
        interest_ids: list[str] | None = None,
        limit: int = 5,
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        logger.info("list_cards_start", extra={
            "categoryId": category_id,
            "userId": user_id,
            "limit": limit,
        })

        if category_id == "following":
            return self._list_following_cards(user_id=user_id, limit=limit, exclude_ids=exclude_ids)

        # Resolve snapshot
        snapshot = self.snapshot_repo.get_snapshot(user_id) if user_id else None
        interest_memories = snapshot.interest_memories if snapshot else []
        shown_ids = snapshot.shown_card_ids if snapshot else set()
        if exclude_ids:
            shown_ids = set(shown_ids) | set(exclude_ids)

        # Get cards from repository (uses system content pool)
        items = self.repository.list_cards(
            category_id,
            interest_memories=interest_memories,
            user_id=user_id,
        )
        logger.info("list_cards_from_repo", extra={"categoryId": category_id, "count": len(items)})

        # Filter by interests if no category specified
        if not category_id:
            effective_interest_ids = (snapshot.interest_ids if snapshot and snapshot.interest_ids else interest_ids)
            items = _filter_cards(items, effective_interest_ids)

        # Exclude shown cards
        before_exclude = len(items)
        items = [c for c in items if c["id"] not in shown_ids]

        # Limit
        items = items[:limit]

        logger.info("list_cards_done", extra={
            "categoryId": category_id,
            "beforeExclude": before_exclude,
            "afterExclude": len(items),
            "shownCount": len(shown_ids),
            "resultIds": [c["id"] for c in items],
        })

        return {"items": items, "prefetchCount": max(0, len(items) - 1)}

    def get_card(self, card_id: str) -> dict[str, Any]:
        logger.debug("get_card", extra={"cardId": card_id})
        return self.repository.get_card(card_id)

    def get_source(self, card_id: str, source_id: str) -> dict[str, Any]:
        logger.debug("get_source", extra={"cardId": card_id, "sourceId": source_id})
        return self.repository.get_source(card_id, source_id)

    def refresh_category(
        self,
        category_id: str,
        user_id: str | None = None,
        exclude_ids: list[str] | None = None,
        limit: int = 2,
    ) -> dict[str, Any]:
        from .repository import CATEGORIES_BY_ID

        logger.info("refresh_start", extra={
            "categoryId": category_id,
            "userId": user_id,
            "excludeIds": exclude_ids,
        })

        if category_id not in CATEGORIES_BY_ID:
            logger.warning("refresh_unknown_category", extra={"categoryId": category_id})
            raise CategoryNotFound(category_id)

        if category_id == "following":
            result = self._list_following_cards(
                user_id=user_id,
                limit=limit,
                exclude_ids=exclude_ids,
                allow_live_refresh=True,
            )
            return {
                "categoryId": category_id,
                "refreshState": {
                    "refreshCount": 1,
                    "refreshedAt": self._now_iso(),
                    "source": "following_cache_hit" if result.get("cacheHit") else "following_live",
                    "emptyReason": result.get("emptyReason"),
                    "refreshLocked": bool(result.get("refreshLocked")),
                },
                "cards": result.get("items", []),
            }

        # Resolve snapshot for shown IDs and memories
        snapshot = self.snapshot_repo.get_snapshot(user_id) if user_id else None
        shown_ids = set(snapshot.shown_card_ids) if snapshot else set()
        if exclude_ids:
            shown_ids.update(exclude_ids)

        interest_memories = snapshot.interest_memories if snapshot else []

        logger.info("refresh_context", extra={
            "categoryId": category_id,
            "snapshotShownCount": len(snapshot.shown_card_ids) if snapshot else 0,
            "excludeCount": len(exclude_ids) if exclude_ids else 0,
            "totalShownIds": len(shown_ids),
            "memoryCount": len(interest_memories),
        })

        # Get cards for category from system content pool
        from . import scheduler as content_scheduler

        cards = content_scheduler.get_cached_cards(category_id)
        unshown = [c for c in cards if c["id"] not in shown_ids]

        logger.info("refresh_pool", extra={
            "categoryId": category_id,
            "totalCards": len(cards),
            "unshownCards": len(unshown),
        })

        if unshown:
            # Score and select next batch
            from .scorer import score_card

            for card in unshown:
                memory = _find_matching_memory(card, interest_memories)
                card["_score"] = score_card(card, memory)

            next_batch = sorted(unshown, key=lambda c: c.get("_score", 0), reverse=True)[:limit]

            # Clean internal score
            for card in next_batch:
                card.pop("_score", None)

            # Mark as shown
            # Do not mark prefetch cards as shown; frontend sends exclude_ids.

            logger.info("refresh_batch_from_cache", extra={
                "categoryId": category_id,
                "batchSize": len(next_batch),
                "batchIds": [c["id"] for c in next_batch],
                "batchTitles": [c.get("title", "")[:40] for c in next_batch],
            })

            return {
                "categoryId": category_id,
                "refreshState": {
                    "refreshCount": 1,
                    "refreshedAt": self._now_iso(),
                    "source": "cache",
                },
                "cards": next_batch,
            }

        # No more unshown cards - try to fetch new content
        logger.info("refresh_pool_exhausted_fetching_new", extra={"categoryId": category_id})
        new_cards = self.repository._fetch_new_content_for_category(category_id)
        if new_cards:
            # Score and select
            from .scorer import score_card

            for card in new_cards:
                memory = _find_matching_memory(card, interest_memories)
                card["_score"] = score_card(card, memory)

            next_batch = sorted(new_cards, key=lambda c: c.get("_score", 0), reverse=True)[:limit]

            for card in next_batch:
                card.pop("_score", None)

            # Do not mark prefetch cards as shown; frontend sends exclude_ids.

            logger.info("refresh_batch_from_fresh", extra={
                "categoryId": category_id,
                "batchSize": len(next_batch),
                "batchIds": [c["id"] for c in next_batch],
            })

            return {
                "categoryId": category_id,
                "refreshState": {
                    "refreshCount": 1,
                    "refreshedAt": self._now_iso(),
                    "source": "fresh",
                },
                "cards": next_batch,
            }

        # Still no cards
        logger.warning("refresh_no_cards_available", extra={"categoryId": category_id})
        return {
            "categoryId": category_id,
            "refreshState": {
                "refreshCount": 0,
                "refreshedAt": self._now_iso(),
                "source": "cache",
            },
            "cards": [],
        }

    def summarize_card(self, card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        logger.info("summarize_card", extra={"cardId": card_id, "focus": (payload or {}).get("focus")})
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
                "controversies": controversies or [f"围绕“{card.get('title', '这个话题')}”最需要先区分事实、判断和立场。"],
                "writingAngles": writing_angles or [f"我对“{card.get('title', '这个话题')}”的核心判断"],
            },
        )
        return {
            "cardId": card_id,
            "summary": next_card["contentSummary"],
            "controversies": next_card["controversies"],
            "writingAngles": next_card["writingAngles"],
            "schemaVersion": "content.summarize.v1",
        }

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def _list_following_cards(
        self,
        user_id: str | None,
        limit: int,
        exclude_ids: list[str] | None = None,
        allow_live_refresh: bool = False,
    ) -> dict[str, Any]:
        if not user_id:
            logger.info("following_cards_no_user")
            return {
                "items": [],
                "emptyReason": "需要登录并关联知乎账号后才能获取关注流。",
                "prefetchCount": 0,
            }
        try:
            from kanshan_shared import load_config
            from .scheduler import fetch_following_cards_bundle, queue_following_enrichment

            config = load_config()
            bundle = fetch_following_cards_bundle(
                zhihu_base_url=config.service_urls.zhihu,
                profile_base_url=config.service_urls.profile,
                user_id=user_id,
                force_refresh=False,
            )
            excluded = set(exclude_ids or [])
            cards = bundle.get("cards", [])
            available = [card for card in cards if card.get("id") not in excluded]

            if allow_live_refresh and not available and not bundle.get("emptyReason"):
                bundle = fetch_following_cards_bundle(
                    zhihu_base_url=config.service_urls.zhihu,
                    profile_base_url=config.service_urls.profile,
                    user_id=user_id,
                    force_refresh=True,
                )
                cards = bundle.get("cards", [])
                available = [card for card in cards if card.get("id") not in excluded]

            items = available[:limit]
            queue_following_enrichment(
                user_id=user_id,
                cache_key=bundle.get("cacheKey"),
                cards=cards,
                llm_base_url=config.service_urls.llm,
                max_cards=3,
            )
            logger.info("following_cards_loaded", extra={
                "userId": user_id,
                "total": len(cards),
                "available": len(available),
                "returned": len(items),
                "excludeCount": len(excluded),
                "cacheHit": bool(bundle.get("cacheHit")),
                "refreshLocked": bool(bundle.get("refreshLocked")),
                "emptyReason": bundle.get("emptyReason"),
            })
            return {
                "items": items,
                "prefetchCount": max(0, len(available) - len(items)),
                "cacheHit": bool(bundle.get("cacheHit")),
                "refreshLocked": bool(bundle.get("refreshLocked")),
                "emptyReason": bundle.get("emptyReason"),
            }
        except Exception as error:
            logger.warning("following_cards_failed", extra={"userId": user_id, "error": str(error)})
            return {
                "items": [],
                "emptyReason": "关注流暂未获取到真实数据，请检查知乎 OAuth token。",
                "prefetchCount": 0,
            }
