from __future__ import annotations

from dataclasses import dataclass

from kanshan_shared import load_config

_config = load_config()


@dataclass(frozen=True)
class Settings:
    provider_mode: str = _config.llm.provider_mode
    profile_service_url: str = _config.service_urls.profile
    zhihu_adapter_url: str = _config.service_urls.zhihu
    default_model: str = _config.llm.default_model
    openai_compat_base_url: str = _config.openai_compat.base_url
    openai_compat_api_key: str = _config.openai_compat.api_key
    openai_compat_model: str = _config.openai_compat.model
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
