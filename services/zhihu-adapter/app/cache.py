import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .settings import Settings


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        ...

    def get_quota(self, endpoint: str, user_id: str) -> int:
        ...

    def increment_quota(self, endpoint: str, user_id: str) -> int:
        ...


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class MemoryCache:
    """Local fallback cache with the same semantics expected from Redis in P0 tests."""

    def __init__(self) -> None:
        self._values: dict[str, CacheEntry] = {}
        self._counters: dict[str, tuple[int, str]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._values.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._values.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._values[key] = CacheEntry(value=value, expires_at=time.time() + ttl_seconds)

    def quota_key(self, endpoint: str, user_id: str) -> str:
        today = datetime.now().strftime("%Y%m%d")
        return f"quota:{endpoint}:{user_id}:{today}"

    def get_quota(self, endpoint: str, user_id: str) -> int:
        key = self.quota_key(endpoint, user_id)
        value, _ = self._counters.get(key, (0, key))
        return value

    def increment_quota(self, endpoint: str, user_id: str) -> int:
        key = self.quota_key(endpoint, user_id)
        value, _ = self._counters.get(key, (0, key))
        next_value = value + 1
        self._counters[key] = (next_value, key)
        return next_value


class RedisCache:
    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("Install redis dependency or set ZHIHU_CACHE_BACKEND=memory.") from exc
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> Any | None:
        import json

        value = self.client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        import json

        self.client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))

    def quota_key(self, endpoint: str, user_id: str) -> str:
        today = datetime.now().strftime("%Y%m%d")
        return f"quota:{endpoint}:{user_id}:{today}"

    def get_quota(self, endpoint: str, user_id: str) -> int:
        value = self.client.get(self.quota_key(endpoint, user_id))
        return int(value or 0)

    def increment_quota(self, endpoint: str, user_id: str) -> int:
        key = self.quota_key(endpoint, user_id)
        value = int(self.client.incr(key))
        self.client.expire(key, 36 * 60 * 60)
        return value


def build_cache(settings: Settings) -> CacheBackend:
    if settings.cache_backend == "redis":
        return RedisCache(settings.redis_url)
    return MemoryCache()
