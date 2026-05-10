from __future__ import annotations

import json
import time
from typing import Any, Protocol

from .settings import Settings


class CacheBackend(Protocol):
    def get(self, key: str) -> dict[str, Any] | None:
        ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        ...


class MemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, dict[str, Any]]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._values.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= time.time():
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._values[key] = (time.time() + ttl_seconds, value)


class RedisCache:
    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("Install redis dependency or set LLM_CACHE_BACKEND=memory.") from exc
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self.client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))


def build_cache(settings: Settings) -> CacheBackend:
    if settings.cache_backend == "redis":
        return RedisCache(settings.redis_url)
    return MemoryCache()
