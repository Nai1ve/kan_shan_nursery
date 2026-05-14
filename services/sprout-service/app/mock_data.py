from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


SEED_OPPORTUNITIES: list[dict[str, Any]] = []


VALID_STATUSES = {"new", "supplemented", "angle_changed", "dismissed", "writing"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def initial_opportunities() -> list[dict[str, Any]]:
    return [dict(item) for item in SEED_OPPORTUNITIES]
