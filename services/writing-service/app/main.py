from __future__ import annotations


import sys
from pathlib import Path

# In Docker, shared-python is installed via pip, so no sys.path manipulation needed.
try:
    _SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
except (IndexError, OSError):
    _SHARED_ROOT = None
if _SHARED_ROOT and str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from kanshan_shared import configure_logging, get_logger, load_config
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .feedback_client import FeedbackServiceClient
from .llm_client import WritingLlmClient
from .session_logic import InvalidTransition, SessionNotFound
from .service import WritingService


app = FastAPI(title="Kanshan Writing Service", version="0.2.0")
_config = load_config()
configure_logging("writing-service", _config.logging)
logger = get_logger("kanshan.writing_service.main")

_llm_client = WritingLlmClient(base_url=_config.service_urls.llm)
_feedback_client = FeedbackServiceClient(base_url=_config.service_urls.feedback)

if _config.storage_backend == "postgres":
    from .database import init_db
    init_db()
    from .pg_storage import PostgresSessionStorage
    service = WritingService(storage=PostgresSessionStorage(), llm_client=_llm_client, feedback_client=_feedback_client)
    logger.info("storage_backend_selected", extra={"backend": "postgres"})
else:
    service = WritingService(llm_client=_llm_client, feedback_client=_feedback_client)
    logger.info("storage_backend_selected", extra={"backend": "memory"})


def handle_error(error: Exception) -> None:
    if isinstance(error, SessionNotFound):
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": str(error)})
    if isinstance(error, InvalidTransition):
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "writing-service"}


# ------------------------------------------------------------------
# Session CRUD
# ------------------------------------------------------------------

@app.post("/writing/sessions")
def create_session(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = service.create_session(payload)
        logger.info("writing_session_create", extra={"sessionId": result.get("sessionId", ""), "seedId": payload.get("seedId", "")})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.get("/writing/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    try:
        return service.get_session(session_id)
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/writing/sessions/{session_id}")
def patch_session(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.patch_session(session_id, payload)
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Claim
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/confirm-claim")
def confirm_claim(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.confirm_claim(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "confirm_claim"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/claim/adjust")
def adjust_claim(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.adjust_claim(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "adjust_claim"})
        return result
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/blueprint")
def generate_blueprint(session_id: str) -> dict[str, Any]:
    try:
        result = service.generate_blueprint(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "blueprint"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/writing/sessions/{session_id}/blueprint")
def patch_blueprint(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = service.patch_blueprint(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "patch_blueprint"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/blueprint/regenerate")
def regenerate_blueprint(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.regenerate_blueprint(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "regenerate_blueprint"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/blueprint/confirm")
def confirm_blueprint(session_id: str) -> dict[str, Any]:
    try:
        result = service.confirm_blueprint(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "confirm_blueprint"})
        return result
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Outline
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/outline")
def generate_outline(session_id: str) -> dict[str, Any]:
    try:
        result = service.generate_outline(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "outline"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/writing/sessions/{session_id}/outline")
def patch_outline(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = service.patch_outline(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "patch_outline"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/outline/sections/{section_id}/regenerate")
def regenerate_outline_section(session_id: str, section_id: str) -> dict[str, Any]:
    try:
        result = service.regenerate_outline_section(session_id, section_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "regenerate_outline_section"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/outline/confirm")
def confirm_outline(session_id: str) -> dict[str, Any]:
    try:
        result = service.confirm_outline(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "confirm_outline"})
        return result
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Draft
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/draft")
def generate_draft(session_id: str) -> dict[str, Any]:
    try:
        result = service.generate_draft(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "draft"})
        return result
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Roundtable
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/roundtable/start")
def start_roundtable(session_id: str) -> dict[str, Any]:
    try:
        result = service.start_roundtable(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "start_roundtable"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/roundtable/messages")
def roundtable_message(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        content = payload.get("content", "")
        if not content:
            raise ValueError("content is required")
        result = service.roundtable_author_message(session_id, content)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "roundtable_author_message"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/roundtable/continue")
def continue_roundtable(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.continue_roundtable(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "continue_roundtable"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/roundtable/suggestions/{suggestion_id}/adopt")
def adopt_suggestion(session_id: str, suggestion_id: str) -> dict[str, Any]:
    try:
        result = service.adopt_suggestion(session_id, suggestion_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "adopt_suggestion"})
        return result
    except Exception as error:
        handle_error(error)
        raise


# ------------------------------------------------------------------
# Finalize & Publish
# ------------------------------------------------------------------

@app.post("/writing/sessions/{session_id}/finalize")
def finalize(session_id: str) -> dict[str, Any]:
    try:
        result = service.finalize(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "finalize"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/publish/mock")
def publish_mock(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.publish_mock(session_id, payload)
        logger.info("writing_publish", extra={"sessionId": session_id, "mode": "mock"})
        return result
    except Exception as error:
        handle_error(error)
        raise
