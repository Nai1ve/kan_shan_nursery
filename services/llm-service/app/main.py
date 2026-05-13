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

from dataclasses import asdict
from typing import Any

from kanshan_shared import configure_logging, get_logger, load_config

try:
    from fastapi import FastAPI, HTTPException, Request
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .prompts import TASKS
from .service import LlmService, QuotaExceeded


app = FastAPI(title="Kanshan LLM Service", version="0.1.0")
_config = load_config()
configure_logging("llm-service", _config.logging)
logger = get_logger("kanshan.llm_service.main")

_quota_limits = asdict(_config.llm.quota)
# Convert snake_case config keys to the task-type format used by TASKS (kebab-case)
_task_quota_map: dict[str, int] = {}
for key, limit in _quota_limits.items():
    task_key = key.replace("_", "-")
    _task_quota_map[task_key] = limit

service = LlmService(quota_limits=_task_quota_map)


def _extract_user_id(request: Request) -> str:
    """Extract user_id from query param or header, default to 'default'."""
    return request.query_params.get("user_id") or request.headers.get("x-user-id") or "default"


def handle_error(error: Exception) -> None:
    if isinstance(error, QuotaExceeded):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": f"每日额度已用完：{error.task_type} ({error.used}/{error.limit})",
                "taskType": error.task_type,
                "used": error.used,
                "limit": error.limit,
            },
        )
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-service"}


@app.get("/llm/config/me")
def get_llm_config(request: Request) -> dict[str, Any]:
    user_id = _extract_user_id(request)
    return service.get_config_status(user_id)


@app.get("/llm/quota/me")
def get_llm_quota(request: Request) -> dict[str, Any]:
    user_id = _extract_user_id(request)
    return {
        "platform": service.get_quota(user_id),
    }


@app.post("/llm/tasks/{task_type}")
def run_task(request: Request, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_type not in TASKS:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": task_type})
    user_id = _extract_user_id(request)
    try:
        logger.info("llm_task_started", extra={"taskType": task_type, "userId": user_id})
        result = service.run_task(payload, task_type, user_id=user_id)
        logger.info("llm_task_completed", extra={"taskType": task_type, "cacheHit": result.get("cache", {}).get("hit", False)})
        return result
    except Exception as error:
        handle_error(error)
        raise
