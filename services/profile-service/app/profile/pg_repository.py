"""PostgreSQL-backed profile repository."""

from __future__ import annotations

import json
from typing import Any

from ..database import get_db_session_factory
from ..models import MemoryUpdateRequestTable, ProfileDataTable, ProfileVersionTable
from .defaults import clone, create_id, now_iso


class PostgresProfileRepository:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    def _ensure_default_profile(self, session) -> ProfileDataTable:
        row = session.get(ProfileDataTable, "default")
        if not row:
            from .defaults import default_profile
            row = ProfileDataTable(id="default", data=json.dumps(default_profile(), ensure_ascii=False))
            session.add(row)
            session.commit()
            session.refresh(row)
        return row

    def get_profile(self) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = self._ensure_default_profile(session)
            return json.loads(row.data)
        finally:
            session.close()

    def save_profile(self, profile: dict[str, Any], reason: str) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = self._ensure_default_profile(session)
            # Save version snapshot
            old_data = row.data
            version = ProfileVersionTable(
                id=create_id("ver"),
                target="profile",
                snapshot=old_data,
                reason=reason,
                created_at=now_iso(),
            )
            session.add(version)
            # Update profile
            row.data = json.dumps(profile, ensure_ascii=False)
            session.commit()
            return clone(profile)
        finally:
            session.close()

    def list_versions(self) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            rows = session.query(ProfileVersionTable).order_by(ProfileVersionTable.created_at.desc()).all()
            return [
                {"target": r.target, "snapshot": json.loads(r.snapshot), "reason": r.reason, "createdAt": r.created_at}
                for r in rows
            ]
        finally:
            session.close()

    def list_update_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            q = session.query(MemoryUpdateRequestTable)
            if status:
                q = q.filter_by(status=status)
            rows = q.all()
            return [self._row_to_request(r) for r in rows]
        finally:
            session.close()

    def get_update_request(self, request_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(MemoryUpdateRequestTable, request_id)
            return self._row_to_request(row) if row else None
        finally:
            session.close()

    def save_update_request(self, request: dict[str, Any]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = MemoryUpdateRequestTable(
                id=request["id"],
                interest_id=request["interestId"],
                target_field=request["targetField"],
                suggested_value=request["suggestedValue"],
                reason=request["reason"],
                status=request.get("status", "pending"),
                created_at=request.get("createdAt", now_iso()),
            )
            session.merge(row)
            session.commit()
            return clone(request)
        finally:
            session.close()

    @staticmethod
    def _row_to_request(row: MemoryUpdateRequestTable) -> dict[str, Any]:
        return {
            "id": row.id,
            "interestId": row.interest_id,
            "targetField": row.target_field,
            "suggestedValue": row.suggested_value,
            "reason": row.reason,
            "status": row.status,
            "createdAt": row.created_at,
        }
