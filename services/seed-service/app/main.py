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

from .service import SeedNotFound, SeedService


app = FastAPI(title="Kanshan Seed Service", version="0.1.0")
_config = load_config()
configure_logging("seed-service", _config.logging)
logger = get_logger("kanshan.seed_service.main")

service = SeedService()


def handle_error(error: Exception) -> None:
    if isinstance(error, SeedNotFound):
        raise HTTPException(
            status_code=404,
            detail={"code": "SEED_NOT_FOUND", "message": f"Seed not found: {error}"},
        )
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    if isinstance(error, KeyError):
        raise HTTPException(status_code=400, detail={"code": "MISSING_FIELD", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "seed-service"}


@app.get("/seeds")
def list_seeds() -> dict[str, Any]:
    return {"items": service.list_seeds()}


@app.post("/seeds")
def create_seed(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.create_manual_seed(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/seeds/from-card")
def create_seed_from_card(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.from_card(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/seeds/{seed_id}")
def get_seed(seed_id: str) -> dict[str, Any]:
    try:
        return service.get_seed(seed_id)
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/seeds/{seed_id}")
def update_seed(seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.update_seed(seed_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/seeds/{seed_id}/questions")
def add_question(seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.add_question(seed_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/seeds/{seed_id}/questions/{question_id}")
def mark_question(seed_id: str, question_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.mark_question(seed_id, question_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/seeds/{seed_id}/materials")
def add_material(seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.add_material(seed_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.patch("/seeds/{seed_id}/materials/{material_id}")
def update_material(seed_id: str, material_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.update_material(seed_id, material_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.delete("/seeds/{seed_id}/materials/{material_id}")
def delete_material(seed_id: str, material_id: str) -> dict[str, Any]:
    try:
        return service.delete_material(seed_id, material_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/seeds/{seed_id}/materials/agent-supplement")
def agent_supplement(seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.agent_supplement(seed_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/seeds/{target_seed_id}/merge")
def merge_seed(target_seed_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.merge(target_seed_id, payload)
    except Exception as error:
        handle_error(error)
        raise
