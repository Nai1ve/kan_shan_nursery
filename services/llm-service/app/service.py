from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from .cache import CacheBackend, build_cache
from .hash_utils import stable_hash
from .providers.openai_compat import OpenAICompatProvider
from .registry import Registry
from .router import USER_PROVIDER_FAILED_NOTICE
from .router import Router
from .settings import Settings, get_settings
from .trace import Tracer, now_ms, now_ts
from .validators import validate_output, validate_request


PERSONAL_LLM_TASKS = {
    "answer-seed-question",
    "supplement-material",
    "sprout-opportunities",
    "switch-sprout-angle",
    "argument-blueprint",
    "generate-outline",
    "draft",
    "roundtable-review",
    "feedback-summary",
    "profile-memory-synthesis",
}


class QuotaExceeded(Exception):
    def __init__(self, task_type: str, used: int, limit: int) -> None:
        self.task_type = task_type
        self.used = used
        self.limit = limit
        super().__init__(f"Quota exceeded for {task_type}: {used}/{limit}")


class LlmService:
    def __init__(
        self,
        settings: Settings | None = None,
        cache: CacheBackend | None = None,
        registry: Registry | None = None,
        tracer: Tracer | None = None,
        quota_limits: dict[str, int] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or build_cache(self.settings)
        self.registry = registry or Registry.load_default(self.settings)
        self.router = Router(self.registry)
        self.tracer = tracer if tracer is not None else Tracer(self.settings.trace_dir)
        self.quota_limits = quota_limits or {}

    def run_task(self, payload: dict[str, Any], expected_task: str | None = None, user_id: str = "default") -> dict[str, Any]:
        task_type, input_data, prompt_version, schema_version = validate_request(payload, expected_task)
        prompt_version = prompt_version or self.settings.prompt_version
        schema_version = schema_version or self.settings.schema_version
        user_config = self._resolve_user_llm_config(payload, task_type, user_id)
        user_provider = self._build_user_provider(user_config) if user_config else None
        provider_cache_key = self._provider_cache_key(task_type, user_config)
        input_hash = stable_hash(input_data)
        cache_key = f"llm:{task_type}:{input_hash}:{prompt_version}:{schema_version}:{provider_cache_key}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            self._emit_trace(
                task_type,
                cache_key,
                input_hash,
                prompt_version,
                schema_version,
                started_ms=now_ms(),
                cache_hit=True,
                fallback=cached.get("fallback", False),
                route_meta=cached.get("routeMeta", {}),
                sub_calls=cached.get("subCalls", []),
            )
            return {
                **cached,
                "cache": {"hit": True, "key": cache_key, "ttlSeconds": self.settings.cache_ttl_seconds},
            }

        limit = self.quota_limits.get(task_type, 0)
        if limit > 0 and user_provider is None:
            used = self.cache.get_quota(task_type, user_id)
            if used >= limit:
                raise QuotaExceeded(task_type, used, limit)

        started_ms = now_ms()
        output, fallback, route_meta, sub_calls = self.router.run(
            task_type,
            input_data,
            prompt_version,
            user_provider=user_provider,
            user_provider_id=user_config.get("providerId") if user_config else None,
        )
        validate_output(task_type, output)
        notices = self._build_notices(route_meta)

        if limit > 0 and self._used_platform_provider(route_meta):
            self.cache.increment_quota(task_type, user_id)

        response: dict[str, Any] = {
            "taskType": task_type,
            "schemaVersion": schema_version,
            "output": output,
            "fallback": fallback,
            "routeMeta": route_meta,
            "subCalls": sub_calls,
        }
        if notices:
            response["notices"] = notices
        self.cache.set(cache_key, response, self.settings.cache_ttl_seconds)
        self._emit_trace(
            task_type,
            cache_key,
            input_hash,
            prompt_version,
            schema_version,
            started_ms=started_ms,
            cache_hit=False,
            fallback=fallback,
            route_meta=route_meta,
            sub_calls=sub_calls,
        )
        return {
            **response,
            "cache": {"hit": False, "key": cache_key, "ttlSeconds": self.settings.cache_ttl_seconds},
        }

    def get_config_status(self, user_id: str = "default") -> dict[str, Any]:
        user_config = self._fetch_user_llm_config(user_id, include_secret=False)
        quota = self.get_quota(user_id)
        if user_config and user_config.get("activeProvider") == "user_provider":
            public_config = {key: value for key, value in user_config.items() if key != "apiKey"}
            return {
                **public_config,
                "quota": quota,
                "fallbackProvider": "platform_free",
                "routingPolicy": {
                    "genericExtraction": "platform_free",
                    "personalTasks": "user_provider_with_platform_fallback",
                },
            }
        return {
            "status": "platform_free",
            "activeProvider": "platform_free",
            "displayName": "平台免费额度",
            "quota": quota,
            "routingPolicy": {
                "genericExtraction": "platform_free",
                "personalTasks": "platform_free",
            },
        }

    def get_quota(self, user_id: str = "default") -> dict[str, dict[str, int]]:
        """Return quota usage for all task types."""
        result = {}
        for task_type, limit in self.quota_limits.items():
            used = self.cache.get_quota(task_type, user_id)
            result[task_type] = {"used": used, "limit": limit, "remaining": max(0, limit - used)}
        return result

    def _resolve_user_llm_config(self, payload: dict[str, Any], task_type: str, user_id: str) -> dict[str, Any] | None:
        if task_type not in PERSONAL_LLM_TASKS:
            return None
        inline_config = payload.get("userLlmConfig") or payload.get("llmProvider") or payload.get("providerConfig")
        if isinstance(inline_config, dict):
            normalized = self._normalize_user_llm_config(inline_config)
            if normalized:
                return normalized
        return self._fetch_user_llm_config(user_id, include_secret=True)

    def _fetch_user_llm_config(self, user_id: str, *, include_secret: bool) -> dict[str, Any] | None:
        if not user_id or user_id == "default" or not self.settings.profile_service_url:
            return None
        query = urllib.parse.urlencode({"user_id": user_id, "include_secret": str(include_secret).lower()})
        url = f"{self.settings.profile_service_url.rstrip('/')}/profiles/me/llm-config?{query}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.settings.request_timeout_seconds) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None
        return self._normalize_user_llm_config(raw, require_secret=include_secret)

    def _normalize_user_llm_config(self, config: dict[str, Any], *, require_secret: bool = True) -> dict[str, Any] | None:
        active_provider = config.get("activeProvider") or config.get("active_provider")
        if active_provider != "user_provider":
            return None
        base_url = config.get("baseUrl") or config.get("base_url") or ""
        api_key = config.get("apiKey") or config.get("api_key") or ""
        model = config.get("model") or ""
        if not base_url or not model:
            return None
        if require_secret and not api_key:
            return None
        return {
            "status": "user_configured",
            "activeProvider": "user_provider",
            "providerId": stable_hash({"provider": "openai_compat", "baseUrl": base_url, "model": model})[:12],
            "provider": "openai_compat",
            "displayName": config.get("displayName") or "自有 LLM",
            "baseUrl": base_url,
            "apiKey": api_key,
            "model": model,
        }

    def _build_user_provider(self, config: dict[str, Any] | None) -> OpenAICompatProvider | None:
        if not config:
            return None
        return OpenAICompatProvider(
            base_url=config["baseUrl"],
            api_key=config["apiKey"],
            model=config["model"],
            timeout_seconds=self.settings.request_timeout_seconds,
        )

    def _provider_cache_key(self, task_type: str, user_config: dict[str, Any] | None) -> str:
        if task_type not in PERSONAL_LLM_TASKS or not user_config:
            return "platform"
        return "user:" + stable_hash({
            "provider": user_config.get("provider"),
            "baseUrl": user_config.get("baseUrl"),
            "model": user_config.get("model"),
            "apiKeyHash": stable_hash(user_config.get("apiKey", ""))[:12],
        })[:16]

    def _used_platform_provider(self, route_meta: dict[str, Any]) -> bool:
        if route_meta.get("providerSource") == "user_provider" and not route_meta.get("userProviderFailed"):
            return False
        return True

    def _build_notices(self, route_meta: dict[str, Any]) -> list[dict[str, Any]]:
        if route_meta.get("userProviderFailed"):
            return [route_meta.get("notice") or USER_PROVIDER_FAILED_NOTICE]
        return []

    def _emit_trace(
        self,
        task_type: str,
        cache_key: str,
        input_hash: str,
        prompt_version: str,
        schema_version: str,
        *,
        started_ms: int,
        cache_hit: bool,
        fallback: bool,
        route_meta: dict[str, Any],
        sub_calls: list[dict[str, Any]],
    ) -> None:
        if not self.settings.trace_enabled:
            return
        record = {
            "ts": now_ts(),
            "taskType": task_type,
            "mode": route_meta.get("mode", "single"),
            "provider": route_meta.get("provider"),
            "fallback": fallback,
            "fallbackTo": route_meta.get("fallbackTo"),
            "cacheHit": cache_hit,
            "cacheKey": cache_key,
            "latencyMs": now_ms() - started_ms,
            "promptVersion": prompt_version,
            "schemaVersion": schema_version,
            "inputHash": input_hash,
            "subCalls": sub_calls,
        }
        self.tracer.emit(record)
