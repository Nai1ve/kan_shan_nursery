"""PostgreSQL-backed storage for feedback-service."""

from __future__ import annotations

import json
from typing import Any

from .database import get_db_session_factory
from .models import FeedbackArticleTable


class PostgresFeedbackStorage:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    def load_initial_articles(self, items: list[dict[str, Any]]) -> None:
        session = self._SessionFactory()
        try:
            existing = session.query(FeedbackArticleTable).count()
            if existing == 0:
                for item in items:
                    session.add(FeedbackArticleTable(
                        id=item["id"],
                        title=item.get("title"),
                        interest_id=item.get("interestId"),
                        status=item.get("status"),
                        data=json.dumps(item, ensure_ascii=False),
                    ))
                session.commit()
        finally:
            session.close()

    def get_article(self, article_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(FeedbackArticleTable, article_id)
            return json.loads(row.data) if row else None
        finally:
            session.close()

    def save_article(self, article_id: str, data: dict[str, Any]) -> None:
        session = self._SessionFactory()
        try:
            row = FeedbackArticleTable(
                id=article_id,
                title=data.get("title"),
                interest_id=data.get("interestId"),
                status=data.get("status"),
                data=json.dumps(data, ensure_ascii=False),
            )
            session.merge(row)
            session.commit()
        finally:
            session.close()

    def list_articles(self) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            rows = session.query(FeedbackArticleTable).all()
            return [json.loads(r.data) for r in rows]
        finally:
            session.close()
