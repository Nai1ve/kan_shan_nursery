import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED_ROOT = ROOT.parents[1] / "packages" / "shared-python"
sys.path.insert(0, str(SHARED_ROOT))
sys.path.insert(0, str(ROOT))

from app.repository import CardNotFound, CategoryNotFound, SourceNotFound
from app.service import ContentService


def _following_card(card_id: str, title: str) -> dict:
    return {
        "id": card_id,
        "categoryId": "following",
        "title": title,
        "contentSummary": f"{title} 摘要",
        "recommendationReason": "来自关注流",
        "controversies": [],
        "writingAngles": [],
        "originalSources": [
            {
                "sourceId": f"source-{card_id}",
                "sourceType": "following",
                "sourceUrl": "https://www.zhihu.com/question/1",
                "title": title,
                "rawExcerpt": f"{title} 摘要",
                "fullContent": f"{title} 完整内容",
                "meta": ["作者回答了问题"],
            }
        ],
        "relevanceScore": 80,
        "createdAt": "2026-05-13T00:00:00+00:00",
    }


class ContentServiceTests(unittest.TestCase):
    def test_bootstrap_returns_categories_and_cards(self) -> None:
        service = ContentService()

        bootstrap = service.bootstrap()

        category_ids = {item["id"] for item in bootstrap["categories"]}
        self.assertIn("shuma", category_ids)
        self.assertIn("lishi", category_ids)
        self.assertIn("following", category_ids)
        self.assertIn("serendipity", category_ids)
        self.assertIsInstance(bootstrap["cards"], list)

    def test_bootstrap_filters_by_user_interest_ids(self) -> None:
        service = ContentService()

        bootstrap = service.bootstrap(interest_ids=["shuma"])

        category_ids = {item["id"] for item in bootstrap["categories"]}
        self.assertEqual(category_ids, {"shuma", "following", "serendipity"})
        for card in bootstrap["cards"]:
            self.assertIn(card["categoryId"], category_ids)

    def test_list_cards_filters_by_category(self) -> None:
        service = ContentService()
        bootstrap = service.bootstrap()
        cards = bootstrap["cards"]
        if not cards:
            self.skipTest("no cached cards available (scheduler not running)")
        # Pick a card and verify it can be listed by its category
        sample = cards[0]
        cat_id = sample["categoryId"]
        if cat_id in ("following", "serendipity"):
            cat_id = next((c["categoryId"] for c in cards if c["categoryId"] not in ("following", "serendipity")), None)
        if not cat_id:
            self.skipTest("no interest-category cards available")
        listed = service.list_cards(cat_id)["items"]
        for card in listed:
            self.assertEqual(card["categoryId"], cat_id)

    def test_get_card_returns_full_payload_with_sources(self) -> None:
        service = ContentService()
        bootstrap = service.bootstrap()
        cards = bootstrap["cards"]
        if not cards:
            self.skipTest("no cached cards available (scheduler not running)")

        card = service.get_card(cards[0]["id"])

        self.assertIn("categoryId", card)
        self.assertIn("relevanceScore", card)
        self.assertIn("contentSummary", card)

    def test_get_card_raises_when_missing(self) -> None:
        service = ContentService()

        with self.assertRaises(CardNotFound):
            service.get_card("missing-card")

    def test_get_source_returns_full_content(self) -> None:
        service = ContentService()
        bootstrap = service.bootstrap()
        cards = bootstrap["cards"]
        if not cards:
            self.skipTest("no cached cards available (scheduler not running)")
        card = service.get_card(cards[0]["id"])
        sources = card.get("originalSources", [])
        if not sources:
            self.skipTest("card has no sources")
        source_id = sources[0]["sourceId"]

        source = service.get_source(card["id"], source_id)

        self.assertEqual(source["sourceId"], source_id)
        self.assertIn("fullContent", source)

    def test_get_source_raises_when_missing(self) -> None:
        service = ContentService()
        bootstrap = service.bootstrap()
        cards = bootstrap["cards"]
        if not cards:
            self.skipTest("no cached cards available (scheduler not running)")
        with self.assertRaises(SourceNotFound):
            service.get_source(cards[0]["id"], "missing-source")

    def test_refresh_category_returns_structure(self) -> None:
        service = ContentService()
        result = service.refresh_category("shuma")

        self.assertEqual(result["categoryId"], "shuma")
        self.assertIn("refreshState", result)
        self.assertIn("cards", result)
        self.assertIsInstance(result["cards"], list)

    def test_refresh_unknown_category_raises(self) -> None:
        service = ContentService()
        with self.assertRaises(CategoryNotFound):
            service.refresh_category("unknown-category")

    def test_summarize_card_writes_back_summary_and_returns_writing_angles(self) -> None:
        service = ContentService()
        bootstrap = service.bootstrap()
        cards = bootstrap["cards"]
        if not cards:
            self.skipTest("no cached cards available (scheduler not running)")
        card_id = cards[0]["id"]

        result = service.summarize_card(card_id, {"focus": "test-focus"})

        self.assertEqual(result["cardId"], card_id)
        self.assertIn("test-focus", result["summary"])
        self.assertGreater(len(result["controversies"]), 0)
        self.assertGreater(len(result["writingAngles"]), 0)

    def test_following_cards_use_cache_bundle_and_queue_enrichment(self) -> None:
        service = ContentService()
        cards = [
            _following_card("fol-a", "已看过"),
            _following_card("fol-b", "关注流新动态"),
            _following_card("fol-c", "下一条关注动态"),
        ]

        with (
            patch(
                "app.scheduler.fetch_following_cards_bundle",
                return_value={"cards": cards, "cacheHit": True, "cacheKey": "following-cache-key"},
            ) as fetch_bundle,
            patch("app.scheduler.queue_following_enrichment") as queue_enrichment,
        ):
            result = service._list_following_cards("user-1", 1, exclude_ids=["fol-a"])

        self.assertEqual(fetch_bundle.call_args.kwargs["force_refresh"], False)
        self.assertEqual(result["items"][0]["id"], "fol-b")
        self.assertEqual(result["prefetchCount"], 1)
        self.assertTrue(result["cacheHit"])
        queue_enrichment.assert_called_once()

    def test_following_refresh_fetches_live_only_when_cached_cards_exhausted(self) -> None:
        service = ContentService()
        first_bundle = {
            "cards": [_following_card("fol-a", "已全部划过")],
            "cacheHit": True,
            "cacheKey": "following-cache-key",
        }
        second_bundle = {
            "cards": [_following_card("fol-b", "新刷出的关注流")],
            "cacheHit": False,
            "cacheKey": "following-cache-key",
        }

        with (
            patch("app.scheduler.fetch_following_cards_bundle", side_effect=[first_bundle, second_bundle]) as fetch_bundle,
            patch("app.scheduler.queue_following_enrichment"),
        ):
            result = service._list_following_cards("user-1", 1, exclude_ids=["fol-a"], allow_live_refresh=True)

        self.assertEqual(result["items"][0]["id"], "fol-b")
        self.assertEqual(fetch_bundle.call_args_list[0].kwargs["force_refresh"], False)
        self.assertEqual(fetch_bundle.call_args_list[1].kwargs["force_refresh"], True)

    def test_following_bundle_short_cache_avoids_second_oauth_feed_call(self) -> None:
        from app import scheduler

        class FakeZhihuClient:
            calls = 0

            def __init__(self, base_url: str) -> None:
                self.base_url = base_url

            def following_feed(self, access_token: str | None = None) -> list[dict]:
                FakeZhihuClient.calls += 1
                return [
                    {
                        "sourceId": "moment-1",
                        "sourceType": "following",
                        "contentType": "回答了问题",
                        "title": "Agent Quality 到底评估什么",
                        "url": "https://www.zhihu.com/question/1",
                        "author": "知乎作者",
                        "publishedAt": "2026-05-13T00:00:00+00:00",
                        "summary": "关注作者给出了一段高密度观点。",
                        "fullContent": "关注作者给出了一段高密度观点，适合转化为观点种子。" * 8,
                        "actor": "关注作者",
                    }
                ]

        original_memory = dict(scheduler._memory_cache)
        scheduler._memory_cache.clear()
        scheduler._memory_cache.update({
            "cards": {},
            "categories": [],
            "last_refresh": None,
            "shown_ids": set(),
        })
        FakeZhihuClient.calls = 0
        try:
            with (
                patch("app.scheduler._get_redis", return_value=None),
                patch("app.scheduler._fetch_zhihu_token", return_value={"access_token": "token-1"}),
                patch("app.zhihu_client.ZhihuClient", FakeZhihuClient),
            ):
                first = scheduler.fetch_following_cards_bundle(user_id="user-1")
                second = scheduler.fetch_following_cards_bundle(user_id="user-1")
        finally:
            scheduler._memory_cache.clear()
            scheduler._memory_cache.update(original_memory)

        self.assertFalse(first["cacheHit"])
        self.assertTrue(second["cacheHit"])
        self.assertEqual(FakeZhihuClient.calls, 1)
        self.assertEqual(first["cards"][0]["categoryId"], "following")
        self.assertIn("观点种子", first["cards"][0]["originalSources"][0]["fullContent"])


if __name__ == "__main__":
    unittest.main()
