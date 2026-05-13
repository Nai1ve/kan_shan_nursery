"""PostgreSQL-backed storage for feedback-service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .database import get_db_session_factory
from .models import FeedbackAnalysisTable, FeedbackArticleTable, FeedbackSnapshotTable


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
                        user_id=item.get("userId"),
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
                user_id=data.get("userId"),
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

    def save_snapshot(self, snapshot_id: str, article_id: str, metrics: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            now = datetime.now(timezone.utc)
            row = FeedbackSnapshotTable(
                id=snapshot_id,
                article_id=article_id,
                captured_at=now,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                comments_json=json.dumps(comments, ensure_ascii=False),
            )
            session.add(row)
            session.commit()
            return {
                "snapshotId": snapshot_id,
                "articleId": article_id,
                "capturedAt": now.isoformat(),
                "metrics": metrics,
                "comments": comments,
            }
        finally:
            session.close()

    def get_latest_snapshot(self, article_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = (
                session.query(FeedbackSnapshotTable)
                .filter_by(article_id=article_id)
                .order_by(FeedbackSnapshotTable.captured_at.desc())
                .first()
            )
            if not row:
                return None
            return {
                "snapshotId": row.id,
                "articleId": row.article_id,
                "capturedAt": row.captured_at.isoformat() if row.captured_at else None,
                "metrics": json.loads(row.metrics_json),
                "comments": json.loads(row.comments_json),
            }
        finally:
            session.close()

    def save_analysis(self, analysis_id: str, article_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            now = datetime.now(timezone.utc)
            # Upsert: delete existing then insert new
            session.query(FeedbackAnalysisTable).filter_by(article_id=article_id).delete()
            row = FeedbackAnalysisTable(
                id=analysis_id,
                article_id=article_id,
                generated_at=now,
                data=json.dumps(analysis, ensure_ascii=False),
            )
            session.add(row)
            session.commit()
            analysis["generatedAt"] = now.isoformat()
            return analysis
        finally:
            session.close()

    def get_analysis(self, article_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.query(FeedbackAnalysisTable).filter_by(article_id=article_id).first()
            if not row:
                return None
            return json.loads(row.data)
        finally:
            session.close()
