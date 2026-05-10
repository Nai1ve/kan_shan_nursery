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
        self.assertIn("ai-coding", category_ids)
        self.assertIn("following", category_ids)
        self.assertIn("serendipity", category_ids)
        self.assertGreaterEqual(len(bootstrap["cards"]), 12)

    def test_list_cards_filters_by_category_and_each_interest_has_at_least_two(self) -> None:
        service = ContentService()
        for category_id in ["agent", "ai-coding", "rag", "backend", "growth"]:
            cards = service.list_cards(category_id)["items"]
            self.assertGreaterEqual(len(cards), 2, msg=f"category {category_id} only has {len(cards)} cards")
            for card in cards:
                self.assertEqual(card["categoryId"], category_id)
                self.assertGreaterEqual(len(card["originalSources"]), 1)

    def test_get_card_returns_full_payload_with_sources(self) -> None:
        service = ContentService()

        card = service.get_card("ai-coding-moat")

        self.assertEqual(card["categoryId"], "ai-coding")
        self.assertGreater(len(card["originalSources"]), 0)
        self.assertIn("relevanceScore", card)
        self.assertIn("contentSummary", card)

    def test_get_card_raises_when_missing(self) -> None:
        service = ContentService()

        with self.assertRaises(CardNotFound):
            service.get_card("missing-card")

    def test_get_source_returns_full_content(self) -> None:
        service = ContentService()
        card = service.get_card("ai-coding-moat")
        source_id = card["originalSources"][0]["sourceId"]

        source = service.get_source(card["id"], source_id)

        self.assertEqual(source["sourceId"], source_id)
        self.assertIn("fullContent", source)
        self.assertGreater(len(source["fullContent"]), 0)

    def test_get_source_raises_when_missing(self) -> None:
        service = ContentService()
        with self.assertRaises(SourceNotFound):
            service.get_source("ai-coding-moat", "missing-source")

    def test_refresh_category_rotates_cards_and_increments_count(self) -> None:
        service = ContentService()
        before = service.list_cards("ai-coding")["items"]

        first = service.refresh_category("ai-coding")
        second = service.refresh_category("ai-coding")
        after = service.list_cards("ai-coding")["items"]

        self.assertEqual(first["refreshState"]["refreshCount"], 1)
        self.assertEqual(second["refreshState"]["refreshCount"], 2)
        self.assertEqual(len(before), len(after))
        before_ids = {card["id"] for card in before}
        after_ids = {card["id"] for card in after}
        self.assertNotEqual(before_ids, after_ids)

    def test_refresh_unknown_category_raises(self) -> None:
        service = ContentService()
        with self.assertRaises(CategoryNotFound):
            service.refresh_category("unknown-category")

    def test_summarize_card_writes_back_summary_and_returns_writing_angles(self) -> None:
        service = ContentService()

        result = service.summarize_card("agent-quality", {"focus": "失败模式"})

        self.assertEqual(result["cardId"], "agent-quality")
        self.assertIn("失败模式", result["summary"])
        self.assertGreater(len(result["controversies"]), 0)
        self.assertGreater(len(result["writingAngles"]), 0)
        next_card = service.get_card("agent-quality")
        self.assertIn("失败模式", next_card["contentSummary"])


if __name__ == "__main__":
    unittest.main()
