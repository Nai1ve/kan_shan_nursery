"""PostgreSQL-backed profile repository."""

from __future__ import annotations

import json
from typing import Any

from ..database import get_db_session_factory
from ..models import LLMConfigTable, MemoryUpdateRequestTable, ProfileDataTable, ProfileVersionTable, WritingStyleTable
from .defaults import clone, create_id, default_profile, now_iso


class PostgresProfileRepository:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    def _ensure_profile(self, session, user_id: str) -> ProfileDataTable:
        row = session.get(ProfileDataTable, user_id)
        if not row:
            row = ProfileDataTable(id=user_id, data=json.dumps(default_profile(), ensure_ascii=False))
            session.add(row)
            session.commit()
            session.refresh(row)
        return row

    def get_profile(self, user_id: str | None = None) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            if user_id:
                row = self._ensure_profile(session, user_id)
                return json.loads(row.data)
            # Fallback: return first profile or default
            rows = session.query(ProfileDataTable).all()
            if rows:
                return json.loads(rows[0].data)
            return default_profile()
        finally:
            session.close()

    def save_profile(self, profile: dict[str, Any], reason: str, user_id: str | None = None) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            target_user_id = user_id or profile.get("userId", "default")
            row = self._ensure_profile(session, target_user_id)
            # Save version snapshot
            old_data = row.data
            version = ProfileVersionTable(
                id=create_id("ver"),
                target=target_user_id,
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

    def list_update_requests(self, status: str | None = None, user_id: str | None = None) -> list[dict[str, Any]]:
        session = self._SessionFactory()
        try:
            q = session.query(MemoryUpdateRequestTable)
            if status:
                q = q.filter_by(status=status)
            rows = q.all()
            return [self._row_to_request(r) for r in rows]
        finally:
            session.close()

    def get_update_request(self, request_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(MemoryUpdateRequestTable, request_id)
            return self._row_to_request(row) if row else None
        finally:
            session.close()

    def save_update_request(self, request: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
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

    def get_writing_style(self, user_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(WritingStyleTable, user_id)
            if not row:
                return None
            return {
                "logicDepth": row.logic_depth,
                "stanceSharpness": row.stance_sharpness,
                "personalExperience": row.personal_experience,
                "expressionSharpness": row.expression_sharpness,
                "uncertaintyTolerance": row.uncertainty_tolerance,
                "preferredFormat": row.preferred_format,
                "evidenceVsJudgment": row.evidence_vs_judgment,
                "openingStyle": row.opening_style,
                "titleStyle": row.title_style,
                "emotionalTemperature": row.emotional_temperature,
                "aiAssistanceBoundary": row.ai_assistance_boundary,
            }
        finally:
            session.close()

    def save_writing_style(self, user_id: str, style: dict[str, Any]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = session.get(WritingStyleTable, user_id)
            if not row:
                row = WritingStyleTable(user_id=user_id)
                session.add(row)
            row.logic_depth = style.get("logicDepth", 3)
            row.stance_sharpness = style.get("stanceSharpness", 3)
            row.personal_experience = style.get("personalExperience", 3)
            row.expression_sharpness = style.get("expressionSharpness", 3)
            row.uncertainty_tolerance = style.get("uncertaintyTolerance", 3)
            row.preferred_format = style.get("preferredFormat", "long_article")
            row.evidence_vs_judgment = style.get("evidenceVsJudgment", "balanced")
            row.opening_style = style.get("openingStyle", "question")
            row.title_style = style.get("titleStyle", "controversy")
            row.emotional_temperature = style.get("emotionalTemperature", "rational")
            row.ai_assistance_boundary = style.get("aiAssistanceBoundary", "draft_only")
            session.commit()
            return clone(style)
        finally:
            session.close()

    def get_llm_config(self, user_id: str) -> dict[str, Any] | None:
        session = self._SessionFactory()
        try:
            row = session.get(LLMConfigTable, user_id)
            if not row:
                return None
            return {
                "provider": row.provider,
                "model": row.model,
                "baseUrl": row.base_url,
                "apiKey": row.api_key,
            }
        finally:
            session.close()

    def save_llm_config(self, user_id: str, config: dict[str, Any]) -> dict[str, Any]:
        session = self._SessionFactory()
        try:
            row = session.get(LLMConfigTable, user_id)
            if not row:
                row = LLMConfigTable(user_id=user_id)
                session.add(row)
            row.provider = config.get("provider", "openai_compat")
            row.model = config.get("model", "gpt-5.5")
            row.base_url = config.get("baseUrl")
            row.api_key = config.get("apiKey")
            session.commit()
            return clone(config)
        finally:
            session.close()
