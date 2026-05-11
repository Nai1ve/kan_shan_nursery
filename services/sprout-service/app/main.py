from __future__ import annotations


import sys
from pathlib import Path

_SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from kanshan_shared import configure_logging, get_logger, load_config
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .service import OpportunityNotFound, RunNotFound, SproutService


app = FastAPI(title="Kanshan Sprout Service", version="0.1.0")
_config = load_config()
configure_logging("sprout-service", _config.logging)
logger = get_logger("kanshan.sprout_service.main")

service = SproutService()


def handle_error(error: Exception) -> None:
    if isinstance(error, RunNotFound):
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": str(error)})
    if isinstance(error, OpportunityNotFound):
        raise HTTPException(status_code=404, detail={"code": "OPPORTUNITY_NOT_FOUND", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sprout-service"}


@app.post("/sprout/start")
def start_run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return service.start_run(payload)


@app.get("/sprout/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    try:
        return service.get_run(run_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/sprout/opportunities")
def list_opportunities(interest_id: str | None = None) -> dict[str, Any]:
    return service.list_opportunities(interest_id)


@app.post("/sprout/opportunities/{opportunity_id}/supplement")
def supplement_opportunity(opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.supplement(opportunity_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/sprout/opportunities/{opportunity_id}/switch-angle")
def switch_angle(opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.switch_angle(opportunity_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/sprout/opportunities/{opportunity_id}/dismiss")
def dismiss_opportunity(opportunity_id: str) -> dict[str, Any]:
    try:
        return service.dismiss(opportunity_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/sprout/opportunities/{opportunity_id}/start-writing")
def start_writing(opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.start_writing(opportunity_id, payload)
    except Exception as error:
        handle_error(error)
        raise
