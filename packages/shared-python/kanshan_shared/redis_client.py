"""Shared Redis client factory.

Usage::

    from kanshan_shared.redis_client import get_redis_client

    r = get_redis_client("redis://127.0.0.1:6379/0")
    r.set("key", "value", ex=60)
"""

from __future__ import annotations

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


def get_redis_client(redis_url: str):
    if redis is None:
        raise RuntimeError(
            "redis package not installed. Install with: pip install redis>=5.0.0"
        )
    return redis.Redis.from_url(redis_url, decode_responses=True)
