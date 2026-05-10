from __future__ import annotations

from typing import Any

from .cache import CacheBackend, build_cache
from .hash_utils import stable_hash
from .registry import Registry
from .router import Router
from .settings import Settings, get_settings
from .trace import Tracer, now_ms, now_ts
from .validators import validate_output, validate_request


class LlmService:
    def __init__(
        self,
        settings: Settings | None = None,
        cache: CacheBackend | None = None,
        registry: Registry | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or build_cache(self.settings)
        self.registry = registry or Registry.load_default(self.settings)
        self.router = Router(self.registry)
        self.tracer = tracer if tracer is not None else Tracer(self.settings.trace_dir)

    def run_task(self, payload: dict[str, Any], expected_task: str | None = None) -> dict[str, Any]:
        task_type, input_data, prompt_version, schema_version = validate_request(payload, expected_task)
        prompt_version = prompt_version or self.settings.prompt_version
        schema_version = schema_version or self.settings.schema_version
        input_hash = stable_hash(input_data)
        cache_key = f"llm:{task_type}:{input_hash}:{prompt_version}:{schema_version}"

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

        started_ms = now_ms()
        output, fallback, route_meta, sub_calls = self.router.run(task_type, input_data, prompt_version)
        validate_output(task_type, output)

        response: dict[str, Any] = {
            "taskType": task_type,
            "schemaVersion": schema_version,
            "output": output,
            "fallback": fallback,
            "routeMeta": route_meta,
            "subCalls": sub_calls,
        }
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
