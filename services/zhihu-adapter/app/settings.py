"""Adapter settings backed by ``kanshan_shared.load_config``.

Historically the adapter had its own flat ``Settings`` dataclass with one
field per env var. v0.6 moves all credentials into the shared yaml/env
loader so every service consumes the same source of truth, while the
adapter exposes a thin facade that exposes exactly what its modules need.
"""

from __future__ import annotations

from dataclasses import dataclass

from kanshan_shared import KanshanConfig, load_config
from kanshan_shared.config import (
    CacheConfig,
    LoggingConfig,
    ZhihuConfig,
)


@dataclass(frozen=True)
class Settings:
    config: KanshanConfig

    @property
    def provider_mode(self) -> str:
        return self.config.provider_mode

    @property
    def zhihu(self) -> ZhihuConfig:
        return self.config.zhihu

    @property
    def cache_backend(self) -> str:
        return self.config.cache.backend

    @property
    def redis_url(self) -> str:
        return self.config.cache.redis_url

    @property
    def logging(self) -> LoggingConfig:
        return self.config.logging

    @property
    def demo_user_id(self) -> str:
        # Adapter quota counters are keyed per "user". We use a stable demo
        # user id while real per-user OAuth tokens are not yet wired through
        # the gateway; the field exists so the same call path works once
        # OAuth is fully integrated.
        return "demo-user"


def get_settings() -> Settings:
    return Settings(config=load_config())
