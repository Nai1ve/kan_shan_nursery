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

from .llm_client import WritingLlmClient
from .session_logic import InvalidTransition, SessionNotFound
from .service import WritingService


app = FastAPI(title="Kanshan Writing Service", version="0.1.0")
_config = load_config()
configure_logging("writing-service", _config.logging)
logger = get_logger("kanshan.writing_service.main")

_llm_client = WritingLlmClient(base_url=_config.service_urls.llm)

if _config.storage_backend == "postgres":
    from .database import init_db
    init_db()
    from .pg_storage import PostgresSessionStorage
    service = WritingService(storage=PostgresSessionStorage(), llm_client=_llm_client)
    logger.info("storage_backend_selected", extra={"backend": "postgres"})
else:
    service = WritingService(llm_client=_llm_client)
    logger.info("storage_backend_selected", extra={"backend": "memory"})


def handle_error(error: Exception) -> None:
    if isinstance(error, SessionNotFound):
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": str(error)})
    if isinstance(error, InvalidTransition):
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "writing-service"}


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


@app.post("/writing/sessions/{session_id}/confirm-claim")
def confirm_claim(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.confirm_claim(session_id, payload)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "confirm_claim"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/blueprint")
def generate_blueprint(session_id: str) -> dict[str, Any]:
    try:
        result = service.generate_blueprint(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "blueprint"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/draft")
def generate_draft(session_id: str) -> dict[str, Any]:
    try:
        result = service.generate_draft(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "draft"})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/writing/sessions/{session_id}/roundtable")
def roundtable(session_id: str) -> dict[str, Any]:
    try:
        result = service.roundtable(session_id)
        logger.info("writing_state_transition", extra={"sessionId": session_id, "action": "roundtable"})
        return result
    except Exception as error:
        handle_error(error)
        raise


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
