from __future__ import annotations

from typing import Any

from kanshan_shared.categories import ALL_CATEGORIES


def build_categories() -> list[dict[str, Any]]:
    """Build category dicts from the canonical shared definition."""
    return [
        {"id": cat.id, "name": cat.name, "meta": "", "kind": cat.kind}
        for cat in ALL_CATEGORIES
    ]
