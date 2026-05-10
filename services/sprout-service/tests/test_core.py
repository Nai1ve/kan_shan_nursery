import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.service import OpportunityNotFound, RunNotFound, SproutService


class SproutServiceTests(unittest.TestCase):
    def test_start_run_returns_completed_with_opportunities(self) -> None:
        service = SproutService()

        run = service.start_run({"interestId": "ai-coding"})

        self.assertEqual(run["status"], "completed")
        self.assertGreater(len(run["opportunities"]), 0)
        for opportunity in run["opportunities"]:
            self.assertEqual(opportunity["interestId"], "ai-coding")

    def test_same_interest_run_hits_cache(self) -> None:
        service = SproutService()

        first = service.start_run({"interestId": "ai-coding"})
        second = service.start_run({"interestId": "ai-coding"})

        self.assertFalse(first["cacheHit"])
        self.assertTrue(second["cacheHit"])
        self.assertEqual(first["id"], second["id"])

    def test_get_run_after_start_returns_same_payload(self) -> None:
        service = SproutService()
        run = service.start_run()

        same = service.get_run(run["id"])

        self.assertEqual(same["id"], run["id"])
        self.assertEqual(len(same["opportunities"]), len(run["opportunities"]))

    def test_get_run_missing_raises(self) -> None:
        service = SproutService()
        with self.assertRaises(RunNotFound):
            service.get_run("missing-run")

    def test_supplement_changes_status_and_returns_seed_material(self) -> None:
        service = SproutService()

        result = service.supplement("sprout-moat", {"material": "补充一次企业协作落地复盘。"})

        self.assertEqual(result["opportunity"]["status"], "supplemented")
        self.assertEqual(result["seedMaterial"]["type"], "evidence")
        self.assertIn("企业协作落地复盘", result["opportunity"]["suggestedMaterials"])

    def test_switch_angle_only_modifies_opportunity(self) -> None:
        service = SproutService()
        before = service.list_opportunities()["items"]
        before_seed = next(item for item in before if item["id"] == "sprout-moat")["activatedSeed"]

        result = service.switch_angle("sprout-moat", {"angle": "从反方视角重写", "title": "反方视角下的护城河"})

        self.assertEqual(result["status"], "angle_changed")
        self.assertEqual(result["suggestedAngle"], "从反方视角重写")
        self.assertEqual(result["activatedSeed"], before_seed)

    def test_dismiss_marks_dismissed(self) -> None:
        service = SproutService()

        result = service.dismiss("sprout-moat")

        self.assertEqual(result["status"], "dismissed")

    def test_start_writing_returns_handoff_payload(self) -> None:
        service = SproutService()

        result = service.start_writing("sprout-quality")

        self.assertEqual(result["opportunity"]["status"], "writing")
        handoff = result["writingHandoff"]
        self.assertEqual(handoff["seedId"], "seed-agent-quality")
        self.assertEqual(handoff["interestId"], "agent")

    def test_unknown_opportunity_raises(self) -> None:
        service = SproutService()
        with self.assertRaises(OpportunityNotFound):
            service.dismiss("unknown")


if __name__ == "__main__":
    unittest.main()
