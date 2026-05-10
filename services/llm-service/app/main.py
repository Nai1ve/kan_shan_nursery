from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .prompts import TASKS
from .service import LlmService


app = FastAPI(title="Kanshan LLM Service", version="0.1.0")
service = LlmService()


def handle_error(error: Exception) -> None:
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-service"}


@app.post("/llm/tasks/{task_type}")
def run_task(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task_type not in TASKS:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": task_type})
    try:
        return service.run_task(payload, task_type)
    except Exception as error:
        handle_error(error)
        raise
