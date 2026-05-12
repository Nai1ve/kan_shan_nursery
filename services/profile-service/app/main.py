from __future__ import annotations


import sys
from pathlib import Path

_SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from kanshan_shared import configure_logging, get_logger, load_config
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from app.auth import AuthError, AuthRepository, AuthService
from app.memory.service import MemoryNotFound, MemoryService
from app.profile.repository import ProfileRepository
from app.profile.service import ProfileService


app = FastAPI(title="Kanshan Profile Service", version="0.1.0")
_config = load_config()
configure_logging("profile-service", _config.logging)
logger = get_logger("kanshan.profile_service.main")

# Select storage backend based on config
if _config.storage_backend == "postgres":
    from app.database import init_db
    init_db()
    from app.auth.pg_repository import PostgresAuthRepository
    from app.profile.pg_repository import PostgresProfileRepository
    repository = PostgresProfileRepository()
    auth_repository = PostgresAuthRepository()
    logger.info("storage_backend_selected", extra={"backend": "postgres"})
else:
    repository = ProfileRepository()
    auth_repository = AuthRepository()
    logger.info("storage_backend_selected", extra={"backend": "memory"})

profile_service = ProfileService(repository)
memory_service = MemoryService(repository)
auth_service = AuthService(auth_repository)


def handle_error(error: Exception) -> None:
    if isinstance(error, MemoryNotFound):
        raise HTTPException(status_code=404, detail={"code": "MEMORY_NOT_FOUND", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    if isinstance(error, AuthError):
        raise HTTPException(status_code=401, detail={"code": "AUTH_ERROR", "message": str(error)})
    raise error


@app.post("/auth/register")
def register(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = auth_service.register(
            nickname=payload.get("nickname", ""),
            password=payload.get("password", ""),
            email=payload.get("email"),
            username=payload.get("username"),
        )
        logger.info("auth_register", extra={"userId": result.get("user", {}).get("userId", "")})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/auth/login")
def login(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = auth_service.login(
            identifier=payload.get("identifier", ""),
            password=payload.get("password", ""),
        )
        logger.info("auth_login", extra={"userId": result.get("user", {}).get("userId", "")})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/auth/logout")
def logout(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("sessionId")
    logger.info("auth_logout", extra={"sessionId": session_id})
    return auth_service.logout(session_id)


@app.get("/auth/me")
def get_me(session_id: str | None = None) -> dict[str, Any]:
    result = auth_service.me(session_id)
    logger.info("auth_me", extra={"authenticated": result.get("authenticated", False)})
    return result


@app.get("/auth/zhihu/authorize")
def get_zhihu_authorize() -> dict[str, Any]:
    return auth_service.get_zhihu_authorize_url()


@app.post("/auth/zhihu/binding")
def create_zhihu_binding(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return auth_service.create_zhihu_binding(
            user_id=payload.get("userId", ""),
            zhihu_uid=payload.get("zhihuUid", ""),
            access_token=payload.get("accessToken", ""),
            expires_in=payload.get("expiresIn", 0),
        )
    except Exception as error:
        handle_error(error)
        raise


@app.get("/auth/zhihu/binding")
def get_zhihu_binding(user_id: str) -> dict[str, Any]:
    return auth_service.get_zhihu_binding(user_id)


@app.delete("/auth/zhihu/binding")
def delete_zhihu_binding(user_id: str) -> dict[str, Any]:
    return auth_service.delete_zhihu_binding(user_id)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "profile-service"}


@app.get("/profiles/me")
def get_profile() -> dict[str, Any]:
    return profile_service.get_profile()


@app.put("/profiles/me")
def update_profile(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = profile_service.update_profile(payload)
        logger.info("profile_update")
        return result
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
        result = memory_service.create_update_request(payload)
        logger.info("memory_update_request", extra={"action": "create", "requestId": result.get("id", "")})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/apply")
def apply_memory_update_request(request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = memory_service.apply_update_request(request_id, payload)
        logger.info("memory_update_request", extra={"action": "apply", "requestId": request_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/reject")
def reject_memory_update_request(request_id: str) -> dict[str, Any]:
    try:
        result = memory_service.reject_update_request(request_id)
        logger.info("memory_update_request", extra={"action": "reject", "requestId": request_id})
        return result
    except Exception as error:
        handle_error(error)
        raise
