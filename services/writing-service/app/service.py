from __future__ import annotations

from typing import Any

from . import session_logic
from .session_logic import InvalidTransition, SessionNotFound, VALID_TONES


class WritingService:
    def __init__(self, storage: Any = None) -> None:
        self._storage = storage  # If None, use in-memory dict
        self._sessions: dict[str, dict[str, Any]] = {}

    def _store_get(self, session_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get(session_id)
        return self._sessions.get(session_id)

    def _store_save(self, session_id: str, data: dict[str, Any]) -> None:
        if self._storage:
            self._storage.save(session_id, data)
        self._sessions[session_id] = data

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("seedId"):
            raise ValueError("seedId is required")
        if not payload.get("interestId"):
            raise ValueError("interestId is required")
        tone = payload.get("tone", "balanced")
        if tone not in VALID_TONES:
            raise ValueError(f"tone must be one of {sorted(VALID_TONES)}")
        memory = payload.get("memoryOverride") or session_logic._default_memory_for_interest(payload["interestId"])
        session = {
            "sessionId": session_logic._create_id("ws"),
            "seedId": payload["seedId"],
            "interestId": payload["interestId"],
            "articleType": payload.get("articleType", "工程复盘"),
            "coreClaim": payload.get("coreClaim", ""),
            "memoryOverride": memory,
            "tone": tone,
            "confirmed": False,
            "adoptedSuggestions": [],
            "draftStatus": "claim_confirming",
            "savedDraft": False,
        }
        self._store_save(session["sessionId"], session)
        return session

    def get_session(self, session_id: str) -> dict[str, Any]:
        session = self._store_get(session_id)
        if not session:
            raise SessionNotFound(session_id)
        return session

    def patch_session(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        session = self.get_session(session_id)
        merged = {**session}
        for key in ["articleType", "coreClaim", "tone", "memoryOverride", "adoptedSuggestions", "savedDraft"]:
            if key in patch:
                if key == "tone" and patch[key] not in VALID_TONES:
                    raise ValueError(f"tone must be one of {sorted(VALID_TONES)}")
                merged[key] = patch[key]
        self._store_save(session_id, merged)
        return merged

    def confirm_claim(self, session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["draftStatus"] not in {"claim_confirming"}:
            raise InvalidTransition(f"cannot confirm from status {session['draftStatus']}")
        payload = payload or {}
        next_session = {
            **session,
            "coreClaim": payload.get("coreClaim", session["coreClaim"]),
            "articleType": payload.get("articleType", session["articleType"]),
            "tone": payload.get("tone", session["tone"]),
            "confirmed": True,
            "draftStatus": "claim_confirming",
        }
        self._store_save(session_id, next_session)
        return next_session

    def generate_blueprint(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if not session["confirmed"]:
            raise InvalidTransition("claim must be confirmed before blueprint")
        blueprint = session_logic._build_blueprint(session.get("coreClaim") or "未确认观点")
        next_session = {**session, "draftStatus": "blueprint_ready"}
        self._store_save(session_id, next_session)
        return {"session": next_session, "blueprint": blueprint}

    def generate_draft(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["draftStatus"] not in {"blueprint_ready", "draft_ready", "reviewing"}:
            raise InvalidTransition(f"cannot draft from status {session['draftStatus']}")
        draft = session_logic._build_draft(session.get("coreClaim") or "未确认观点", session["tone"])
        next_session = {**session, "draftStatus": "draft_ready", "savedDraft": True}
        self._store_save(session_id, next_session)
        return {"session": next_session, "draft": draft}

    def roundtable(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["draftStatus"] not in {"draft_ready", "reviewing"}:
            raise InvalidTransition("draft must be ready before roundtable")
        review = session_logic._build_roundtable(session.get("coreClaim") or "未确认观点")
        next_session = {**session, "draftStatus": "reviewing"}
        self._store_save(session_id, next_session)
        return {"session": next_session, "review": review}

    def finalize(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["draftStatus"] not in {"reviewing", "draft_ready"}:
            raise InvalidTransition("session must finish review before finalizing")
        finalized = session_logic._build_finalized(session.get("coreClaim") or "未确认观点")
        next_session = {**session, "draftStatus": "finalized"}
        self._store_save(session_id, next_session)
        return {"session": next_session, "finalized": finalized}

    def publish_mock(self, session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["draftStatus"] not in {"finalized", "published"}:
            raise InvalidTransition("session must be finalized before publish")
        article_id = session_logic._create_id("article")
        next_session = {
            **session,
            "draftStatus": "published",
            "publishedArticleId": article_id,
        }
        self._store_save(session_id, next_session)
        return {
            "session": next_session,
            "publishedArticle": {
                "articleId": article_id,
                "title": (payload or {}).get("title", f"定稿：{session.get('coreClaim') or '未确认观点'}"),
                "interestId": session["interestId"],
                "linkedSeedId": session["seedId"],
                "publishedAt": session_logic._now_iso(),
                "publishMode": "mock",
            },
            "feedbackHandoff": {
                "articleId": article_id,
                "linkedSeedId": session["seedId"],
                "interestId": session["interestId"],
            },
        }
