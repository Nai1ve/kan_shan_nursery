from __future__ import annotations

from typing import Any

from .cache import CacheBackend, build_cache
from .hash_utils import stable_hash
from .settings import Settings, get_settings
from .validators import validate_output, validate_request
from .zhihu_provider import run_with_fallback


class LlmService:
    def __init__(self, settings: Settings | None = None, cache: CacheBackend | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or build_cache(self.settings)

    def run_task(self, payload: dict[str, Any], expected_task: str | None = None) -> dict[str, Any]:
        task_type, input_data, prompt_version, schema_version = validate_request(payload, expected_task)
        prompt_version = prompt_version or self.settings.prompt_version
        schema_version = schema_version or self.settings.schema_version
        cache_key = self._cache_key(task_type, input_data, prompt_version, schema_version)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return {
                **cached,
                "cache": {"hit": True, "key": cache_key, "ttlSeconds": self.settings.cache_ttl_seconds},
            }

        output, fallback = run_with_fallback(task_type, input_data, self.settings, prompt_version)
        validate_output(task_type, output)
        response = {
            "taskType": task_type,
            "schemaVersion": schema_version,
            "output": output,
            "fallback": fallback,
        }
        self.cache.set(cache_key, response, self.settings.cache_ttl_seconds)
        return {
            **response,
            "cache": {"hit": False, "key": cache_key, "ttlSeconds": self.settings.cache_ttl_seconds},
        }

    def _cache_key(self, task_type: str, input_data: dict[str, Any], prompt_version: str, schema_version: str) -> str:
        return f"llm:{task_type}:{stable_hash(input_data)}:{prompt_version}:{schema_version}"
