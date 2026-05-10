from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from app.memory.service import MemoryNotFound, MemoryService
from app.profile.repository import ProfileRepository
from app.profile.service import ProfileService


app = FastAPI(title="Kanshan Profile Service", version="0.1.0")
repository = ProfileRepository()
profile_service = ProfileService(repository)
memory_service = MemoryService(repository)


def handle_error(error: Exception) -> None:
    if isinstance(error, MemoryNotFound):
        raise HTTPException(status_code=404, detail={"code": "MEMORY_NOT_FOUND", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "profile-service"}


@app.get("/profiles/me")
def get_profile() -> dict[str, Any]:
    return profile_service.get_profile()


@app.put("/profiles/me")
def update_profile(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return profile_service.update_profile(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/profiles/onboarding")
def onboarding(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return profile_service.save_onboarding(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/profiles/me/interests")
def list_interests() -> list[dict[str, Any]]:
    return memory_service.list_interest_memories()


@app.put("/profiles/me/interests/{interest_id}")
def update_profile_interest(interest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return memory_service.update_interest_memory(interest_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/me")
def get_memory() -> dict[str, Any]:
    return memory_service.get_full_memory()


@app.put("/memory/me/global")
def update_global_memory(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return memory_service.update_global_memory(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/me/interests/{interest_id}")
def get_interest_memory(interest_id: str) -> dict[str, Any]:
    try:
        return memory_service.get_interest_memory(interest_id)
    except Exception as error:
        handle_error(error)
        raise


@app.put("/memory/me/interests/{interest_id}")
def update_interest_memory(interest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return memory_service.update_interest_memory(interest_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/injection/{interest_id}")
def get_memory_injection(interest_id: str) -> dict[str, Any]:
    try:
        return memory_service.build_injection_summary(interest_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/update-requests")
def list_memory_update_requests(status: str | None = Query(default=None)) -> list[dict[str, Any]]:
    return memory_service.list_update_requests(status)


@app.post("/memory/update-requests")
def create_memory_update_request(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return memory_service.create_update_request(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/apply")
def apply_memory_update_request(request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return memory_service.apply_update_request(request_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/reject")
def reject_memory_update_request(request_id: str) -> dict[str, Any]:
    try:
        return memory_service.reject_update_request(request_id)
    except Exception as error:
        handle_error(error)
        raise
