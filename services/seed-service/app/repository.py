from __future__ import annotations

from typing import Any

from .seed_fixtures import initial_seeds


class SeedRepository:
    def __init__(self, *, preload: bool = True) -> None:
        self._seeds: dict[str, dict[str, Any]] = {}
        if preload:
            for seed in initial_seeds():
                self._seeds[seed["id"]] = seed

    def list(self) -> list[dict[str, Any]]:
        return list(self._seeds.values())

    def get(self, seed_id: str) -> dict[str, Any] | None:
        return self._seeds.get(seed_id)

    def find_by_card_id(self, card_id: str) -> dict[str, Any] | None:
        return next((seed for seed in self._seeds.values() if seed.get("createdFromCardId") == card_id), None)

    def save(self, seed: dict[str, Any]) -> dict[str, Any]:
        self._seeds[seed["id"]] = seed
        return seed

    def delete(self, seed_id: str) -> None:
        self._seeds.pop(seed_id, None)
