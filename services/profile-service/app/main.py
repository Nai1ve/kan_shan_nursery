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

# Start background scheduler
from app.scheduler import ProfileScheduler
_profile_scheduler = ProfileScheduler(
    repository=repository,
    llm_service_url=_config.service_urls.llm,
)
_profile_scheduler.start()


def _resolve_user_id(request: Request) -> str | None:
    """Resolve user_id from x-session-id header via auth repository."""
    session_id = request.headers.get("x-session-id")
    if not session_id:
        return None
    try:
        session = auth_service._repo.get_session(session_id)
        if not session:
            return None
        return session.user_id
    except Exception:
        return None


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


@app.get("/auth/zhihu/callback")
def zhihu_callback(code: str | None = None, error: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    """Handle OAuth callback from zhihu-adapter."""
    if error:
        raise HTTPException(status_code=400, detail={"code": "OAUTH_DENIED", "message": error})
    if not code:
        raise HTTPException(status_code=400, detail={"code": "OAUTH_CODE_MISSING", "message": "code is required"})

    try:
        # 1. Get current user from session
        if not session_id:
            raise HTTPException(status_code=401, detail={"code": "SESSION_MISSING", "message": "session_id is required"})

        me_result = auth_service.me(session_id)
        if not me_result.get("authenticated"):
            raise HTTPException(status_code=401, detail={"code": "NOT_AUTHENTICATED", "message": "User not authenticated"})

        user_id = me_result["user"]["userId"]

        # 2. Exchange code for token via zhihu-adapter
        token_result = auth_service.exchange_zhihu_code(code)

        # 3. Get user info from Zhihu
        user_info = auth_service.get_zhihu_user_info(token_result.get("access_token", ""))

        # 4. Save binding to database
        result = auth_service.create_zhihu_binding(
            user_id=user_id,
            zhihu_uid=str(user_info.get("uid", "")),
            access_token=token_result.get("access_token", ""),
            expires_in=token_result.get("expires_in", 0),
        )

        logger.info("zhihu_oauth_completed", extra={"userId": user_id})
        return result
    except HTTPException:
        raise
    except Exception as error:
        handle_error(error)
        raise


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "profile-service"}


@app.get("/profiles/me")
def get_profile(request: Request) -> dict[str, Any]:
    user_id = _resolve_user_id(request)
    return profile_service.get_profile(user_id=user_id)


@app.put("/profiles/me")
def update_profile(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = profile_service.update_profile(payload)
        logger.info("profile_update")
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/profiles/onboarding")
def onboarding(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        if not user_id:
            raise ValueError("session required")
        return profile_service.save_onboarding(payload, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/profiles/me/interests")
def list_interests(request: Request) -> list[dict[str, Any]]:
    user_id = _resolve_user_id(request)
    return memory_service.list_interest_memories(user_id=user_id)


@app.put("/profiles/me/interests")
def update_profile_interests(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return profile_service.update_interests(payload, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.put("/profiles/me/interests/{interest_id}")
def update_profile_interest(request: Request, interest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return memory_service.update_interest_memory(interest_id, payload, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/me")
def get_memory(request: Request) -> dict[str, Any]:
    user_id = _resolve_user_id(request)
    return memory_service.get_full_memory(user_id=user_id)


@app.put("/memory/me/global")
def update_global_memory(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return memory_service.update_global_memory(payload, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/me/interests/{interest_id}")
def get_interest_memory(request: Request, interest_id: str) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return memory_service.get_interest_memory(interest_id, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.put("/memory/me/interests/{interest_id}")
def update_interest_memory(request: Request, interest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return memory_service.update_interest_memory(interest_id, payload, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/injection/{interest_id}")
def get_memory_injection(request: Request, interest_id: str) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        return memory_service.build_injection_summary(interest_id, user_id=user_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/memory/update-requests")
def list_memory_update_requests(request: Request, status: str | None = Query(default=None)) -> list[dict[str, Any]]:
    user_id = _resolve_user_id(request)
    return memory_service.list_update_requests(status, user_id=user_id)


@app.post("/memory/update-requests")
def create_memory_update_request(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        result = memory_service.create_update_request(payload, user_id=user_id)
        logger.info("memory_update_request", extra={"action": "create", "requestId": result.get("id", "")})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/apply")
def apply_memory_update_request(request: Request, request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        result = memory_service.apply_update_request(request_id, payload, user_id=user_id)
        logger.info("memory_update_request", extra={"action": "apply", "requestId": request_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/memory/update-requests/{request_id}/reject")
def reject_memory_update_request(request: Request, request_id: str) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        result = memory_service.reject_update_request(request_id, user_id=user_id)
        logger.info("memory_update_request", extra={"action": "reject", "requestId": request_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.put("/profiles/me/basic")
def update_basic_profile(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = _resolve_user_id(request)
        result = profile_service.update_basic_profile(payload, user_id=user_id)
        logger.info("profile_basic_update")
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.get("/profiles/me/writing-style")
def get_writing_style() -> dict[str, Any]:
    try:
        return profile_service.get_writing_style()
    except Exception as error:
        handle_error(error)
        raise


@app.put("/profiles/me/writing-style")
def update_writing_style(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = profile_service.update_writing_style(payload)
        logger.info("writing_style_update")
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.get("/profiles/me/llm-config")
def get_llm_config() -> dict[str, Any]:
    try:
        return profile_service.get_llm_config()
    except Exception as error:
        handle_error(error)
        raise


@app.put("/profiles/me/llm-config")
def update_llm_config(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = profile_service.update_llm_config(payload)
        logger.info("llm_config_update")
        return result
    except Exception as error:
        handle_error(error)
        raise
