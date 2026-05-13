"""PostgreSQL-backed seed repository."""

from __future__ import annotations

import json
from typing import Any

from .database import get_db_session_factory
from .models import SeedTable


class PostgresSeedRepository:
    def __init__(self, *, preload: bool = True) -> None:
        self._SessionFactory = get_db_session_factory()
        if preload:
            self._ensure_fixtures()

    def _ensure_fixtures(self):
        from .seed_fixtures import initial_seeds
        session = self._SessionFactory()
        try:
            existing = session.query(SeedTable).count()
            if existing == 0:
                for seed in initial_seeds():
                    session.add(SeedTable(
                        id=seed["id"],
                        user_id=seed.get("userId"),
                        title=seed.get("title", ""),
                        interest_id=seed.get("interestId"),
                        core_claim=seed.get("coreClaim"),
                        user_reaction=seed.get("userReaction"),
                        status=seed.get("status"),
                        maturity_score=str(seed.get("maturityScore", 0)),
                        data=json.dumps(seed, ensure_ascii=False),
                    ))
                session.commit()
        finally:
            session.close()

    def list(self) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            rows = session.query(SeedTable).all()
            return [json.loads(r.data) for r in rows]
        finally:
            session.close()

    def get(self, seed_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(SeedTable, seed_id)
            return json.loads(row.data) if row else None
        finally:
            session.close()

    def find_by_card_id(self, card_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            rows = session.query(SeedTable).all()
            for r in rows:
                seed = json.loads(r.data)
                if seed.get("createdFromCardId") == card_id:
                    return seed
            return None
        finally:
            session.close()

    def save(self, seed: dict[str, Any]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = SeedTable(
                id=seed["id"],
                user_id=seed.get("userId"),
                title=seed.get("title", ""),
                interest_id=seed.get("interestId"),
                core_claim=seed.get("coreClaim"),
                user_reaction=seed.get("userReaction"),
                status=seed.get("status"),
                maturity_score=str(seed.get("maturityScore", 0)),
                data=json.dumps(seed, ensure_ascii=False),
            )
            session.merge(row)
            session.commit()
            return seed
        finally:
            session.close()

    def delete(self, seed_id: str) -> None:
        session = self._SessionFactory()
        try:
            row = session.get(SeedTable, seed_id)
            if row:
                session.delete(row)
                session.commit()
        finally:
            session.close()
