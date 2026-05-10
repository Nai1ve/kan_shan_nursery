import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
