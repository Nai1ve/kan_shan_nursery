from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ProviderError(Exception):
    """Raised when a provider fails to produce a usable structured output."""


@dataclass
class ProviderResult:
    output: dict[str, Any]
    provider_meta: dict[str, Any]


class Provider(Protocol):
    name: str

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        persona: str | None = None,
    ) -> ProviderResult:
        ...
