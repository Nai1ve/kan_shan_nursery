import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.memory.service import MemoryNotFound, MemoryService
from app.profile.repository import ProfileRepository
from app.profile.service import ProfileService


class ProfileServiceTests(unittest.TestCase):
    def make_services(self) -> tuple[ProfileService, MemoryService]:
        repository = ProfileRepository()
        return ProfileService(repository), MemoryService(repository)

    def test_default_profile_contains_complete_interest_memory_set(self) -> None:
        profile_service, memory_service = self.make_services()

        profile = profile_service.get_profile()
        interest_ids = {item["interestId"] for item in memory_service.list_interest_memories()}

        self.assertIn("AI Coding", profile["interests"])
        self.assertIn("agent", interest_ids)
        self.assertIn("ai-coding", interest_ids)
        self.assertIn("following", interest_ids)
        self.assertIn("serendipity", interest_ids)

    def test_update_interest_memory_is_scoped(self) -> None:
        _, memory_service = self.make_services()

        updated = memory_service.update_interest_memory(
            "ai-coding",
            {"writingReminder": "必须补充真实工程场景。", "feedbackSummary": "读者关注企业落地。"},
        )
        agent = memory_service.get_interest_memory("agent")

        self.assertEqual(updated["writingReminder"], "必须补充真实工程场景。")
        self.assertNotEqual(agent["writingReminder"], updated["writingReminder"])

    def test_memory_injection_summary_is_visible_and_editable(self) -> None:
        _, memory_service = self.make_services()

        summary = memory_service.build_injection_summary("ai-coding")

        self.assertTrue(summary["editable"])
        self.assertIn("AI Coding", summary["displaySummary"])
        self.assertIn("globalMemory", summary)
        self.assertIn("interestMemory", summary)

    def test_memory_update_request_does_not_apply_until_confirmed(self) -> None:
        _, memory_service = self.make_services()
        request = memory_service.create_update_request(
            {
                "interestId": "ai-coding",
                "targetField": "writingReminder",
                "suggestedValue": "增加权限、安全审计和组织知识库材料。",
                "reason": "历史反馈提示读者追问企业落地。",
            }
        )

        before = memory_service.get_interest_memory("ai-coding")
        self.assertNotEqual(before["writingReminder"], request["suggestedValue"])

        applied = memory_service.apply_update_request(request["id"])
        after = memory_service.get_interest_memory("ai-coding")

        self.assertEqual(applied["request"]["status"], "applied")
        self.assertEqual(after["writingReminder"], request["suggestedValue"])

    def test_reject_memory_request_keeps_memory_unchanged(self) -> None:
        _, memory_service = self.make_services()
        request = memory_service.create_update_request(
            {
                "interestId": "ai-coding",
                "targetField": "feedbackSummary",
                "suggestedValue": "不要写入。",
                "reason": "测试拒绝。",
            }
        )
        before = memory_service.get_interest_memory("ai-coding")
        rejected = memory_service.reject_update_request(request["id"])
        after = memory_service.get_interest_memory("ai-coding")

        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(before, after)

    def test_missing_interest_raises_not_found(self) -> None:
        _, memory_service = self.make_services()

        with self.assertRaises(MemoryNotFound):
            memory_service.get_interest_memory("missing")


if __name__ == "__main__":
    unittest.main()
