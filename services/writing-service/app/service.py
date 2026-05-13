from __future__ import annotations

from typing import Any

from . import session_logic
from .session_logic import InvalidTransition, SessionNotFound, VALID_TONES, check_transition


class WritingService:
    def __init__(self, storage: Any = None, llm_client: Any = None, feedback_client: Any = None) -> None:
        self._storage = storage  # If None, use in-memory dict
        self._llm_client = llm_client
        self._feedback_client = feedback_client
        self._sessions: dict[str, dict[str, Any]] = {}

    def _store_get(self, session_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get(session_id)
        return self._sessions.get(session_id)

    def _store_save(self, session_id: str, data: dict[str, Any]) -> None:
        if self._storage:
            self._storage.save(session_id, data)
        self._sessions[session_id] = data

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Claim
    # ------------------------------------------------------------------

    def confirm_claim(self, session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "confirm_claim")
        payload = payload or {}
        next_session = {
            **session,
            "coreClaim": payload.get("coreClaim", session["coreClaim"]),
            "articleType": payload.get("articleType", session["articleType"]),
            "tone": payload.get("tone", session["tone"]),
            "confirmed": True,
        }
        self._store_save(session_id, next_session)
        return next_session

    # ------------------------------------------------------------------
    # Blueprint
    # ------------------------------------------------------------------

    def generate_blueprint(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "generate_blueprint")
        if not session.get("confirmed"):
            raise InvalidTransition("claim must be confirmed before generating blueprint")
        blueprint = session_logic._build_blueprint(
            session.get("coreClaim") or "未确认观点",
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "draftStatus": "blueprint_ready", "blueprint": blueprint}
        self._store_save(session_id, next_session)
        return {"session": next_session, "blueprint": blueprint}

    def patch_blueprint(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "patch_blueprint")
        blueprint = {**session.get("blueprint", {})}
        for key in ["centralClaim", "mainThread", "counterArguments", "responseStrategy", "personalExperienceNeeded", "riskNotes"]:
            if key in patch:
                blueprint[key] = patch[key]
        if "argumentSteps" in patch:
            blueprint["argumentSteps"] = patch["argumentSteps"]
        next_session = {**session, "blueprint": blueprint}
        self._store_save(session_id, next_session)
        return {"session": next_session, "blueprint": blueprint}

    def regenerate_blueprint(self, session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "regenerate_blueprint")
        payload = payload or {}
        if payload:
            session = {
                **session,
                "coreClaim": payload.get("coreClaim", session.get("coreClaim", "")),
                "regenerateInstruction": (
                    payload.get("instruction")
                    or payload.get("userInstruction")
                    or payload.get("regenerateInstruction")
                    or ""
                ),
            }
        blueprint = session_logic._build_blueprint(
            session.get("coreClaim") or "未确认观点",
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "blueprint": blueprint}
        self._store_save(session_id, next_session)
        return {"session": next_session, "blueprint": blueprint}

    def confirm_blueprint(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "confirm_blueprint")
        next_session = {**session, "draftStatus": "blueprint_confirmed"}
        self._store_save(session_id, next_session)
        return next_session

    # ------------------------------------------------------------------
    # Outline
    # ------------------------------------------------------------------

    def generate_outline(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "generate_outline")
        blueprint = session.get("blueprint", {})
        outline = session_logic._build_outline(
            blueprint=blueprint,
            materials=[],
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "draftStatus": "outline_ready", "outline": outline}
        self._store_save(session_id, next_session)
        return {"session": next_session, "outline": outline}

    def patch_outline(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "patch_outline")
        outline = session.get("outline", {"sections": []})
        if "sections" in patch:
            outline = {"sections": patch["sections"]}
        next_session = {**session, "outline": outline}
        self._store_save(session_id, next_session)
        return {"session": next_session, "outline": outline}

    def regenerate_outline_section(self, session_id: str, section_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "regenerate_outline_section")
        outline = session.get("outline", {"sections": []})
        blueprint = session.get("blueprint", {})
        new_outline = session_logic._build_outline(
            blueprint=blueprint,
            materials=[],
            llm_client=self._llm_client,
            session=session,
        )
        # Replace matching section by id, or replace last section if no match
        existing_sections = list(outline.get("sections", []))
        existing_ids = {s["id"]: i for i, s in enumerate(existing_sections)}
        replaced = False
        for new_sec in new_outline.get("sections", []):
            if section_id in existing_ids:
                existing_sections[existing_ids[section_id]] = new_sec
                replaced = True
                break
        if not replaced and new_outline.get("sections"):
            # If section_id not found, append the first new section
            existing_sections.append(new_outline["sections"][0])
        outline = {"sections": existing_sections}
        next_session = {**session, "outline": outline}
        self._store_save(session_id, next_session)
        return {"session": next_session, "outline": outline}

    def confirm_outline(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "confirm_outline")
        next_session = {**session, "draftStatus": "outline_confirmed"}
        self._store_save(session_id, next_session)
        return next_session

    # ------------------------------------------------------------------
    # Draft
    # ------------------------------------------------------------------

    def generate_draft(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "generate_draft")
        draft = session_logic._build_draft(
            session.get("coreClaim") or "未确认观点",
            session["tone"],
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "draftStatus": "draft_ready", "savedDraft": True, "draft": draft}
        self._store_save(session_id, next_session)
        return {"session": next_session, "draft": draft}

    # ------------------------------------------------------------------
    # Roundtable
    # ------------------------------------------------------------------

    def start_roundtable(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "start_roundtable")
        roundtable_state = session_logic._init_roundtable_state(
            session.get("coreClaim") or "未确认观点",
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "draftStatus": "reviewing", "roundtable": roundtable_state}
        self._store_save(session_id, next_session)
        return {"session": next_session, "roundtable": roundtable_state}

    def roundtable_author_message(self, session_id: str, content: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "roundtable_author_message")
        roundtable_state = session.get("roundtable", {"status": "not_started", "turns": [], "suggestions": []})
        roundtable_state = session_logic._build_roundtable_author_message(roundtable_state, content)
        next_session = {**session, "roundtable": roundtable_state}
        self._store_save(session_id, next_session)
        return {"session": next_session, "roundtable": roundtable_state}

    def continue_roundtable(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "continue_roundtable")
        roundtable_state = session.get("roundtable", {"status": "not_started", "turns": [], "suggestions": []})
        roundtable_state = session_logic._continue_roundtable(
            roundtable_state,
            session.get("coreClaim") or "未确认观点",
            llm_client=self._llm_client,
            session=session,
        )
        next_session = {**session, "roundtable": roundtable_state}
        self._store_save(session_id, next_session)
        return {"session": next_session, "roundtable": roundtable_state}

    def adopt_suggestion(self, session_id: str, suggestion_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "adopt_suggestion")
        roundtable_state = session.get("roundtable", {"status": "not_started", "turns": [], "suggestions": []})
        roundtable_state = session_logic._adopt_suggestion(roundtable_state, suggestion_id)
        next_session = {**session, "roundtable": roundtable_state}
        self._store_save(session_id, next_session)
        return {"session": next_session, "roundtable": roundtable_state}

    # ------------------------------------------------------------------
    # Finalize & Publish
    # ------------------------------------------------------------------

    def finalize(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "finalize")
        finalized = session_logic._build_finalized(session.get("coreClaim") or "未确认观点")
        next_session = {**session, "draftStatus": "finalized"}
        self._store_save(session_id, next_session)
        return {"session": next_session, "finalized": finalized}

    def publish_mock(self, session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        check_transition(session["draftStatus"], "publish_mock")
        article_id = session_logic._create_id("article")
        next_session = {
            **session,
            "draftStatus": "published",
            "publishedArticleId": article_id,
        }
        self._store_save(session_id, next_session)

        title = (payload or {}).get("title", f"定稿：{session.get('coreClaim') or '未确认观点'}")
        published_at = session_logic._now_iso()

        # Call feedback-service to create tracking record (non-blocking)
        if self._feedback_client:
            try:
                self._feedback_client.create_from_writing_session({
                    "writingSessionId": session_id,
                    "seedId": session["seedId"],
                    "interestId": session["interestId"],
                    "title": title,
                    "coreClaim": session.get("coreClaim", ""),
                    "articleType": session.get("articleType", "article"),
                    "publishMode": "mock",
                    "publishedAt": published_at,
                })
            except Exception:
                pass  # Don't block publish on feedback-service failure

        return {
            "session": next_session,
            "publishedArticle": {
                "articleId": article_id,
                "title": title,
                "interestId": session["interestId"],
                "linkedSeedId": session["seedId"],
                "publishedAt": published_at,
                "publishMode": "mock",
            },
            "feedbackHandoff": {
                "articleId": article_id,
                "linkedSeedId": session["seedId"],
                "interestId": session["interestId"],
            },
        }
