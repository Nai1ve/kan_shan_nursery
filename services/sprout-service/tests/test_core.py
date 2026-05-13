import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.filter import build_dismissed_pairs_from_opportunities, filter_candidates
from app.scorer import compute_activation_score, score_seed_maturity, score_topic_relatedness
from app.service import OpportunityNotFound, RunNotFound, SproutService


def _make_seed(**overrides) -> dict:
    """Build a minimal valid seed for testing."""
    seed = {
        "id": "seed-test-1",
        "userId": "test-user",
        "interestId": "ai-coding",
        "title": "AI 编程工具的护城河很浅",
        "coreClaim": "单纯代码生成工具的护城河很浅",
        "status": "sproutable",
        "maturityScore": 70,
        "userReaction": "agree",
        "userNote": "",
        "possibleAngles": ["从代码生成商品化切入"],
        "counterArguments": ["垂直领域仍有壁垒"],
        "requiredMaterials": [],
        "wateringMaterials": [
            {"id": "m1", "type": "evidence", "title": "GitHub Copilot 数据", "content": "...", "adopted": True, "createdAt": "2026-05-01T00:00:00Z"}
        ],
        "questions": [],
        "sourceTitle": "某 AI 编程工具发布",
        "contentSummary": "...",
        "createdAt": "2026-05-01T00:00:00Z",
        "updatedAt": "2026-05-01T00:00:00Z",
    }
    seed.update(overrides)
    return seed


def _make_card(**overrides) -> dict:
    card = {
        "id": "card-test-1",
        "categoryId": "ai-coding",
        "title": "AI 编程工具发布企业协作能力",
        "contentSummary": "...",
        "controversies": ["是否会取代开发者"],
        "writingAngles": ["从工作流角度分析"],
        "enriched": True,
    }
    card.update(overrides)
    return card


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------

class TestFilterCandidates(unittest.TestCase):
    def test_excludes_published_seeds(self):
        seeds = [_make_seed(status="published")]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 0)

    def test_excludes_writing_seeds(self):
        seeds = [_make_seed(status="writing")]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 0)

    def test_excludes_low_maturity(self):
        seeds = [_make_seed(maturityScore=30)]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 0)

    def test_excludes_no_materials(self):
        seeds = [_make_seed(wateringMaterials=[])]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 0)

    def test_excludes_empty_seed(self):
        seeds = [_make_seed(title="", coreClaim="")]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 0)

    def test_excludes_dismissed_seed(self):
        seeds = [_make_seed()]
        dismissed = {("seed-test-1", "card-1")}
        result = filter_candidates(seeds, dismissed)
        self.assertEqual(len(result), 0)

    def test_excludes_active_writing(self):
        seeds = [_make_seed()]
        result = filter_candidates(seeds, active_writing_seed_ids={"seed-test-1"})
        self.assertEqual(len(result), 0)

    def test_includes_valid_seed(self):
        seeds = [_make_seed()]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "seed-test-1")

    def test_handles_string_maturity_score(self):
        seeds = [_make_seed(maturityScore="70")]
        result = filter_candidates(seeds)
        self.assertEqual(len(result), 1)


# ---------------------------------------------------------------------------
# Scorer tests
# ---------------------------------------------------------------------------

class TestScorer(unittest.TestCase):
    def test_seed_maturity_formula(self):
        self.assertAlmostEqual(score_seed_maturity({"maturityScore": 72}), 0.72)
        self.assertAlmostEqual(score_seed_maturity({"maturityScore": 0}), 0.0)
        self.assertAlmostEqual(score_seed_maturity({"maturityScore": 100}), 1.0)
        self.assertAlmostEqual(score_seed_maturity({"maturityScore": "50"}), 0.5)

    def test_topic_relatedness_returns_score_and_trigger_cards(self):
        seed = _make_seed(title="AI 编程工具的护城河", coreClaim="护城河不在代码生成")
        cards = [_make_card(title="AI 编程工具发布企业协作能力")]
        score, trigger_cards, trigger_type = score_topic_relatedness(seed, cards, [])
        self.assertGreater(score, 0.0)
        self.assertEqual(len(trigger_cards), 1)
        self.assertEqual(trigger_type, "hot")

    def test_topic_relatedness_prefends_today_card_when_better_match(self):
        seed = _make_seed(title="AI 编程工具的护城河")
        hot = [_make_card(title="完全无关的话题", id="hot-1")]
        today = [_make_card(title="AI 编程工具的护城河到底在哪", id="today-1")]
        score, trigger_cards, trigger_type = score_topic_relatedness(seed, hot, today)
        self.assertEqual(trigger_type, "today_card")
        self.assertIn("today-1", trigger_cards)

    def test_activation_score_range(self):
        result = compute_activation_score(
            _make_seed(),
            [_make_card()],
            [_make_card(id="card-today", title="AI 编程工具的护城河讨论")],
            {},
        )
        self.assertGreaterEqual(result["total"], 0)
        self.assertLessEqual(result["total"], 100)
        self.assertIn("factors", result)
        self.assertIn("penalties", result)
        self.assertIn("bestTriggerCards", result)
        self.assertIn("triggerType", result)

    def test_activation_score_penalties_for_empty_materials(self):
        result = compute_activation_score(
            _make_seed(wateringMaterials=[]),
            [_make_card()],
            [],
            {},
        )
        self.assertIn("evidence_empty", result["penaltyReasons"])

    def test_activation_score_penalties_for_dismissed(self):
        result = compute_activation_score(
            _make_seed(),
            [_make_card()],
            [],
            {},
            dismissed_pairs={("seed-test-1", "card-1")},
        )
        self.assertIn("recently_dismissed", result["penaltyReasons"])


# ---------------------------------------------------------------------------
# Build dismissed pairs
# ---------------------------------------------------------------------------

class TestBuildDismissedPairs(unittest.TestCase):
    def test_extracts_pairs_from_dismissed_opportunities(self):
        opps = [
            {"id": "o1", "seedId": "s1", "status": "dismissed", "dismissedAt": "2026-05-13T00:00:00Z", "triggerCardIds": ["c1", "c2"]},
            {"id": "o2", "seedId": "s2", "status": "active", "triggerCardIds": ["c3"]},
        ]
        pairs = build_dismissed_pairs_from_opportunities(opps)
        self.assertEqual(len(pairs), 2)
        self.assertIn(("s1", "c1"), pairs)
        self.assertIn(("s1", "c2"), pairs)

    def test_ignores_old_dismissals(self):
        opps = [
            {"id": "o1", "seedId": "s1", "status": "dismissed", "dismissedAt": "2026-01-01T00:00:00Z", "triggerCardIds": ["c1"]},
        ]
        pairs = build_dismissed_pairs_from_opportunities(opps, days=7)
        self.assertEqual(len(pairs), 0)


# ---------------------------------------------------------------------------
# Service integration tests
# ---------------------------------------------------------------------------

class SproutServiceTests(unittest.TestCase):
    def test_start_run_with_payload_seeds(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds, "interestId": "ai-coding"})
        self.assertEqual(run["status"], "completed")
        self.assertGreater(len(run["opportunities"]), 0)
        for opp in run["opportunities"]:
            self.assertEqual(opp["interestId"], "ai-coding")

    def test_start_run_empty_seeds_returns_empty(self) -> None:
        service = SproutService()
        # No data_fetcher, no seeds in payload → mock fallback
        run = service.start_run({"userId": "test-user"})
        self.assertEqual(run["status"], "completed")
        # With no data_fetcher and no seeds, falls back to mock
        self.assertGreater(len(run["opportunities"]), 0)

    def test_same_interest_run_hits_cache(self) -> None:
        seeds = [_make_seed()]

        class Fetcher:
            def fetch_seeds(self, user_id: str):
                return seeds

            def fetch_hot_cards(self):
                return []

            def fetch_today_cards(self, user_id: str):
                return []

            def fetch_memory(self, session_id: str):
                return {}

        service = SproutService(data_fetcher=Fetcher())
        first = service.start_run({"userId": "test-user", "interestId": "ai-coding"})
        second = service.start_run({"userId": "test-user", "interestId": "ai-coding"})
        self.assertFalse(first["cacheHit"])
        self.assertTrue(second["cacheHit"])
        self.assertEqual(first["id"], second["id"])

    def test_cache_is_scoped_by_user(self) -> None:
        seeds = [_make_seed()]

        class Fetcher:
            def fetch_seeds(self, user_id: str):
                return seeds

            def fetch_hot_cards(self):
                return []

            def fetch_today_cards(self, user_id: str):
                return []

            def fetch_memory(self, session_id: str):
                return {}

        service = SproutService(data_fetcher=Fetcher())
        first = service.start_run({"userId": "user-a", "interestId": "ai-coding"})
        second = service.start_run({"userId": "user-b", "interestId": "ai-coding"})

        self.assertFalse(first["cacheHit"])
        self.assertFalse(second["cacheHit"])
        self.assertNotEqual(first["id"], second["id"])

    def test_get_run_after_start_returns_same_payload(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds})
        same = service.get_run(run["id"])
        self.assertEqual(same["id"], run["id"])
        self.assertEqual(len(same["opportunities"]), len(run["opportunities"]))

    def test_get_run_missing_raises(self) -> None:
        service = SproutService()
        with self.assertRaises(RunNotFound):
            service.get_run("missing-run")

    def test_opportunity_has_new_fields(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds})
        opp = run["opportunities"][0]
        self.assertIn("runId", opp)
        self.assertIn("userId", opp)
        self.assertIn("triggerType", opp)
        self.assertIn("triggerCardIds", opp)
        self.assertIn("createdAt", opp)
        self.assertIn("score", opp)
        self.assertIn("tags", opp)

    def test_supplement_changes_status_and_returns_seed_material(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds})
        opp_id = run["opportunities"][0]["id"]
        result = service.supplement(opp_id, {"material": "补充一次企业协作落地复盘。"})
        self.assertEqual(result["opportunity"]["status"], "supplemented")
        self.assertEqual(result["seedMaterial"]["type"], "evidence")
        self.assertIn("企业协作落地复盘", result["opportunity"]["suggestedMaterials"])

    def test_switch_angle_modifies_opportunity(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds})
        opp_id = run["opportunities"][0]["id"]
        result = service.switch_angle(opp_id, {"angle": "从反方视角重写", "title": "反方视角下的护城河"})
        self.assertEqual(result["status"], "angle_changed")
        self.assertEqual(result["suggestedAngle"], "从反方视角重写")

    def test_dismiss_marks_dismissed_and_records_pair(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        run = service.start_run({"userId": "test-user", "seeds": seeds})
        opp_id = run["opportunities"][0]["id"]
        result = service.dismiss(opp_id)
        self.assertEqual(result["status"], "dismissed")
        self.assertIn("dismissedAt", result)

    def test_dismiss_excludes_seed_from_next_run(self) -> None:
        service = SproutService()
        seeds = [_make_seed()]
        # First run
        run1 = service.start_run({"userId": "test-user", "seeds": seeds})
        opp_id = run1["opportunities"][0]["id"]
        service.dismiss(opp_id)
        # Second run — seed should be excluded by dismissed filter
        # Need to clear cache first
        service._cache_by_interest.clear()
        run2 = service.start_run({"userId": "test-user", "seeds": seeds})
        # The seed was dismissed, so no opportunities from it
        self.assertEqual(len(run2["opportunities"]), 0)

    def test_start_writing_returns_handoff_payload(self) -> None:
        service = SproutService()
        seeds = [_make_seed(interestId="agent")]
        run = service.start_run({"userId": "test-user", "seeds": seeds, "interestId": "agent"})
        opp_id = run["opportunities"][0]["id"]
        result = service.start_writing(opp_id)
        self.assertEqual(result["opportunity"]["status"], "writing")
        handoff = result["writingHandoff"]
        self.assertEqual(handoff["seedId"], "seed-test-1")
        self.assertEqual(handoff["interestId"], "agent")

    def test_unknown_opportunity_raises(self) -> None:
        service = SproutService()
        with self.assertRaises(OpportunityNotFound):
            service.dismiss("unknown")


if __name__ == "__main__":
    unittest.main()
