from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Protocol

from .settings import Settings


class CacheBackend(Protocol):
    def get(self, key: str) -> dict[str, Any] | None:
        ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        ...

    def get_quota(self, task_type: str, user_id: str) -> int:
        ...

    def increment_quota(self, task_type: str, user_id: str) -> int:
        ...


class MemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, dict[str, Any]]] = {}
        self._counters: dict[str, tuple[int, str]] = {}

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

    def _quota_key(self, task_type: str, user_id: str) -> str:
        today = datetime.now().strftime("%Y%m%d")
        return f"quota:{task_type}:{user_id}:{today}"

    def get_quota(self, task_type: str, user_id: str) -> int:
        key = self._quota_key(task_type, user_id)
        value, _ = self._counters.get(key, (0, key))
        return value

    def increment_quota(self, task_type: str, user_id: str) -> int:
        key = self._quota_key(task_type, user_id)
        value, _ = self._counters.get(key, (0, key))
        next_value = value + 1
        self._counters[key] = (next_value, key)
        return next_value


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

    def _quota_key(self, task_type: str, user_id: str) -> str:
        today = datetime.now().strftime("%Y%m%d")
        return f"quota:{task_type}:{user_id}:{today}"

    def get_quota(self, task_type: str, user_id: str) -> int:
        value = self.client.get(self._quota_key(task_type, user_id))
        return int(value or 0)

    def increment_quota(self, task_type: str, user_id: str) -> int:
        key = self._quota_key(task_type, user_id)
        value = int(self.client.incr(key))
        self.client.expire(key, 36 * 60 * 60)
        return value


def build_cache(settings: Settings) -> CacheBackend:
    if settings.cache_backend == "redis":
        return RedisCache(settings.redis_url)
    return MemoryCache()
