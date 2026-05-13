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
    from fastapi import FastAPI, HTTPException, Query, Request
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from app.auth import AuthError, AuthRepository, AuthService
from app.enrichment.models import EnrichmentJob
from app.enrichment.repository import EnrichmentRepository
from app.enrichment.runner import EnrichmentRunner
from app.enrichment.service import EnrichmentService
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
    from app.enrichment.pg_repository import PostgresEnrichmentRepository
    from app.profile.pg_repository import PostgresProfileRepository
    repository = PostgresProfileRepository()
    auth_repository = PostgresAuthRepository()
    enrichment_repository = PostgresEnrichmentRepository()
    logger.info("storage_backend_selected", extra={"backend": "postgres"})
else:
    from app.enrichment.memory_repository import MemoryEnrichmentRepository
    repository = ProfileRepository()
    auth_repository = AuthRepository()
    enrichment_repository = MemoryEnrichmentRepository()
    logger.info("storage_backend_selected", extra={"backend": "memory"})

profile_service = ProfileService(repository)
memory_service = MemoryService(repository)
auth_service = AuthService(auth_repository, zhihu_adapter_url=_config.service_urls.zhihu)

# Initialize enrichment service
enrichment_service = EnrichmentService(
    repo=enrichment_repository,
    zhihu_adapter_url=_config.service_urls.zhihu,
    llm_service_url=_config.service_urls.llm,
    profile_service_url=f"http://127.0.0.1:{_config.port if hasattr(_config, 'port') else 8010}",
    memory_service=memory_service,
)
enrichment_runner = EnrichmentRunner(
    repo=enrichment_repository,
    enrichment_service=enrichment_service,
    profile_repo=repository,
    auth_repo=auth_repository,
)

# Start background scheduler
from app.scheduler import ProfileScheduler
_profile_scheduler = ProfileScheduler(
    repository=repository,
    llm_service_url=_config.service_urls.llm,
    enrichment_runner=enrichment_runner,
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
    logger.info("知乎授权入口")
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
def get_zhihu_binding(request: Request, user_id: str | None = None) -> dict[str, Any]:
    if not user_id:
        user_id = _resolve_user_id(request)
    if not user_id:
        raise HTTPException(status_code=400, detail={"code": "USER_ID_MISSING", "message": "user_id is required"})
    return auth_service.get_zhihu_binding(user_id)


@app.delete("/auth/zhihu/binding")
def delete_zhihu_binding(request: Request, user_id: str | None = None) -> dict[str, Any]:
    if not user_id:
        user_id = _resolve_user_id(request)
    if not user_id:
        raise HTTPException(status_code=400, detail={"code": "USER_ID_MISSING", "message": "user_id is required"})
    return auth_service.delete_zhihu_binding(user_id)


@app.get("/internal/auth/zhihu-token")
def get_zhihu_token_internal(user_id: str) -> dict[str, Any]:
    """Internal endpoint: return raw access_token for inter-service calls."""
    return auth_service.get_zhihu_token(user_id)


@app.post("/auth/zhihu/exchange-ticket")
def exchange_zhihu_ticket(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        ticket = str(payload.get("ticket", "") or "")
        return auth_service.exchange_login_ticket(ticket)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/auth/zhihu/callback")
def zhihu_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    session_id: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """Handle OAuth callback from zhihu-adapter and issue short-lived login ticket."""
    request_id_value = request.headers.get("x-request-id") or ""

    logger.info(
        "知乎回调已收到",
        extra={
            "请求ID": request_id_value,
            "有授权码": bool(code),
            "有错误参数": bool(error),
            "有query_session": bool(session_id),
            "有header_session": bool(request.headers.get("x-session-id")),
            "有state": bool(state),
        },
    )

    if error:
        logger.warning("知乎回调被拒绝", extra={"请求ID": request_id_value, "错误": error})
        raise HTTPException(status_code=400, detail={"code": "OAUTH_DENIED", "message": error})
    if not code:
        logger.warning("知乎回调缺少授权码", extra={"请求ID": request_id_value})
        raise HTTPException(status_code=400, detail={"code": "OAUTH_CODE_MISSING", "message": "code is required"})

    try:
        token_result = auth_service.exchange_zhihu_code(code)
        user_info = auth_service.get_zhihu_user_info(token_result.get("access_token", ""))

        zhihu_uid = str(user_info.get("uid", ""))
        if not zhihu_uid:
            logger.warning("知乎回调缺少知乎UID", extra={"请求ID": request_id_value})
            raise HTTPException(status_code=502, detail={"code": "ZHIHU_UID_MISSING", "message": "Zhihu user uid missing"})

        existing_user = auth_service._repo.get_user_by_zhihu_uid(zhihu_uid)
        local_user = auth_service.ensure_user_by_zhihu_profile(user_info)
        binding = auth_service.create_zhihu_binding(
            user_id=local_user.user_id,
            zhihu_uid=zhihu_uid,
            access_token=token_result.get("access_token", ""),
            expires_in=token_result.get("expires_in", 0),
        )
        setup_state_hint = "llm_pending" if not existing_user else None
        if setup_state_hint == "llm_pending":
            auth_service.set_user_setup_state(local_user.user_id, "llm_pending")
        ticket = auth_service.create_login_ticket_for_user(local_user.user_id, setup_state_hint=setup_state_hint)

        logger.info("知乎授权完成并签发ticket", extra={"请求ID": request_id_value, "用户ID": local_user.user_id})
        return {
            "binding": binding,
            "ticket": ticket.ticket,
            "ticketExpiresAt": ticket.expires_at,
            "user": local_user.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("知乎回调处理失败", extra={"请求ID": request_id_value, "错误类型": type(error).__name__})
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
        result = profile_service.save_onboarding(payload, user_id=user_id)
        auth_service.set_user_setup_state(user_id, "ready")
        return result
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
def get_llm_config(request: Request, user_id: str | None = None, include_secret: bool = False) -> dict[str, Any]:
    try:
        resolved_user_id = user_id or _resolve_user_id(request)
        return profile_service.get_llm_config(resolved_user_id, include_secret=include_secret)
    except Exception as error:
        handle_error(error)
        raise


@app.put("/profiles/me/llm-config")
def update_llm_config(request: Request, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    try:
        resolved_user_id = user_id or _resolve_user_id(request)
        result = profile_service.update_llm_config(payload, resolved_user_id)
        if resolved_user_id:
            auth_service.set_user_setup_state(resolved_user_id, "preferences_pending")
        logger.info("llm_config_update")
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/profiles/me/enrichment-jobs")
async def create_enrichment_job(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new enrichment job."""
    try:
        user_id = _resolve_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Session required"})

        trigger = payload.get("trigger", "oauth_bound")
        include_sources = payload.get("includeSources", ["zhihu_user", "followed", "followers", "moments"])

        job = await enrichment_service.create_job(
            user_id=user_id,
            trigger=trigger,
            include_sources=include_sources,
        )

        logger.info("enrichment_job_created", extra={"jobId": job.job_id, "userId": user_id})

        return {
            "jobId": job.job_id,
            "status": job.status,
            "temporaryProfileReady": True,
        }
    except Exception as error:
        handle_error(error)
        raise


@app.get("/profiles/me/enrichment-jobs/latest")
async def get_latest_enrichment_job(request: Request) -> dict[str, Any]:
    """Get the latest enrichment job for the current user."""
    try:
        user_id = _resolve_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Session required"})

        job = await enrichment_service.get_latest_job(user_id)

        if not job:
            return {
                "jobId": None,
                "status": "not_started",
                "temporaryProfile": None,
                "signalCounts": {},
                "memoryUpdateRequestIds": [],
                "errorMessage": None,
            }

        return {
            "jobId": job.job_id,
            "status": job.status,
            "temporaryProfile": job.temporary_profile,
            "signalCounts": job.signal_counts,
            "memoryUpdateRequestIds": job.memory_update_request_ids,
            "errorMessage": job.error_message,
        }
    except Exception as error:
        handle_error(error)
        raise
