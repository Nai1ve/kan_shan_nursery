import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.service import ArticleNotFound, FeedbackService


class FeedbackServiceTests(unittest.TestCase):
    def test_list_articles_contains_seeded_items(self) -> None:
        service = FeedbackService()

        items = service.list_articles()["items"]

        ids = {item["id"] for item in items}
        self.assertIn("article-moat", ids)
        self.assertIn("article-quality", ids)

    def test_list_articles_filters_by_interest(self) -> None:
        service = FeedbackService()

        items = service.list_articles("agent")["items"]

        self.assertTrue(all(item["interestId"] == "agent" for item in items))

    def test_get_article_raises_when_missing(self) -> None:
        service = FeedbackService()
        with self.assertRaises(ArticleNotFound):
            service.get_article("missing")

    def test_comments_summary_returns_supporting_and_counter_arguments(self) -> None:
        service = FeedbackService()

        summary = service.comments_summary("article-moat")

        self.assertEqual(summary["articleId"], "article-moat")
        self.assertGreater(len(summary["supportingViews"]), 0)
        self.assertGreater(len(summary["counterArguments"]), 0)
        self.assertGreater(len(summary["supplementaryMaterials"]), 0)

    def test_second_seed_returns_seed_payload_and_does_not_create_seed(self) -> None:
        service = FeedbackService()

        result = service.second_seed("article-moat")

        self.assertEqual(result["articleId"], "article-moat")
        seed_payload = result["seedPayload"]
        self.assertEqual(seed_payload["interestId"], "ai-coding")
        self.assertIn("coreClaim", seed_payload)
        self.assertIn("requiredMaterials", seed_payload)

    def test_memory_update_request_returns_pending_suggestion(self) -> None:
        service = FeedbackService()

        result = service.memory_update_request("article-quality")

        self.assertEqual(result["articleId"], "article-quality")
        request_body = result["memoryUpdateRequest"]
        self.assertEqual(request_body["status"], "pending")
        self.assertEqual(request_body["interestId"], "agent")
        self.assertIn("proposedPatch", request_body)
        self.assertIn("apply", result["note"])

    def test_sync_accepts_new_article(self) -> None:
        service = FeedbackService()

        result = service.sync(
            {
                "article": {
                    "title": "新发布文章",
                    "interestId": "ai-coding",
                    "linkedSeedId": "seed-new",
                }
            }
        )

        new_id = result["syncedArticleId"]
        fetched = service.get_article(new_id)
        self.assertEqual(fetched["title"], "新发布文章")
        self.assertEqual(fetched["status"], "待解析")


if __name__ == "__main__":
    unittest.main()
