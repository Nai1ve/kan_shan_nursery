import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cache import MemoryCache
from app.service import LlmService
from app.settings import Settings
from app.validators import TASK_REQUIRED_KEYS


def request(task_type: str, input_data: dict | None = None) -> dict:
    return {
        "taskType": task_type,
        "input": input_data or {"title": "AI Coding 与程序员成长"},
        "promptVersion": "v1",
        "schemaVersion": "v1",
    }


class LlmServiceTests(unittest.TestCase):
    def test_all_mock_tasks_return_required_keys(self) -> None:
        service = LlmService(Settings(provider_mode="mock"), MemoryCache())
        for task_type, required_keys in TASK_REQUIRED_KEYS.items():
            with self.subTest(task_type=task_type):
                response = service.run_task(request(task_type))
                self.assertEqual(response["taskType"], task_type)
                self.assertFalse(response["cache"]["hit"])
                self.assertTrue(required_keys.issubset(response["output"].keys()))

    def test_cache_hit_reuses_same_task_output(self) -> None:
        service = LlmService(Settings(provider_mode="mock"), MemoryCache())
        first = service.run_task(request("generate-writing-angles"))
        second = service.run_task(request("generate-writing-angles"))

        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["output"], second["output"])

    def test_expected_task_must_match_path_task(self) -> None:
        service = LlmService(Settings(provider_mode="mock"), MemoryCache())
        with self.assertRaises(ValueError):
            service.run_task(request("draft"), expected_task="summarize-content")

    def test_zhihu_provider_failure_falls_back_to_mock(self) -> None:
        settings = Settings(provider_mode="zhihu", zhihu_adapter_url="http://127.0.0.1:1", request_timeout_seconds=0.01)
        service = LlmService(settings, MemoryCache())

        response = service.run_task(request("answer-seed-question", {"question": "有没有证据？"}))

        self.assertTrue(response["fallback"])
        self.assertIn("answer", response["output"])


if __name__ == "__main__":
    unittest.main()
