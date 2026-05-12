"""PostgreSQL-backed session storage for writing-service."""

from __future__ import annotations

import json
from typing import Any

from .database import get_db_session_factory
from .models import WritingSessionTable


class PostgresSessionStorage:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    def get(self, session_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(WritingSessionTable, session_id)
            return json.loads(row.data) if row else None
        finally:
            session.close()

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        session = self._SessionFactory()
        try:
            row = WritingSessionTable(
                session_id=session_id,
                state=data.get("draftStatus", "unknown"),
                data=json.dumps(data, ensure_ascii=False),
            )
            session.merge(row)
            session.commit()
        finally:
            session.close()

    def values(self) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            rows = session.query(WritingSessionTable).all()
            return [json.loads(r.data) for r in rows]
        finally:
            session.close()
