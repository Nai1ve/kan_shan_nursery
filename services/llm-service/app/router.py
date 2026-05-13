from __future__ import annotations

import concurrent.futures
from typing import Any

from .prompts import load_persona_prompt, load_prompt
from .providers import ProviderError, ProviderResult
from .providers.mock import MockProvider, run_mock_task
from .registry import PersonaSpec, Registry, TaskRoute
from .trace import now_ms
from .validators import validate_output


USER_PROVIDER_FAILED_NOTICE = {
    "code": "USER_LLM_PROVIDER_FAILED",
    "level": "warning",
    "message": "你的自定义 LLM 连接失败，已切换到平台免费额度兜底。请检查 Base URL、API Key 或模型名称。",
}


class Router:
    """Resolves task routing and dispatches to one or more providers.

    Returns a tuple ``(output, fallback, route_meta, sub_calls)`` where
    ``route_meta`` is suitable for storing in trace records and providerMeta
    fields, and ``sub_calls`` is a list (possibly empty) of per-persona run
    summaries for multi_persona tasks.
    """

    def __init__(self, registry: Registry) -> None:
        self.registry = registry
        self._mock = MockProvider()

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt_version: str,
        user_provider: Any | None = None,
        user_provider_id: str | None = None,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        route = self.registry.resolve_route(task_type)
        if route.mode == "multi_persona":
            return self._run_multi_persona(task_type, input_data, prompt_version, route, user_provider, user_provider_id)
        return self._run_single(task_type, input_data, prompt_version, route, user_provider, user_provider_id)

    def _run_single(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt_version: str,
        route: TaskRoute,
        user_provider: Any | None = None,
        user_provider_id: str | None = None,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        prompt = load_prompt(task_type, prompt_version)
        if user_provider is not None:
            try:
                result = user_provider.run(task_type, input_data, prompt)
                validate_output(task_type, result.output)
                meta = {
                    "mode": "single",
                    "provider": "user_provider",
                    "providerSource": "user_provider",
                    "providerId": user_provider_id or "user_openai_compat",
                    "fallback": False,
                    "platformProvider": self.registry.effective_provider(route),
                }
                return result.output, False, meta, []
            except (ProviderError, KeyError, ValueError) as error:
                output, _, meta, sub_calls = self._run_platform_single(task_type, input_data, prompt, route)
                meta.update(
                    {
                        "fallback": True,
                        "fallbackFrom": "user_provider",
                        "providerSource": "platform_free",
                        "userProviderFailed": True,
                        "userProviderError": _summarize_error(error),
                        "notice": USER_PROVIDER_FAILED_NOTICE,
                    }
                )
                return output, True, meta, sub_calls

        return self._run_platform_single(task_type, input_data, prompt, route)

    def _run_platform_single(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        route: TaskRoute,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        primary_name = self.registry.effective_provider(route)
        fallback_name = route.fallback or "mock"
        meta = {"mode": "single", "provider": primary_name, "providerSource": "platform_free", "fallback": False}
        try:
            provider = self.registry.get_provider(primary_name)
            result = provider.run(task_type, input_data, prompt)
            validate_output(task_type, result.output)
            return result.output, False, meta, []
        except (ProviderError, KeyError, ValueError):
            fallback_provider = (
                self.registry.get_provider(fallback_name)
                if self.registry.has_provider(fallback_name)
                else self._mock
            )
            fallback_result = fallback_provider.run(task_type, input_data, prompt)
            validate_output(task_type, fallback_result.output)
            meta = {
                "mode": "single",
                "provider": primary_name,
                "providerSource": "platform_free",
                "fallback": True,
                "fallbackTo": fallback_provider.name,
            }
            return fallback_result.output, True, meta, []

    def _run_multi_persona(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt_version: str,
        route: TaskRoute,
        user_provider: Any | None = None,
        user_provider_id: str | None = None,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        base_prompt = load_prompt(task_type, prompt_version)
        sub_calls: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []

        def call_persona(persona: PersonaSpec) -> dict[str, Any]:
            persona_prompt = load_persona_prompt(prompt_version, persona.persona_prompt)
            full_prompt = f"{base_prompt}\n\n---\n{persona_prompt}" if persona_prompt else base_prompt
            provider_name = self.registry.effective_persona_provider(persona)
            started = now_ms()
            user_provider_failed = False
            user_provider_error = None
            if user_provider is not None:
                try:
                    result = user_provider.run(task_type, input_data, full_prompt, persona=persona.id)
                    validate_output(task_type, result.output)
                    return {
                        "personaId": persona.id,
                        "provider": "user_provider",
                        "providerSource": "user_provider",
                        "providerId": user_provider_id or "user_openai_compat",
                        "fallback": False,
                        "userProviderFailed": False,
                        "latencyMs": now_ms() - started,
                        "output": result.output,
                    }
                except (ProviderError, KeyError, ValueError) as error:
                    user_provider_failed = True
                    user_provider_error = _summarize_error(error)
            try:
                provider = self.registry.get_provider(provider_name)
                result: ProviderResult = provider.run(task_type, input_data, full_prompt, persona=persona.id)
                validate_output(task_type, result.output)
                fallback = user_provider_failed
                provider_source = "platform_free"
            except (ProviderError, KeyError, ValueError):
                result = self._mock.run(task_type, input_data, full_prompt, persona=persona.id)
                validate_output(task_type, result.output)
                fallback = True
                provider_source = "platform_free"
            return {
                "personaId": persona.id,
                "provider": provider_name,
                "providerSource": provider_source,
                "fallback": fallback,
                "userProviderFailed": user_provider_failed,
                "userProviderError": user_provider_error,
                "latencyMs": now_ms() - started,
                "output": result.output,
            }

        if not route.personas:
            mock_output = run_mock_task(task_type, input_data)
            return mock_output, False, {"mode": "multi_persona", "provider": "mock", "fallback": False}, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(route.personas)) as pool:
            results = list(pool.map(call_persona, route.personas))

        any_fallback = any(item["fallback"] for item in results)
        any_user_provider_failed = any(item.get("userProviderFailed") for item in results)
        for item in results:
            output = item["output"]
            persona_reviews = output.get("reviews") or []
            for review in persona_reviews:
                review = {**review, "_persona": item["personaId"], "_provider": item["provider"]}
                reviews.append(review)
            sub_calls.append(
                {
                    "personaId": item["personaId"],
                    "provider": item["provider"],
                    "providerSource": item.get("providerSource", "platform_free"),
                    "providerId": item.get("providerId"),
                    "fallback": item["fallback"],
                    "userProviderFailed": item.get("userProviderFailed", False),
                    "userProviderError": item.get("userProviderError"),
                    "latencyMs": item["latencyMs"],
                }
            )

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        reviews.sort(key=lambda item: severity_rank.get(item.get("severity", "low"), 3))

        aggregated = {
            "reviews": reviews,
            "summary": _build_aggregate_summary(reviews),
            "personasUsed": [persona.id for persona in route.personas],
        }
        meta = {
            "mode": "multi_persona",
            "provider": "multi_persona",
            "providerSource": "platform_free" if any_user_provider_failed else ("user_provider" if user_provider else "platform_free"),
            "fallback": any_fallback,
        }
        if user_provider is not None:
            meta["providerId"] = user_provider_id or "user_openai_compat"
        if any_user_provider_failed:
            meta["userProviderFailed"] = True
            meta["notice"] = USER_PROVIDER_FAILED_NOTICE
        return aggregated, any_fallback, meta, sub_calls


def _summarize_error(error: Exception) -> str:
    message = str(error)
    return message if len(message) <= 240 else f"{message[:237]}..."


def _build_aggregate_summary(reviews: list[dict[str, Any]]) -> str:
    high = sum(1 for r in reviews if r.get("severity") == "high")
    medium = sum(1 for r in reviews if r.get("severity") == "medium")
    low = sum(1 for r in reviews if r.get("severity") == "low")
    return f"圆桌审稿汇总：{high} 严重 / {medium} 中等 / {low} 轻度。"
