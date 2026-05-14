from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

# In Docker, shared-python is installed via pip, so no sys.path manipulation needed.
# For local development, try to find it relative to the project root.
try:
    _SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
    if _SHARED_ROOT.exists() and str(_SHARED_ROOT) not in sys.path:
        sys.path.insert(0, str(_SHARED_ROOT))
except (IndexError, OSError):
    pass

from kanshan_shared import configure_logging, get_logger, load_config
from kanshan_shared.categories import INTEREST_CATEGORIES, SPECIAL_CATEGORIES

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .errors import GatewayError
from .service import GatewayService


_config = load_config()
configure_logging("api-gateway", _config.logging)
logger = get_logger("kanshan.gateway.main")

app = FastAPI(title="Kanshan API Gateway", version="0.1.0")

# CORS: 从配置文件读取白名单
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
gateway = GatewayService()


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"req-{uuid4().hex[:12]}"


def json_response(request_id_value: str, body: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body, headers={"X-Request-Id": request_id_value})


def gateway_error_response(error: GatewayError, request_id_value: str) -> JSONResponse:
    return json_response(
        request_id_value,
        {
            "request_id": request_id_value,
            "error": {
                "code": error.code,
                "message": error.message,
                "detail": error.detail,
            },
        },
        error.status_code,
    )


def run_proxy(
    request: Request,
    service_name: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id_value = request_id(request)
    session_id = request.headers.get("x-session-id")
    logger.info(
        "gateway_proxy",
        extra={
            "requestId": request_id_value,
            "service": service_name,
            "method": method,
            "path": path,
        },
    )
    try:
        return json_response(
            request_id_value,
            gateway.proxy(request_id_value, service_name, method, path, params, payload, session_id),
        )
    except GatewayError as error:
        logger.warning(
            "gateway_proxy_error",
            extra={
                "requestId": request_id_value,
                "service": service_name,
                "path": path,
                "errorCode": error.code,
                "httpStatus": error.status_code,
            },
        )
        return gateway_error_response(error, request_id_value)


def _resolve_user_id(request: Request) -> str | None:
    """Resolve user_id from the request's x-session-id header via profile-service.

    Returns None if no session, invalid session, or profile-service unreachable.
    Used by write endpoints that need user attribution before forwarding.
    """
    session_id = request.headers.get("x-session-id")
    if not session_id:
        return None
    try:
        request_id_value = request_id(request)
        envelope = gateway.proxy(
            request_id_value,
            "profile",
            "GET",
            "/auth/me",
            params={"session_id": session_id},
        )
        inner = envelope.get("data") or envelope
        user = inner.get("user") if isinstance(inner, dict) else None
        if not user:
            return None
        return user.get("userId") or user.get("user_id")
    except Exception:  # noqa: BLE001 — best-effort attribution
        return None


def _inject_user_id(request: Request, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve user_id once and inject into the outgoing payload as ``userId``."""
    user_id = _resolve_user_id(request)
    next_payload = dict(payload or {})
    if user_id and "userId" not in next_payload:
        next_payload["userId"] = user_id
    return next_payload


async def _optional_json_payload(request: Request) -> dict[str, Any]:
    """Parse an optional JSON object body.

    The frontend can intentionally call some POST endpoints without a body.
    Some browsers/clients still send ``Content-Type: application/json`` for
    those requests, so an empty body must be treated as ``{}`` instead of
    bubbling up ``JSONDecodeError`` as a 500.
    """
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return {}
    body = await request.body()
    if not body or not body.strip():
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_JSON", "message": "Request body must be valid JSON."},
        ) from error
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_JSON", "message": "Request body must be a JSON object."},
        )
    return payload


def _extract_interest_ids(payload: Any) -> list[str]:
    if isinstance(payload, list):
        ids: list[str] = []
        for item in payload:
            if isinstance(item, dict) and item.get("interestId"):
                ids.append(item["interestId"])
            elif isinstance(item, str):
                ids.append(item)
        return ids
    if isinstance(payload, dict):
        if payload.get("interestId"):
            return [payload["interestId"]]
        for key in ("data", "items", "interestMemories", "interests"):
            if key in payload:
                nested = _extract_interest_ids(payload.get(key))
                if nested:
                    return nested
    return []


def _canonicalize_interest_ids(ids: list[str]) -> list[str]:
    allowed = {cat.id for cat in INTEREST_CATEGORIES}
    return [interest_id for interest_id in ids if interest_id in allowed]


def _resolve_user_interests(request: Request) -> str | None:
    """Return a comma-separated list of interest IDs for the current session, or None.

    Best-effort: returns None when no session, no profile, or the call fails so
    that content endpoints fall back to showing the full catalog.
    """
    user_id = _resolve_user_id(request)
    if not user_id:
        return None
    try:
        request_id_value = request_id(request)
        session_id = request.headers.get("x-session-id")

        interest_envelope = gateway.proxy(
            request_id_value,
            "profile",
            "GET",
            "/profiles/me/interests",
            session_id=session_id,
        )
        ids = _canonicalize_interest_ids(_extract_interest_ids(interest_envelope))

        if not ids:
            profile_envelope = gateway.proxy(
                request_id_value,
                "profile",
                "GET",
                "/profiles/me",
                session_id=session_id,
            )
            profile_ids = _canonicalize_interest_ids(_extract_interest_ids(profile_envelope))
            if profile_ids:
                ids = profile_ids

        merged = list(dict.fromkeys([*ids, *SPECIAL_CATEGORIES]))
        return ",".join(merged) if merged else None
    except Exception:  # noqa: BLE001
        fallback = [cat.id for cat in INTEREST_CATEGORIES]
        merged = list(dict.fromkeys([*fallback, *SPECIAL_CATEGORIES]))
        return ",".join(merged) if merged else None


@app.get("/health")
def health(request: Request) -> JSONResponse:
    request_id_value = request_id(request)
    return json_response(request_id_value, gateway.health(request_id_value))


@app.get("/api/v1/profile/me")
def get_profile(request: Request) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/profiles/me")


@app.post("/api/v1/auth/register")
def auth_register(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/auth/register", payload=payload)


@app.post("/api/v1/auth/login")
def auth_login(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/auth/login", payload=payload)


@app.post("/api/v1/auth/logout")
def auth_logout(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/auth/logout", payload=payload)


@app.get("/api/v1/auth/me")
def auth_me(request: Request) -> JSONResponse:
    session_id = request.headers.get("x-session-id")
    return run_proxy(request, "profile", "GET", "/auth/me", params={"session_id": session_id})


@app.get("/api/v1/auth/zhihu/authorize")
def auth_zhihu_authorize(request: Request) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/auth/zhihu/authorize")


@app.post("/api/v1/auth/zhihu/exchange-ticket")
def auth_zhihu_exchange_ticket(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/auth/zhihu/exchange-ticket", payload=payload)


@app.get("/api/v1/auth/zhihu/callback")
def auth_zhihu_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    session_id: str | None = None,
    state: str | None = None,
) -> JSONResponse:
    """Proxy OAuth callback to profile-service with session_id from header/query/state and keep ticket in response.data."""
    header_session_id = request.headers.get("x-session-id")
    resolved_session_id = header_session_id or session_id
    request_id_value = request_id(request)
    logger.info(
        "网关收到知乎回调",
        extra={
            "请求ID": request_id_value,
            "有授权码": bool(code),
            "有错误参数": bool(error),
            "有Header会话": bool(header_session_id),
            "有Query会话": bool(session_id),
            "有State": bool(state),
            "会话来源": "header" if header_session_id else ("query" if session_id else "none"),
        },
    )
    return run_proxy(
        request,
        "profile",
        "GET",
        "/auth/zhihu/callback",
        params={"code": code, "error": error, "session_id": resolved_session_id, "state": state},
    )


@app.get("/api/v1/auth/zhihu/binding")
def auth_zhihu_binding(request: Request, user_id: str | None = None) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/auth/zhihu/binding", params={"user_id": user_id})


@app.delete("/api/v1/auth/zhihu/binding")
def auth_zhihu_unbind(request: Request, user_id: str | None = None) -> JSONResponse:
    return run_proxy(request, "profile", "DELETE", "/auth/zhihu/binding", params={"user_id": user_id})


@app.get("/api/v1/llm/config/me")
def get_llm_config(request: Request) -> JSONResponse:
    user_id = _resolve_user_id(request)
    params = {"user_id": user_id} if user_id else None
    return run_proxy(request, "llm", "GET", "/llm/config/me", params=params)


@app.put("/api/v1/llm/config/me")
def update_llm_config(request: Request, payload: dict[str, Any]) -> JSONResponse:
    user_id = _resolve_user_id(request)
    params = {"user_id": user_id} if user_id else None
    return run_proxy(request, "profile", "PUT", "/profiles/me/llm-config", params=params, payload=payload)


@app.get("/api/v1/llm/quota/me")
def get_llm_quota(request: Request) -> JSONResponse:
    user_id = _resolve_user_id(request)
    params = {"user_id": user_id} if user_id else None
    return run_proxy(request, "llm", "GET", "/llm/quota/me", params=params)


@app.put("/api/v1/profile/me")
def update_profile(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "PUT", "/profiles/me", payload=payload)


@app.post("/api/v1/profile/onboarding")
def save_profile_onboarding(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/profiles/onboarding", payload=payload)


@app.get("/api/v1/profile/interests")
def list_profile_interests(request: Request) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/profiles/me/interests")


@app.put("/api/v1/profile/interests")
def update_profile_interests(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "PUT", "/profiles/me/interests", payload=payload)


@app.get("/api/v1/memory/injection/{interest_id}")
def get_memory_injection(request: Request, interest_id: str) -> JSONResponse:
    return run_proxy(request, "profile", "GET", f"/memory/injection/{interest_id}")


@app.get("/api/v1/memory/update-requests")
def list_memory_update_requests(request: Request, status: str | None = None) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/memory/update-requests", params={"status": status})


@app.post("/api/v1/memory/update-requests")
def create_memory_update_request(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/memory/update-requests", payload=payload)


@app.post("/api/v1/memory/update-requests/{request_id_value}/apply")
def apply_memory_update_request(request: Request, request_id_value: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "profile", "POST", f"/memory/update-requests/{request_id_value}/apply", payload=payload)


@app.post("/api/v1/memory/update-requests/{request_id_value}/reject")
def reject_memory_update_request(request: Request, request_id_value: str) -> JSONResponse:
    return run_proxy(request, "profile", "POST", f"/memory/update-requests/{request_id_value}/reject")


@app.post("/api/v1/profile/enrichment-jobs")
def create_enrichment_job(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/profiles/me/enrichment-jobs", payload=payload)


@app.get("/api/v1/profile/enrichment-jobs/latest")
def get_latest_enrichment_job(request: Request) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/profiles/me/enrichment-jobs/latest")


@app.get("/api/v1/categories")
def list_categories(request: Request) -> JSONResponse:
    """Return the canonical category list from shared definitions."""
    from kanshan_shared.categories import ALL_CATEGORIES
    request_id_value = request_id(request)
    cats = [
        {
            "id": cat.id,
            "name": cat.name,
            "kind": cat.kind,
            "description": cat.description,
        }
        for cat in ALL_CATEGORIES
    ]
    return json_response(request_id_value, {"request_id": request_id_value, "data": cats})


@app.get("/api/v1/content")
def content_bootstrap(request: Request) -> JSONResponse:
    user_id = _resolve_user_id(request)
    interest_ids = _resolve_user_interests(request)
    params: dict[str, Any] = {"interest_ids": interest_ids}
    if user_id:
        params["user_id"] = user_id
    return run_proxy(request, "content", "GET", "/content", params=params)


@app.get("/api/v1/content/cards")
def content_cards(
    request: Request,
    categoryId: str | None = None,
    category_id: str | None = None,
    limit: int = 2,
    excludeIds: str | None = None,
    exclude_ids: str | None = None,
) -> JSONResponse:
    user_id = _resolve_user_id(request)
    resolved_category_id = categoryId or category_id
    interest_ids = _resolve_user_interests(request) if not resolved_category_id else None
    params: dict[str, Any] = {
        "category_id": resolved_category_id,
        "interest_ids": interest_ids,
        "limit": limit,
        "exclude_ids": excludeIds or exclude_ids,
    }
    if user_id:
        params["user_id"] = user_id
    return run_proxy(
        request,
        "content",
        "GET",
        "/content/cards",
        params=params,
    )


@app.get("/api/v1/content/cards/{card_id}")
def content_card(request: Request, card_id: str) -> JSONResponse:
    return run_proxy(request, "content", "GET", f"/content/cards/{card_id}")


@app.get("/api/v1/content/cards/{card_id}/sources/{source_id}")
def content_card_source(request: Request, card_id: str, source_id: str) -> JSONResponse:
    return run_proxy(request, "content", "GET", f"/content/cards/{card_id}/sources/{source_id}")


@app.post("/api/v1/content/categories/{category_id}/refresh")
async def refresh_content_category(request: Request, category_id: str) -> JSONResponse:
    payload = await _optional_json_payload(request)
    user_id = _resolve_user_id(request)
    if user_id and "user_id" not in payload:
        payload["user_id"] = user_id
    return run_proxy(request, "content", "POST", f"/content/categories/{category_id}/refresh", payload=payload)


@app.post("/api/v1/content/cards/{card_id}/summarize")
async def summarize_content_card(request: Request, card_id: str) -> JSONResponse:
    payload = await _optional_json_payload(request)
    user_id = _resolve_user_id(request)
    if user_id and "user_id" not in payload:
        payload["user_id"] = user_id
    return run_proxy(request, "content", "POST", f"/content/cards/{card_id}/summarize", payload=payload)


@app.post("/api/v1/content/cards/{card_id}/enrich")
async def enrich_content_card(request: Request, card_id: str) -> JSONResponse:
    payload = await _optional_json_payload(request)
    user_id = _resolve_user_id(request)
    if user_id and "user_id" not in payload:
        payload["user_id"] = user_id
    return run_proxy(request, "content", "POST", f"/content/cards/{card_id}/enrich", payload=payload)


@app.get("/api/v1/seeds")
def list_seeds(request: Request) -> JSONResponse:
    user_id = _resolve_user_id(request)
    return run_proxy(request, "seed", "GET", "/seeds", params={"user_id": user_id})


@app.post("/api/v1/seeds")
def create_seed(request: Request, payload: dict[str, Any]) -> JSONResponse:
    payload = _inject_user_id(request, payload)
    return run_proxy(request, "seed", "POST", "/seeds", payload=payload)


@app.post("/api/v1/seeds/from-card")
def create_seed_from_card(request: Request, payload: dict[str, Any]) -> JSONResponse:
    payload = _inject_user_id(request, payload)
    return run_proxy(request, "seed", "POST", "/seeds/from-card", payload=payload)


@app.get("/api/v1/seeds/{seed_id}")
def get_seed(request: Request, seed_id: str) -> JSONResponse:
    return run_proxy(request, "seed", "GET", f"/seeds/{seed_id}")


@app.patch("/api/v1/seeds/{seed_id}")
def update_seed(request: Request, seed_id: str, payload: dict[str, Any]) -> JSONResponse:
    payload = _inject_user_id(request, payload)
    return run_proxy(request, "seed", "PATCH", f"/seeds/{seed_id}", payload=payload)


@app.post("/api/v1/seeds/{seed_id}/questions")
def add_seed_question(request: Request, seed_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", f"/seeds/{seed_id}/questions", payload=payload)


@app.patch("/api/v1/seeds/{seed_id}/questions/{question_id}")
def mark_seed_question(request: Request, seed_id: str, question_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "PATCH", f"/seeds/{seed_id}/questions/{question_id}", payload=payload)


@app.post("/api/v1/seeds/{seed_id}/materials")
def add_seed_material(request: Request, seed_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", f"/seeds/{seed_id}/materials", payload=payload)


@app.post("/api/v1/seeds/{seed_id}/materials/agent-supplement")
def agent_supplement_seed_material(request: Request, seed_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", f"/seeds/{seed_id}/materials/agent-supplement", payload=payload)


@app.patch("/api/v1/seeds/{seed_id}/materials/{material_id}")
def update_seed_material(request: Request, seed_id: str, material_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "PATCH", f"/seeds/{seed_id}/materials/{material_id}", payload=payload)


@app.delete("/api/v1/seeds/{seed_id}/materials/{material_id}")
def delete_seed_material(request: Request, seed_id: str, material_id: str) -> JSONResponse:
    return run_proxy(request, "seed", "DELETE", f"/seeds/{seed_id}/materials/{material_id}")


@app.post("/api/v1/seeds/{target_seed_id}/merge")
def merge_seed(request: Request, target_seed_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", f"/seeds/{target_seed_id}/merge", payload=payload)


@app.post("/api/v1/llm/tasks/{task_type}")
def run_llm_task(request: Request, task_type: str, payload: dict[str, Any]) -> JSONResponse:
    user_id = _resolve_user_id(request)
    params = {"user_id": user_id} if user_id else None
    return run_proxy(request, "llm", "POST", f"/llm/tasks/{task_type}", params=params, payload=payload)


@app.post("/api/v1/sprout/start")
def start_sprout(request: Request, payload: dict[str, Any] | None = None) -> JSONResponse:
    payload = _inject_user_id(request, payload)
    return run_proxy(request, "sprout", "POST", "/sprout/start", payload=payload)


@app.get("/api/v1/sprout/runs/{run_id}")
def get_sprout_run(request: Request, run_id: str) -> JSONResponse:
    return run_proxy(request, "sprout", "GET", f"/sprout/runs/{run_id}")


@app.get("/api/v1/sprout/opportunities")
def list_sprout_opportunities(request: Request, interest_id: str | None = None) -> JSONResponse:
    return run_proxy(request, "sprout", "GET", "/sprout/opportunities", params={"interest_id": interest_id})


@app.post("/api/v1/sprout/opportunities/{opportunity_id}/supplement")
def supplement_sprout_opportunity(request: Request, opportunity_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "sprout", "POST", f"/sprout/opportunities/{opportunity_id}/supplement", payload=payload)


@app.post("/api/v1/sprout/opportunities/{opportunity_id}/switch-angle")
def switch_sprout_angle(request: Request, opportunity_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "sprout", "POST", f"/sprout/opportunities/{opportunity_id}/switch-angle", payload=payload)


@app.post("/api/v1/sprout/opportunities/{opportunity_id}/dismiss")
def dismiss_sprout_opportunity(request: Request, opportunity_id: str) -> JSONResponse:
    return run_proxy(request, "sprout", "POST", f"/sprout/opportunities/{opportunity_id}/dismiss")


@app.post("/api/v1/sprout/opportunities/{opportunity_id}/start-writing")
def start_sprout_writing(request: Request, opportunity_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "sprout", "POST", f"/sprout/opportunities/{opportunity_id}/start-writing", payload=payload)


@app.post("/api/v1/writing/sessions")
def create_writing_session(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "writing", "POST", "/writing/sessions", payload=payload)


@app.get("/api/v1/writing/sessions/{session_id}")
def get_writing_session(request: Request, session_id: str) -> JSONResponse:
    return run_proxy(request, "writing", "GET", f"/writing/sessions/{session_id}")


@app.patch("/api/v1/writing/sessions/{session_id}")
def update_writing_session(request: Request, session_id: str, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "writing", "PATCH", f"/writing/sessions/{session_id}", payload=payload)


@app.post("/api/v1/writing/sessions/{session_id}/confirm-claim")
def confirm_writing_claim(request: Request, session_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/confirm-claim", payload=payload)


@app.post("/api/v1/writing/sessions/{session_id}/blueprint")
def writing_blueprint(request: Request, session_id: str) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/blueprint")


@app.post("/api/v1/writing/sessions/{session_id}/draft")
def writing_draft(request: Request, session_id: str) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/draft")


@app.post("/api/v1/writing/sessions/{session_id}/roundtable")
def writing_roundtable(request: Request, session_id: str) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/roundtable")


@app.post("/api/v1/writing/sessions/{session_id}/finalize")
def writing_finalize(request: Request, session_id: str) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/finalize")


@app.post("/api/v1/writing/sessions/{session_id}/publish/mock")
def writing_publish_mock(request: Request, session_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "writing", "POST", f"/writing/sessions/{session_id}/publish/mock", payload=payload)


@app.get("/api/v1/feedback/articles")
def list_feedback_articles(request: Request, interest_id: str | None = None) -> JSONResponse:
    return run_proxy(request, "feedback", "GET", "/feedback/articles", params={"interest_id": interest_id})


@app.get("/api/v1/feedback/articles/{article_id}")
def get_feedback_article(request: Request, article_id: str) -> JSONResponse:
    return run_proxy(request, "feedback", "GET", f"/feedback/articles/{article_id}")


@app.post("/api/v1/feedback/sync")
def sync_feedback(request: Request, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "feedback", "POST", "/feedback/sync", payload=payload)


@app.get("/api/v1/feedback/articles/{article_id}/comments-summary")
def feedback_comments_summary(request: Request, article_id: str) -> JSONResponse:
    return run_proxy(request, "feedback", "GET", f"/feedback/articles/{article_id}/comments-summary")


@app.post("/api/v1/feedback/articles/{article_id}/second-seed")
def feedback_second_seed(request: Request, article_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "feedback", "POST", f"/feedback/articles/{article_id}/second-seed", payload=payload)


@app.post("/api/v1/feedback/articles/{article_id}/memory-update-request")
def feedback_memory_update_request(request: Request, article_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "feedback", "POST", f"/feedback/articles/{article_id}/memory-update-request", payload=payload)


@app.post("/api/v1/feedback/articles/from-writing-session")
def create_feedback_from_session(request: Request, payload: dict[str, Any]) -> JSONResponse:
    payload = _inject_user_id(request, payload)
    return run_proxy(request, "feedback", "POST", "/feedback/articles/from-writing-session", payload=payload)


@app.post("/api/v1/feedback/articles/{article_id}/refresh")
def refresh_feedback(request: Request, article_id: str) -> JSONResponse:
    return run_proxy(request, "feedback", "POST", f"/feedback/articles/{article_id}/refresh")


@app.post("/api/v1/feedback/articles/{article_id}/analyze")
def analyze_feedback(request: Request, article_id: str) -> JSONResponse:
    return run_proxy(request, "feedback", "POST", f"/feedback/articles/{article_id}/analyze")
