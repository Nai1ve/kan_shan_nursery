from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider_mode: str = os.getenv("LLM_PROVIDER_MODE", "mock")
    zhihu_adapter_url: str = os.getenv("ZHIHU_ADAPTER_URL", "http://127.0.0.1:8070")
    default_model: str = os.getenv("LLM_DEFAULT_MODEL", "zhida-thinking-1p5")
    prompt_version: str = os.getenv("LLM_PROMPT_VERSION", "v1")
    schema_version: str = os.getenv("LLM_SCHEMA_VERSION", "v1")
    cache_backend: str = os.getenv("LLM_CACHE_BACKEND", "memory")
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    cache_ttl_seconds: int = int(os.getenv("LLM_CACHE_TTL_SECONDS", str(6 * 60 * 60)))
    request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "20"))


def get_settings() -> Settings:
    return Settings()
