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

        # Step 1: confirm claim
        confirmed = service.confirm_claim(sid, {"coreClaim": "新的观点", "tone": "sharp"})
        self.assertTrue(confirmed["confirmed"])
        self.assertEqual(confirmed["draftStatus"], "claim_confirming")

        # Step 2: generate blueprint
        blueprint_result = service.generate_blueprint(sid)
        self.assertEqual(blueprint_result["session"]["draftStatus"], "blueprint_ready")
        bp = blueprint_result["blueprint"]
        self.assertIn("centralClaim", bp)
        self.assertIn("argumentSteps", bp)
        self.assertIn("counterArguments", bp)
        self.assertIn("mainThread", bp)
        self.assertGreater(len(bp["argumentSteps"]), 0)
        for step in bp["argumentSteps"]:
            self.assertIn("id", step)
            self.assertIn("title", step)
            self.assertIn("purpose", step)
            self.assertIn("keyPoints", step)

        # Step 3: confirm blueprint
        bp_confirmed = service.confirm_blueprint(sid)
        self.assertEqual(bp_confirmed["draftStatus"], "blueprint_confirmed")

        # Step 4: generate outline
        outline_result = service.generate_outline(sid)
        self.assertEqual(outline_result["session"]["draftStatus"], "outline_ready")
        outline = outline_result["outline"]
        self.assertIn("sections", outline)
        self.assertGreater(len(outline["sections"]), 0)
        for sec in outline["sections"]:
            self.assertIn("id", sec)
            self.assertIn("title", sec)
            self.assertIn("purpose", sec)
            self.assertIn("keyPoints", sec)
            self.assertIn("referencedMaterialIds", sec)
            self.assertIn("referencedSourceIds", sec)
            self.assertIn("missingMaterialHints", sec)

        # Step 5: confirm outline
        ol_confirmed = service.confirm_outline(sid)
        self.assertEqual(ol_confirmed["draftStatus"], "outline_confirmed")

        # Step 6: generate draft
        draft_result = service.generate_draft(sid)
        self.assertEqual(draft_result["session"]["draftStatus"], "draft_ready")
        self.assertTrue(draft_result["session"]["savedDraft"])
        draft = draft_result["draft"]
        self.assertIn("title", draft)
        self.assertIn("body", draft)

        # Step 7: start roundtable
        rt_result = service.start_roundtable(sid)
        self.assertEqual(rt_result["session"]["draftStatus"], "reviewing")
        rt = rt_result["roundtable"]
        self.assertEqual(rt["status"], "active")
        self.assertGreater(len(rt["turns"]), 0)
        self.assertGreater(len(rt["suggestions"]), 0)
        for turn in rt["turns"]:
            self.assertIn("id", turn)
            self.assertIn("role", turn)
            self.assertIn("content", turn)
        for sug in rt["suggestions"]:
            self.assertIn("id", sug)
            self.assertIn("fromRole", sug)
            self.assertIn("content", sug)
            self.assertIn("severity", sug)
            self.assertFalse(sug["adopted"])

        # Step 8: finalize
        finalized = service.finalize(sid)
        self.assertEqual(finalized["session"]["draftStatus"], "finalized")

        # Step 9: publish mock
        published = service.publish_mock(sid, {"title": "定稿测试"})
        self.assertEqual(published["session"]["draftStatus"], "published")
        self.assertTrue(published["publishedArticle"]["articleId"].startswith("article-"))
        self.assertEqual(published["publishedArticle"]["publishMode"], "mock")
        self.assertEqual(published["feedbackHandoff"]["linkedSeedId"], "seed-ai-coding-moat")

    def test_blueprint_requires_confirmation(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())

        with self.assertRaises(InvalidTransition):
            service.generate_blueprint(session["sessionId"])

    def test_draft_requires_outline_confirmed(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)

        # From blueprint_ready — should fail
        with self.assertRaises(InvalidTransition):
            service.generate_draft(sid)

    def test_cannot_skip_blueprint(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]

        # From claim_confirming — should fail
        with self.assertRaises(InvalidTransition):
            service.generate_draft(sid)

    def test_cannot_skip_outline(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)
        service.confirm_blueprint(sid)

        # From blueprint_confirmed — should fail (need outline first)
        with self.assertRaises(InvalidTransition):
            service.generate_draft(sid)

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

    def test_blueprint_edit_and_regenerate(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)

        # Patch blueprint
        patched = service.patch_blueprint(sid, {"mainThread": "自定义主线"})
        self.assertEqual(patched["blueprint"]["mainThread"], "自定义主线")
        self.assertEqual(patched["session"]["draftStatus"], "blueprint_ready")

        # Regenerate blueprint
        regen = service.regenerate_blueprint(sid, {"instruction": "请从反方更强的角度重写"})
        self.assertEqual(regen["session"]["draftStatus"], "blueprint_ready")
        self.assertIn("argumentSteps", regen["blueprint"])
        self.assertEqual(regen["session"]["regenerateInstruction"], "请从反方更强的角度重写")

    def test_outline_edit_and_regenerate_section(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)
        service.confirm_blueprint(sid)
        service.generate_outline(sid)

        # Patch outline
        patched = service.patch_outline(sid, {"sections": [{"id": "custom", "title": "自定义"}]})
        self.assertEqual(len(patched["outline"]["sections"]), 1)
        self.assertEqual(patched["session"]["draftStatus"], "outline_ready")

        # Regenerate section
        regen = service.regenerate_outline_section(sid, "custom")
        self.assertEqual(regen["session"]["draftStatus"], "outline_ready")

    def test_roundtable_persists_state_and_author_message(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)
        service.confirm_blueprint(sid)
        service.generate_outline(sid)
        service.confirm_outline(sid)
        service.generate_draft(sid)

        # Start roundtable
        rt_result = service.start_roundtable(sid)
        rt = rt_result["roundtable"]
        initial_turn_count = len(rt["turns"])
        initial_sug_count = len(rt["suggestions"])
        self.assertGreater(initial_turn_count, 0)
        self.assertGreater(initial_sug_count, 0)

        # Author message
        msg_result = service.roundtable_author_message(sid, "我觉得这个建议很好，会采纳。")
        rt_after_msg = msg_result["roundtable"]
        self.assertEqual(len(rt_after_msg["turns"]), initial_turn_count + 1)
        self.assertEqual(rt_after_msg["turns"][-1]["role"], "author")
        self.assertEqual(rt_after_msg["turns"][-1]["content"], "我觉得这个建议很好，会采纳。")

        # Adopt suggestion
        first_sug_id = rt["suggestions"][0]["id"]
        adopt_result = service.adopt_suggestion(sid, first_sug_id)
        adopted_sugs = [s for s in adopt_result["roundtable"]["suggestions"] if s["adopted"]]
        self.assertEqual(len(adopted_sugs), 1)
        self.assertEqual(adopted_sugs[0]["id"], first_sug_id)

        # Continue roundtable
        continue_result = service.continue_roundtable(sid)
        rt_after_continue = continue_result["roundtable"]
        self.assertGreater(len(rt_after_continue["turns"]), len(rt_after_msg["turns"]))

    def test_roundtable_from_draft_ready(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)
        service.confirm_blueprint(sid)
        service.generate_outline(sid)
        service.confirm_outline(sid)
        service.generate_draft(sid)

        # Should be able to finalize directly from draft_ready (without roundtable)
        finalized = service.finalize(sid)
        self.assertEqual(finalized["session"]["draftStatus"], "finalized")

    def test_publish_requires_finalized(self) -> None:
        service = WritingService()
        session = service.create_session(base_payload())
        sid = session["sessionId"]
        service.confirm_claim(sid)
        service.generate_blueprint(sid)
        service.confirm_blueprint(sid)
        service.generate_outline(sid)
        service.confirm_outline(sid)
        service.generate_draft(sid)

        with self.assertRaises(InvalidTransition):
            service.publish_mock(sid)


if __name__ == "__main__":
    unittest.main()
