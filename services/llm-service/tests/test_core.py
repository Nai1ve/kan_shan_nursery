import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED_ROOT = ROOT.parents[1] / "packages" / "shared-python"
sys.path.insert(0, str(SHARED_ROOT))
sys.path.insert(0, str(ROOT))

from app.cache import MemoryCache
from app.providers import MockProvider, ProviderError, ProviderResult
from app.registry import Registry
from app.service import LlmService
import app.service as service_module
from app.settings import Settings
from app.validators import TASK_REQUIRED_KEYS


def make_settings(**overrides) -> Settings:
    base = {
        "provider_mode": "mock",
        "trace_enabled": False,
        "trace_dir": "output/llm-trace-test",
    }
    base.update(overrides)
    return Settings(**base)


def request(task_type: str, input_data: dict | None = None) -> dict:
    return {
        "taskType": task_type,
        "input": input_data or {"title": "AI Coding 与程序员成长"},
        "promptVersion": "v1",
        "schemaVersion": "v1",
    }


class LlmServiceCoreTests(unittest.TestCase):
    def test_all_mock_tasks_return_required_keys(self) -> None:
        service = LlmService(make_settings(), MemoryCache())
        for task_type, required_keys in TASK_REQUIRED_KEYS.items():
            with self.subTest(task_type=task_type):
                response = service.run_task(request(task_type))
                self.assertEqual(response["taskType"], task_type)
                self.assertFalse(response["cache"]["hit"])
                self.assertTrue(required_keys.issubset(response["output"].keys()))

    def test_cache_hit_reuses_same_task_output(self) -> None:
        service = LlmService(make_settings(), MemoryCache())
        first = service.run_task(request("generate-writing-angles"))
        second = service.run_task(request("generate-writing-angles"))

        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["output"], second["output"])

    def test_expected_task_must_match_path_task(self) -> None:
        service = LlmService(make_settings(), MemoryCache())
        with self.assertRaises(ValueError):
            service.run_task(request("draft"), expected_task="summarize-content")

    def test_zhihu_provider_failure_falls_back_to_mock(self) -> None:
        settings = make_settings(
            provider_mode="zhihu",
            zhihu_adapter_url="http://127.0.0.1:1",
            request_timeout_seconds=0.01,
        )
        service = LlmService(settings, MemoryCache())

        response = service.run_task(request("answer-seed-question", {"question": "有没有证据？"}))

        self.assertTrue(response["fallback"])
        self.assertEqual(response["routeMeta"]["fallbackTo"], "mock")
        self.assertIn("answer", response["output"])


class RoutingTests(unittest.TestCase):
    def test_provider_mode_mock_overrides_per_task_route(self) -> None:
        service = LlmService(make_settings(provider_mode="mock"), MemoryCache())
        response = service.run_task(request("summarize-content"))
        self.assertEqual(response["routeMeta"]["provider"], "mock")
        self.assertEqual(response["routeMeta"]["mode"], "single")
        self.assertFalse(response["fallback"])

    def test_provider_mode_zhihu_uses_per_task_provider(self) -> None:
        settings = make_settings(
            provider_mode="zhihu",
            zhihu_adapter_url="http://127.0.0.1:1",
            request_timeout_seconds=0.01,
        )
        service = LlmService(settings, MemoryCache())
        response = service.run_task(request("summarize-content"))
        self.assertEqual(response["routeMeta"]["provider"], "zhihu_direct")
        self.assertTrue(response["fallback"])

    def test_openai_compat_provider_not_registered_when_config_missing(self) -> None:
        registry = Registry.load_default(make_settings(openai_compat_base_url="", openai_compat_api_key=""))
        self.assertFalse(registry.has_provider("openai_compat"))
        self.assertTrue(registry.has_provider("mock"))
        self.assertTrue(registry.has_provider("zhihu_direct"))

    def test_provider_mode_openai_compat_uses_openai_provider_and_falls_back(self) -> None:
        settings = make_settings(
            provider_mode="openai_compat",
            openai_compat_base_url="http://127.0.0.1:1",
            openai_compat_api_key="test-key",
            openai_compat_model="test-model",
            request_timeout_seconds=0.01,
        )
        service = LlmService(settings, MemoryCache())

        response = service.run_task(request("summarize-content"))

        self.assertEqual(response["routeMeta"]["provider"], "openai_compat")
        self.assertTrue(response["fallback"])
        self.assertEqual(response["routeMeta"]["fallbackTo"], "mock")

    def test_provider_invalid_schema_falls_back_to_mock(self) -> None:
        class BadProvider:
            name = "openai_compat"

            def run(self, task_type, input_data, prompt, persona=None):
                return ProviderResult(output={"content": "not the required schema"}, provider_meta={})

        settings = make_settings(
            provider_mode="openai_compat",
            openai_compat_base_url="http://example.invalid",
            openai_compat_api_key="test-key",
        )
        registry = Registry.load_default(settings)
        registry._providers["openai_compat"] = BadProvider()  # type: ignore[index]
        service = LlmService(settings, MemoryCache(), registry=registry)

        response = service.run_task(request("summarize-content"))

        self.assertTrue(response["fallback"])
        self.assertEqual(response["routeMeta"]["provider"], "openai_compat")
        self.assertEqual(response["routeMeta"]["fallbackTo"], "mock")
        self.assertIn("summary", response["output"])

    def test_generic_extraction_ignores_user_provider_config(self) -> None:
        service = LlmService(make_settings(provider_mode="mock"), MemoryCache())
        response = service.run_task({
            **request("summarize-content"),
            "userLlmConfig": {
                "activeProvider": "user_provider",
                "baseUrl": "http://127.0.0.1:1",
                "apiKey": "user-key",
                "model": "user-model",
            },
        })

        self.assertEqual(response["routeMeta"]["provider"], "mock")
        self.assertEqual(response["routeMeta"]["providerSource"], "platform_free")
        self.assertNotIn("notices", response)

    def test_personal_task_uses_user_provider_first(self) -> None:
        class GoodUserProvider:
            name = "openai_compat"

            def __init__(self, *args, **kwargs):
                pass

            def run(self, task_type, input_data, prompt, persona=None):
                return ProviderResult(
                    output={
                        "answer": "用户模型回答",
                        "statusRecommendation": "resolved",
                        "materials": [],
                        "followUpQuestions": [],
                    },
                    provider_meta={},
                )

        original = service_module.OpenAICompatProvider
        service_module.OpenAICompatProvider = GoodUserProvider  # type: ignore[assignment]
        try:
            service = LlmService(
                make_settings(provider_mode="mock"),
                MemoryCache(),
                quota_limits={"answer-seed-question": 1},
            )
            response = service.run_task({
                **request("answer-seed-question", {"question": "证据是什么？"}),
                "userLlmConfig": {
                    "activeProvider": "user_provider",
                    "baseUrl": "http://user-llm.local/v1",
                    "apiKey": "user-key",
                    "model": "user-model",
                },
            })
        finally:
            service_module.OpenAICompatProvider = original  # type: ignore[assignment]

        self.assertFalse(response["fallback"])
        self.assertEqual(response["routeMeta"]["provider"], "user_provider")
        self.assertEqual(response["routeMeta"]["providerSource"], "user_provider")
        self.assertEqual(response["output"]["answer"], "用户模型回答")
        self.assertNotIn("notices", response)
        self.assertEqual(service.get_quota()["answer-seed-question"]["used"], 0)

    def test_user_provider_failure_falls_back_with_notice(self) -> None:
        class BadUserProvider:
            name = "openai_compat"

            def __init__(self, *args, **kwargs):
                pass

            def run(self, task_type, input_data, prompt, persona=None):
                raise ProviderError("user endpoint unreachable")

        original = service_module.OpenAICompatProvider
        service_module.OpenAICompatProvider = BadUserProvider  # type: ignore[assignment]
        try:
            service = LlmService(make_settings(provider_mode="mock"), MemoryCache())
            response = service.run_task({
                **request("answer-seed-question", {"question": "证据是什么？"}),
                "userLlmConfig": {
                    "activeProvider": "user_provider",
                    "baseUrl": "http://user-llm.local/v1",
                    "apiKey": "user-key",
                    "model": "user-model",
                },
            })
        finally:
            service_module.OpenAICompatProvider = original  # type: ignore[assignment]

        self.assertTrue(response["fallback"])
        self.assertTrue(response["routeMeta"]["userProviderFailed"])
        self.assertEqual(response["routeMeta"]["providerSource"], "platform_free")
        self.assertEqual(response["notices"][0]["code"], "USER_LLM_PROVIDER_FAILED")
        self.assertIn("answer", response["output"])


class MultiPersonaTests(unittest.TestCase):
    def test_roundtable_review_aggregates_four_personas(self) -> None:
        service = LlmService(make_settings(), MemoryCache())

        response = service.run_task(request("roundtable-review", {"title": "测试主张"}))

        meta = response["routeMeta"]
        self.assertEqual(meta["mode"], "multi_persona")
        sub_calls = response["subCalls"]
        self.assertEqual(len(sub_calls), 4)
        persona_ids = {item["personaId"] for item in sub_calls}
        self.assertEqual(
            persona_ids,
            {"logic_reviewer", "human_editor", "opponent_reader", "community_editor"},
        )
        reviews = response["output"]["reviews"]
        self.assertEqual(len(reviews), 4)
        for review in reviews:
            self.assertIn(review["_persona"], persona_ids)
            self.assertIn(review["severity"], {"high", "medium", "low"})
        # high-severity reviews must come first
        severities = [r["severity"] for r in reviews]
        rank = {"high": 0, "medium": 1, "low": 2}
        self.assertEqual(severities, sorted(severities, key=lambda s: rank[s]))
        self.assertEqual(response["output"]["personasUsed"], [
            "logic_reviewer", "human_editor", "opponent_reader", "community_editor",
        ])

    def test_persona_failure_only_falls_back_that_persona(self) -> None:
        # Replace zhihu_direct with one that raises so personas needing it fall back per-call.
        from app.providers import ZhihuDirectProvider

        class FlakyProvider:
            name = "zhihu_direct"
            calls = 0

            def run(self, task_type, input_data, prompt, persona=None):
                FlakyProvider.calls += 1
                if persona == "human_editor":
                    raise ProviderError("flaky")
                return ProviderResult(
                    output={
                        "reviews": [
                            {
                                "role": persona or "logic_reviewer",
                                "summary": "ok",
                                "problems": [],
                                "suggestions": [],
                                "severity": "low",
                            }
                        ]
                    },
                    provider_meta={"provider": self.name, "persona": persona},
                )

        settings = make_settings(provider_mode="zhihu")
        registry = Registry.load_default(settings)
        registry._providers["zhihu_direct"] = FlakyProvider()  # type: ignore[index]
        service = LlmService(settings, MemoryCache(), registry=registry)

        response = service.run_task(request("roundtable-review"))

        sub_calls = {item["personaId"]: item for item in response["subCalls"]}
        self.assertTrue(sub_calls["human_editor"]["fallback"])
        self.assertEqual(sub_calls["human_editor"]["provider"], "zhihu_direct")
        self.assertFalse(sub_calls["logic_reviewer"]["fallback"])
        self.assertTrue(response["fallback"])  # any-fallback bubbles up


class TraceTests(unittest.TestCase):
    def test_trace_file_contains_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(trace_enabled=True, trace_dir=tmp)
            service = LlmService(settings, MemoryCache())

            service.run_task(request("summarize-content"))
            service.run_task(request("roundtable-review"))

            files = list(pathlib.Path(tmp).glob("*.jsonl"))
            self.assertEqual(len(files), 1)
            lines = files[0].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            for line in lines:
                record = json.loads(line)
                for key in [
                    "ts", "taskType", "mode", "provider",
                    "fallback", "cacheHit", "latencyMs",
                    "promptVersion", "schemaVersion", "inputHash", "subCalls",
                ]:
                    self.assertIn(key, record)
            multi_record = json.loads(lines[1])
            self.assertEqual(multi_record["mode"], "multi_persona")
            self.assertEqual(len(multi_record["subCalls"]), 4)


if __name__ == "__main__":
    unittest.main()
