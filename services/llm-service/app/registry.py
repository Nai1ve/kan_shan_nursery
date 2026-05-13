from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .providers import (
    MockProvider,
    OpenAICompatProvider,
    Provider,
    ZhihuDirectProvider,
)
from .settings import Settings


CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@dataclass(frozen=True)
class PersonaSpec:
    id: str
    provider: str
    persona_prompt: str | None = None


@dataclass(frozen=True)
class TaskRoute:
    mode: str  # "single" or "multi_persona"
    provider: str | None
    fallback: str | None
    personas: tuple[PersonaSpec, ...] = ()


class Registry:
    """Loads providers + routing config and resolves Provider instances per task."""

    def __init__(self, settings: Settings, config: dict[str, Any]) -> None:
        self.settings = settings
        self._config = config
        self._providers: dict[str, Provider] = {}
        self._build_providers()

    @classmethod
    def load_default(cls, settings: Settings) -> "Registry":
        config_path = CONFIG_DIR / "providers.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(settings, config)

    def _build_providers(self) -> None:
        for name, spec in (self._config.get("providers") or {}).items():
            ptype = spec.get("type")
            if ptype == "mock":
                self._providers[name] = MockProvider()
            elif ptype == "zhihu_direct":
                if self.settings.zhihu_adapter_url:
                    self._providers[name] = ZhihuDirectProvider(
                        base_url=self.settings.zhihu_adapter_url,
                        model=self.settings.default_model,
                        timeout_seconds=self.settings.request_timeout_seconds,
                    )
            elif ptype == "openai_compat":
                base_url = self.settings.openai_compat_base_url
                api_key = self.settings.openai_compat_api_key
                model = self.settings.openai_compat_model or "gpt-4o-mini"

                if base_url and api_key:
                    self._providers[name] = OpenAICompatProvider(
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                        timeout_seconds=self.settings.request_timeout_seconds,
                    )
            else:
                raise ValueError(f"Unknown provider type: {ptype}")

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    def get_provider(self, name: str) -> Provider:
        if name not in self._providers:
            raise KeyError(f"Provider not registered: {name}")
        return self._providers[name]

    def resolve_route(self, task_type: str) -> TaskRoute:
        per_task = (self._config.get("routing") or {}).get("per_task") or {}
        default = (self._config.get("routing") or {}).get("default") or {"provider": "mock", "fallback": None}
        cfg = per_task.get(task_type, default)
        mode = cfg.get("mode", "single")
        if mode == "multi_persona":
            personas = tuple(
                PersonaSpec(
                    id=item["id"],
                    provider=item["provider"],
                    persona_prompt=item.get("persona_prompt"),
                )
                for item in cfg.get("personas") or []
            )
            return TaskRoute(mode="multi_persona", provider=None, fallback=cfg.get("fallback"), personas=personas)
        return TaskRoute(
            mode="single",
            provider=cfg.get("provider"),
            fallback=cfg.get("fallback"),
            personas=(),
        )

    def effective_provider(self, route: TaskRoute) -> str:
        """Apply LLM_PROVIDER_MODE env to override default routing.

        - mock: force every single-mode task onto mock; multi_persona personas
          fall back to mock too (handled at run time when the configured
          provider is missing or LLM_PROVIDER_MODE=mock).
        - zhihu: force zhihu_direct + mock fallback.
        - openai_compat: force openai_compat + mock fallback.
        """
        if self.settings.provider_mode == "mock":
            return "mock"
        if self.settings.provider_mode == "zhihu":
            return "zhihu_direct"
        if self.settings.provider_mode == "openai_compat":
            return "openai_compat"
        return route.provider or "mock"

    def effective_persona_provider(self, persona: PersonaSpec) -> str:
        if self.settings.provider_mode == "mock":
            return "mock"
        if self.settings.provider_mode == "zhihu":
            return "zhihu_direct"
        if self.settings.provider_mode == "openai_compat":
            return "openai_compat"
        return persona.provider
