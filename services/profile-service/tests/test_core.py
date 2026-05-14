import pathlib
import sys
import unittest
import asyncio

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED_ROOT = ROOT.parents[1] / "packages" / "shared-python"
sys.path.insert(0, str(SHARED_ROOT))
sys.path.insert(0, str(ROOT))

from app.auth.models import ZhihuBinding
from app.enrichment.models import ProfileSignalBundle, ProfileSignalSourceItem
from app.enrichment.runner import EnrichmentRunner
from app.enrichment.transformer import build_social_memory_requests, transform_bundle_to_llm_input
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

        self.assertIn("数码科技", profile["interests"])
        self.assertIn("shuma", interest_ids)
        self.assertIn("zhichang", interest_ids)
        self.assertIn("chuangzuo", interest_ids)

    def test_update_interest_memory_is_scoped(self) -> None:
        _, memory_service = self.make_services()

        updated = memory_service.update_interest_memory(
            "shuma",
            {"writingReminder": "必须补充真实使用场景。", "feedbackSummary": "读者关注实际体验。"},
        )
        zhichang = memory_service.get_interest_memory("zhichang")

        self.assertEqual(updated["writingReminder"], "必须补充真实使用场景。")
        self.assertNotEqual(zhichang["writingReminder"], updated["writingReminder"])

    def test_memory_injection_summary_is_visible_and_editable(self) -> None:
        _, memory_service = self.make_services()

        summary = memory_service.build_injection_summary("shuma")

        self.assertTrue(summary["editable"])
        self.assertIn("数码科技", summary["displaySummary"])
        self.assertIn("globalMemory", summary)
        self.assertIn("interestMemory", summary)

    def test_memory_update_request_does_not_apply_until_confirmed(self) -> None:
        _, memory_service = self.make_services()
        request = memory_service.create_update_request(
            {
                "interestId": "shuma",
                "targetField": "writingReminder",
                "suggestedValue": "增加权限、安全审计和组织知识库材料。",
                "reason": "历史反馈提示读者追问企业落地。",
            }
        )

        before = memory_service.get_interest_memory("shuma")
        self.assertNotEqual(before["writingReminder"], request["suggestedValue"])

        applied = memory_service.apply_update_request(request["id"])
        after = memory_service.get_interest_memory("shuma")

        self.assertEqual(applied["request"]["status"], "applied")
        self.assertEqual(after["writingReminder"], request["suggestedValue"])

    def test_reject_memory_request_keeps_memory_unchanged(self) -> None:
        _, memory_service = self.make_services()
        request = memory_service.create_update_request(
            {
                "interestId": "shuma",
                "targetField": "feedbackSummary",
                "suggestedValue": "不要写入。",
                "reason": "测试拒绝。",
            }
        )
        before = memory_service.get_interest_memory("shuma")
        rejected = memory_service.reject_update_request(request["id"])
        after = memory_service.get_interest_memory("shuma")

        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(before, after)

    def test_missing_interest_raises_not_found(self) -> None:
        _, memory_service = self.make_services()

        with self.assertRaises(MemoryNotFound):
            memory_service.get_interest_memory("missing")

    def test_llm_config_is_user_scoped_and_public_response_masks_key(self) -> None:
        profile_service, _ = self.make_services()

        saved = profile_service.update_llm_config(
            {
                "activeProvider": "user_provider",
                "displayName": "DeepSeek",
                "baseUrl": "https://api.example.com/v1",
                "apiKey": "sk-test-secret",
                "model": "deepseek-chat",
            },
            user_id="user-1",
        )
        other = profile_service.get_llm_config("user-2")
        secret = profile_service.get_llm_config("user-1", include_secret=True)

        self.assertEqual(saved["activeProvider"], "user_provider")
        self.assertNotIn("apiKey", saved)
        self.assertEqual(saved["maskedKey"], "sk-t...cret")
        self.assertEqual(secret["apiKey"], "sk-test-secret")
        self.assertEqual(other["activeProvider"], "platform_free")

    def test_enrichment_transformer_accepts_string_interest_catalog(self) -> None:
        bundle = ProfileSignalBundle(
            user_id="user-1",
            generated_at="2026-05-13T00:00:00+00:00",
            onboarding={"selectedInterestIds": ["AI Coding"]},
            signals=[],
        )

        result = transform_bundle_to_llm_input(
            bundle=bundle,
            existing_memory={},
            interest_catalog=["AI Coding", "RAG"],
            profile={"nickname": "测试用户", "interests": ["AI Coding"]},
        )

        self.assertEqual(result["user"]["interests"], ["AI Coding"])

    def test_enrichment_transformer_extracts_social_memory_from_follow_lists(self) -> None:
        bundle = ProfileSignalBundle(
            user_id="user-1",
            generated_at="2026-05-13T00:00:00+00:00",
            onboarding={"selectedInterestIds": ["数码科技"]},
            signals=[
                ProfileSignalSourceItem(
                    evidence_id="ev-1",
                    source_type="followed",
                    source_id="author-1",
                    author_name="AI Coding 作者",
                    headline="长期关注 AI 编程、软件工程和开发者工具",
                    confidence_hint=0.5,
                ),
                ProfileSignalSourceItem(
                    evidence_id="ev-2",
                    source_type="followers",
                    source_id="reader-1",
                    author_name="技术读者",
                    headline="关注 AI 工具和消费电子",
                    confidence_hint=0.3,
                ),
            ],
        )

        llm_input = transform_bundle_to_llm_input(
            bundle=bundle,
            existing_memory={},
            interest_catalog=["数码科技"],
            profile={"nickname": "测试用户", "interests": ["数码科技"]},
        )
        requests = build_social_memory_requests(
            bundle=bundle,
            user_id="user-1",
            existing_memory={},
            interest_catalog=["数码科技"],
        )

        summary = llm_input["interactions"]["socialSignalSummary"]
        self.assertEqual(summary["sourceCounts"]["followed"], 1)
        self.assertEqual(summary["sourceCounts"]["followers"], 1)
        self.assertTrue(any(item["interestId"] == "shuma" for item in summary["categories"]))
        self.assertTrue(any(req["interestId"] == "global" for req in requests))
        self.assertTrue(
            any(req["interestId"] == "shuma" and req["targetField"] == "writingReminder" for req in requests)
        )

    def test_enrichment_runner_reads_access_token_from_binding_model(self) -> None:
        class AuthRepo:
            def get_zhihu_binding(self, user_id: str):
                return ZhihuBinding(
                    user_id=user_id,
                    zhihu_uid="zhihu-1",
                    access_token="token-1",
                    binding_status="bound",
                    bound_at=None,
                    expired_at=None,
                )

        runner = EnrichmentRunner(
            repo=None,
            enrichment_service=None,
            profile_repo=None,
            auth_repo=AuthRepo(),
        )

        token = asyncio.run(runner._get_access_token("user-1"))

        self.assertEqual(token, "token-1")


if __name__ == "__main__":
    unittest.main()
