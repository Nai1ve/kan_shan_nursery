"""Seed fixtures preloaded into the in-memory repository.

These seeds match the two demo seeds that the frontend mock-data.ts has
historically shown so the gateway-backed view shows the same starting
state as the legacy /api/mock/seeds route. They use stable ids so a
demo-mode reset still finds them.
"""

from __future__ import annotations

from typing import Any


CREATED_AT = "2026-05-09T09:00:00+08:00"


SEED_FIXTURES: list[dict[str, Any]] = []


def initial_seeds() -> list[dict[str, Any]]:
    """Return deep-copied fixtures so the in-memory repo can mutate freely."""
    import copy
    return copy.deepcopy(SEED_FIXTURES)
