import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.repository import SeedRepository
from app.service import SeedService


def make_service() -> SeedService:
    return SeedService(SeedRepository(preload=False))


def sample_card(card_id: str = "card-ai-coding-001") -> dict:
    return {
        "id": card_id,
        "categoryId": "ai-coding",
        "title": "AI Coding 到底改变了什么",
        "contentSummary": "AI Coding 正在把机械实现和工程判断区分开。",
        "tags": [{"label": "AI Coding", "tone": "blue"}],
        "controversies": ["AI 是否会压缩初级程序员成长空间？"],
        "writingAngles": ["AI 时代程序员能力结构会被重新定价"],
        "originalSources": [
            {
                "sourceId": "zhihu-001",
                "sourceType": "zhihu_search",
                "sourceUrl": "https://www.zhihu.com/question/mock",
                "author": "知乎用户",
                "publishedAt": "2026-05-10T00:00:00+08:00",
                "rawExcerpt": "高质量讨论强调工程判断比代码补全更重要。",
            }
        ],
    }


class SeedServiceTests(unittest.TestCase):
    def test_from_card_creates_once_and_updates_existing_seed(self) -> None:
        service = make_service()
        first = service.from_card(
            {"cardId": "card-ai-coding-001", "reaction": "agree", "card": sample_card(), "userNote": "先认同"}
        )
        second = service.from_card({"cardId": "card-ai-coding-001", "reaction": "disagree", "userNote": "补充反方"})

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["userReaction"], "disagree")
        self.assertEqual(second["userNote"], "补充反方")
        self.assertEqual(len(service.list_seeds()), 1)

    def test_question_thread_writes_question_and_materials(self) -> None:
        service = make_service()
        seed = service.from_card({"cardId": "card-ai-coding-001", "reaction": "question", "card": sample_card()})

        updated = service.add_question(seed["id"], {"question": "这个判断有没有可靠证据？"})

        self.assertEqual(len(updated["questions"]), 1)
        self.assertEqual(updated["questions"][0]["status"], "answered")
        material_types = [item["type"] for item in updated["wateringMaterials"]]
        self.assertIn("open_question", material_types)
        self.assertIn("evidence", material_types)
        self.assertGreater(updated["maturityScore"], seed["maturityScore"])

    def test_mark_question_changes_status_and_open_question_adoption(self) -> None:
        service = make_service()
        seed = service.from_card({"cardId": "card-ai-coding-001", "reaction": "question", "card": sample_card()})
        with_question = service.add_question(seed["id"], {"question": "反方会怎么质疑这个结论？"})
        question_id = with_question["questions"][0]["id"]

        resolved = service.mark_question(seed["id"], question_id, {"status": "resolved"})
        open_questions = [item for item in resolved["wateringMaterials"] if item["type"] == "open_question"]

        self.assertEqual(resolved["questions"][0]["status"], "resolved")
        self.assertTrue(open_questions[0]["adopted"])

    def test_material_crud_and_maturity_recalculation(self) -> None:
        service = make_service()
        seed = service.from_card({"cardId": "card-ai-coding-001", "reaction": "agree", "card": sample_card()})

        with_material = service.add_material(
            seed["id"],
            {
                "type": "personal_experience",
                "title": "项目经历",
                "content": "我在后端项目中发现需求澄清比代码实现更难。",
                "adopted": True,
            },
        )
        material_id = with_material["wateringMaterials"][0]["id"]
        edited = service.update_material(seed["id"], material_id, {"adopted": False, "content": "暂不采纳"})
        deleted = service.delete_material(seed["id"], material_id)

        self.assertFalse(edited["wateringMaterials"][0]["adopted"])
        self.assertEqual(len(deleted["wateringMaterials"]), len(seed["wateringMaterials"]))
        self.assertLessEqual(deleted["maturityScore"], with_material["maturityScore"])

    def test_agent_supplement_and_merge(self) -> None:
        service = make_service()
        target = service.from_card({"cardId": "card-ai-coding-001", "reaction": "agree", "card": sample_card()})
        source = service.create_manual_seed(
            {
                "title": "手动种子",
                "interestId": "ai-coding",
                "coreClaim": "AI 工具会改变训练方式",
                "wateringMaterials": [
                    {
                        "id": "manual-material-001",
                        "type": "counterargument",
                        "title": "反方",
                        "content": "部分场景仍然需要传统训练。",
                        "sourceLabel": "manual",
                        "adopted": True,
                        "createdAt": target["createdAt"],
                    }
                ],
            }
        )
        supplemented = service.agent_supplement(target["id"], {"type": "counterargument"})
        merged = service.merge(supplemented["id"], {"sourceSeedId": source["id"]})

        self.assertIn("counterargument", [item["type"] for item in supplemented["wateringMaterials"]])
        self.assertRaises(Exception, service.get_seed, source["id"])
        self.assertGreaterEqual(len(merged["wateringMaterials"]), 4)


class SeedFixtureTests(unittest.TestCase):
    def test_default_repo_preloads_two_demo_seeds(self) -> None:
        service = SeedService()
        ids = {seed["id"] for seed in service.list_seeds()}
        self.assertIn("seed-ai-coding-moat", ids)
        self.assertIn("seed-agent-quality", ids)

    def test_preload_disabled_starts_empty(self) -> None:
        service = SeedService(SeedRepository(preload=False))
        self.assertEqual(service.list_seeds(), [])


if __name__ == "__main__":
    unittest.main()
