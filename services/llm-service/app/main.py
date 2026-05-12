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

from .prompts import TASKS
from .service import LlmService


app = FastAPI(title="Kanshan LLM Service", version="0.1.0")
_config = load_config()
configure_logging("llm-service", _config.logging)
logger = get_logger("kanshan.llm_service.main")

service = LlmService()


def handle_error(error: Exception) -> None:
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-service"}


@app.get("/llm/config/me")
def get_llm_config(user_id: str | None = None) -> dict[str, Any]:
    return {
        "status": "platform_free",
        "activeProvider": "platform_free",
        "displayName": "平台免费额度",
        "quota": {
            "profileSignalSummarize": {"used": 1, "limit": 3},
            "profileMemorySynthesize": {"used": 1, "limit": 3},
            "profileRiskReview": {"used": 2, "limit": 5},
            "summarizeContent": {"used": 5, "limit": 30},
            "answerSeedQuestion": {"used": 3, "limit": 20},
            "supplementMaterial": {"used": 2, "limit": 20},
            "argumentBlueprint": {"used": 0, "limit": 10},
            "draft": {"used": 0, "limit": 5},
            "roundtableReview": {"used": 0, "limit": 5},
        },
    }


@app.get("/llm/quota/me")
def get_llm_quota(user_id: str | None = None) -> dict[str, Any]:
    return {
        "platform": {
            "profileSignalSummarize": {"used": 1, "limit": 3, "remaining": 2},
            "profileMemorySynthesize": {"used": 1, "limit": 3, "remaining": 2},
            "profileRiskReview": {"used": 2, "limit": 5, "remaining": 3},
            "summarizeContent": {"used": 5, "limit": 30, "remaining": 25},
            "answerSeedQuestion": {"used": 3, "limit": 20, "remaining": 17},
            "supplementMaterial": {"used": 2, "limit": 20, "remaining": 18},
            "argumentBlueprint": {"used": 0, "limit": 10, "remaining": 10},
            "draft": {"used": 0, "limit": 5, "remaining": 5},
            "roundtableReview": {"used": 0, "limit": 5, "remaining": 5},
        }
    }


@app.post("/llm/tasks/{task_type}")
def run_task(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_type not in TASKS:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": task_type})
    try:
        logger.info("llm_task_started", extra={"taskType": task_type})
        result = service.run_task(payload, task_type)
        logger.info("llm_task_completed", extra={"taskType": task_type, "cacheHit": result.get("cache", {}).get("hit", False)})
        return result
    except Exception as error:
        handle_error(error)
        raise
