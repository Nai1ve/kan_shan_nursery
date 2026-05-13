"""PostgreSQL-backed storage for sprout-service."""

from __future__ import annotations

import json
from typing import Any

from .database import get_db_session_factory
from .models import SproutOpportunityTable, SproutRunTable


class PostgresSproutStorage:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    # Opportunities
    def get_opportunity(self, opp_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(SproutOpportunityTable, opp_id)
            return json.loads(row.data) if row else None
        finally:
            session.close()

    def save_opportunity(self, opp_id: str, data: dict[str, Any]) -> None:
        session = self._SessionFactory()
        try:
            row = SproutOpportunityTable(
                id=opp_id,
                seed_id=data.get("seedId"),
                interest_id=data.get("interestId"),
                run_id=data.get("runId"),
                trigger_type=data.get("triggerType"),
                status=data.get("status"),
                score=str(data.get("score", 0)),
                data=json.dumps(data, ensure_ascii=False),
            )
            session.merge(row)
            session.commit()
        finally:
            session.close()

    def list_opportunities(self) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            rows = session.query(SproutOpportunityTable).all()
            return [json.loads(r.data) for r in rows]
        finally:
            session.close()

    def load_initial_opportunities(self, items: list[dict[str, Any]]) -> None:
        session = self._SessionFactory()
        try:
            existing = session.query(SproutOpportunityTable).count()
            if existing == 0:
                for item in items:
                    session.add(SproutOpportunityTable(
                        id=item["id"],
                        seed_id=item.get("seedId"),
                        interest_id=item.get("interestId"),
                        status=item.get("status"),
                        score=str(item.get("score", 0)),
                        data=json.dumps(item, ensure_ascii=False),
                    ))
                session.commit()
        finally:
            session.close()

    # Runs
    def get_run(self, run_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(SproutRunTable, run_id)
            return json.loads(row.data) if row else None
        finally:
            session.close()

    def save_run(self, run_id: str, data: dict[str, Any]) -> None:
        session = self._SessionFactory()
        try:
            row = SproutRunTable(
                id=run_id,
                user_id=data.get("userId"),
                interest_id=data.get("interestId"),
                status=data.get("status"),
                data=json.dumps(data, ensure_ascii=False),
            )
            session.merge(row)
            session.commit()
        finally:
            session.close()

    # Dismissed pairs
    def get_dismissed_pairs(self, user_id: str, days: int = 7) -> set[tuple[str, str]]:
        """Scan dismissed opportunities and return (seedId, triggerCardId) pairs."""
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        session = self._SessionFactory()
        try:
            rows = (
                session.query(SproutOpportunityTable)
                .filter(SproutOpportunityTable.status == "dismissed")
                .all()
            )
            pairs: set[tuple[str, str]] = set()
            for row in rows:
                opp = json.loads(row.data)
                if opp.get("userId") and opp.get("userId") != user_id:
                    continue
                dismissed_at = opp.get("dismissedAt")
                if dismissed_at:
                    try:
                        dt = datetime.fromisoformat(dismissed_at.replace("Z", "+00:00"))
                        if dt < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass
                seed_id = opp.get("seedId", "")
                trigger_ids = opp.get("triggerCardIds") or []
                for card_id in trigger_ids:
                    pairs.add((seed_id, card_id))
                if not trigger_ids:
                    pairs.add((seed_id, ""))
            return pairs
        finally:
            session.close()

    # Cache
    def get_cache(self, key: str) -> str | None:
        session = self._SessionFactory()
        try:
            row = session.get(SproutRunTable, f"cache_{key}")
            return json.loads(row.data).get("run_id") if row else None
        finally:
            session.close()

    def set_cache(self, key: str, run_id: str) -> None:
        session = self._SessionFactory()
        try:
            row = SproutRunTable(
                id=f"cache_{key}",
                data=json.dumps({"run_id": run_id}),
            )
            session.merge(row)
            session.commit()
        finally:
            session.close()
