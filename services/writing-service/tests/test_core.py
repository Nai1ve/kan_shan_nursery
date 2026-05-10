import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.session_logic import InvalidTransition, SessionNotFound
from app.service import WritingService


def base_payload() -> dict:
    return {
        "seedId": "seed-ai-coding-moat",
        "interestId": "ai-coding",
        "coreClaim": "AI 编程工具的护城河可能不在会写代码",
        "articleType": "工程复盘",
        "tone": "balanced",
    }


class WritingServiceTests(unittest.TestCase):
    def test_create_session_injects_default_memory_when_missing(self) -> None:
        service = WritingService()

        session = service.create_session(base_payload())

        self.assertEqual(session["draftStatus"], "claim_confirming")
        self.assertFalse(session["confirmed"])
        self.assertEqual(session["memoryOverride"]["interestId"], "ai-coding")
        self.assertIn("writingReminder", session["memoryOverride"])

    def test_create_session_validates_required_fields(self) -> None:
        service = WritingService()
        with self.assertRaises(ValueError):
            service.create_session({"interestId": "ai-coding"})

    def test_patch_memory_override_only_updates_session(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())

        patched = service.patch_session(
            session["sessionId"],
            {"memoryOverride": {**session["memoryOverride"], "writingReminder": "session-only override"}},
        )

        self.assertEqual(patched["memoryOverride"]["writingReminder"], "session-only override")

    def test_full_lifecycle_runs_through_publish(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]

        confirmed = service.confirm_claim(sid, {"coreClaim": "新的观点", "tone": "sharp"})
        blueprint = service.generate_blueprint(sid)
        draft = service.generate_draft(sid)
        review = service.roundtable(sid)
        finalized = service.finalize(sid)
        published = service.publish_mock(sid, {"title": "定稿测试"})

        self.assertTrue(confirmed["confirmed"])
        self.assertEqual(blueprint["session"]["draftStatus"], "blueprint_ready")
        self.assertEqual(draft["session"]["draftStatus"], "draft_ready")
        self.assertTrue(draft["session"]["savedDraft"])
        self.assertEqual(review["session"]["draftStatus"], "reviewing")
        self.assertEqual(len(review["review"]["reviewers"]), 3)
        self.assertEqual(finalized["session"]["draftStatus"], "finalized")
        self.assertEqual(published["session"]["draftStatus"], "published")
        self.assertTrue(published["publishedArticle"]["articleId"].startswith("article-"))
        self.assertEqual(published["publishedArticle"]["publishMode"], "mock")
        self.assertEqual(published["feedbackHandoff"]["linkedSeedId"], "seed-ai-coding-moat")

    def test_blueprint_requires_confirmation(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())

        with self.assertRaises(InvalidTransition):
            service.generate_blueprint(session["sessionId"])

    def test_finalize_requires_draft_or_review(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        service.confirm_claim(session["sessionId"])

        with self.assertRaises(InvalidTransition):
            service.finalize(session["sessionId"])

    def test_get_unknown_session_raises(self) -> None:
        service = WritingService()
        with self.assertRaises(SessionNotFound):
            service.get_session("missing")


if __name__ == "__main__":
    unittest.main()
