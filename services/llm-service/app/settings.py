from __future__ import annotations

from dataclasses import dataclass

from kanshan_shared import load_config

_config = load_config()


@dataclass(frozen=True)
class Settings:
    provider_mode: str = _config.llm.provider_mode
    zhihu_adapter_url: str = _config.service_urls.zhihu
    default_model: str = _config.llm.default_model
    prompt_version: str = _config.llm.prompt_version
    schema_version: str = _config.llm.schema_version
    cache_backend: str = _config.llm.cache_backend
    redis_url: str = _config.cache.redis_url
    cache_ttl_seconds: int = _config.llm.cache_ttl_seconds
    request_timeout_seconds: float = float(_config.llm.request_timeout_seconds)
    trace_dir: str = _config.llm.trace_dir
    trace_enabled: bool = _config.llm.trace_enabled


def get_settings() -> Settings:
    return Settings()
