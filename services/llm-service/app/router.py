from __future__ import annotations

import concurrent.futures
from typing import Any

from .prompts import load_persona_prompt, load_prompt
from .providers import ProviderError, ProviderResult
from .providers.mock import MockProvider, run_mock_task
from .registry import PersonaSpec, Registry, TaskRoute
from .trace import now_ms


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
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        route = self.registry.resolve_route(task_type)
        if route.mode == "multi_persona":
            return self._run_multi_persona(task_type, input_data, prompt_version, route)
        return self._run_single(task_type, input_data, prompt_version, route)

    def _run_single(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt_version: str,
        route: TaskRoute,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        prompt = load_prompt(task_type, prompt_version)
        primary_name = self.registry.effective_provider(route)
        fallback_name = route.fallback or "mock"
        meta = {"mode": "single", "provider": primary_name, "fallback": False}
        try:
            provider = self.registry.get_provider(primary_name)
            result = provider.run(task_type, input_data, prompt)
            return result.output, False, meta, []
        except (ProviderError, KeyError):
            fallback_provider = (
                self.registry.get_provider(fallback_name)
                if self.registry.has_provider(fallback_name)
                else self._mock
            )
            fallback_result = fallback_provider.run(task_type, input_data, prompt)
            meta = {"mode": "single", "provider": primary_name, "fallback": True, "fallbackTo": fallback_provider.name}
            return fallback_result.output, True, meta, []

    def _run_multi_persona(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt_version: str,
        route: TaskRoute,
    ) -> tuple[dict[str, Any], bool, dict[str, Any], list[dict[str, Any]]]:
        base_prompt = load_prompt(task_type, prompt_version)
        sub_calls: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []

        def call_persona(persona: PersonaSpec) -> dict[str, Any]:
            persona_prompt = load_persona_prompt(prompt_version, persona.persona_prompt)
            full_prompt = f"{base_prompt}\n\n---\n{persona_prompt}" if persona_prompt else base_prompt
            provider_name = self.registry.effective_persona_provider(persona)
            started = now_ms()
            try:
                provider = self.registry.get_provider(provider_name)
                result: ProviderResult = provider.run(task_type, input_data, full_prompt, persona=persona.id)
                fallback = False
            except (ProviderError, KeyError):
                result = self._mock.run(task_type, input_data, full_prompt, persona=persona.id)
                fallback = True
            return {
                "personaId": persona.id,
                "provider": provider_name,
                "fallback": fallback,
                "latencyMs": now_ms() - started,
                "output": result.output,
            }

        if not route.personas:
            mock_output = run_mock_task(task_type, input_data)
            return mock_output, False, {"mode": "multi_persona", "provider": "mock", "fallback": False}, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(route.personas)) as pool:
            results = list(pool.map(call_persona, route.personas))

        any_fallback = any(item["fallback"] for item in results)
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
                    "fallback": item["fallback"],
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
        meta = {"mode": "multi_persona", "provider": "multi_persona", "fallback": any_fallback}
        return aggregated, any_fallback, meta, sub_calls


def _build_aggregate_summary(reviews: list[dict[str, Any]]) -> str:
    high = sum(1 for r in reviews if r.get("severity") == "high")
    medium = sum(1 for r in reviews if r.get("severity") == "medium")
    low = sum(1 for r in reviews if r.get("severity") == "low")
    return f"圆桌审稿汇总：{high} 严重 / {medium} 中等 / {low} 轻度。"
