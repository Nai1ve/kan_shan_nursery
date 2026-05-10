"""OpenAI-compatible provider stub.

This provider is registered only when both ``OPENAI_COMPAT_BASE_URL`` and
``OPENAI_COMPAT_API_KEY`` env vars are set. Until then, it is a placeholder
to make the registry shape explicit. The real chat-completions call will be
wired in v0.5+ when an external endpoint is available.
"""

from __future__ import annotations

from typing import Any

from .base import Provider, ProviderError, ProviderResult


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        persona: str | None = None,
    ) -> ProviderResult:
        raise ProviderError("openai_compat provider is registered but not yet implemented")


__all__ = ["OpenAICompatProvider"]
