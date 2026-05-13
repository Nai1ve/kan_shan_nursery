import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.repository import CardNotFound, CategoryNotFound, SourceNotFound
from app.service import ContentService


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


if __name__ == "__main__":
    unittest.main()
