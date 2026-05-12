from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

_SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from kanshan_shared import configure_logging, get_logger, load_config

try:
    from fastapi import FastAPI, Request
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
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://192.168.1.115:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
            gateway.proxy(request_id_value, service_name, method, path, params, payload),
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


@app.get("/api/v1/auth/zhihu/callback")
def auth_zhihu_callback(request: Request, code: str | None = None, error: str | None = None) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/auth/zhihu/callback", params={"code": code, "error": error})


@app.get("/api/v1/auth/zhihu/binding")
def auth_zhihu_binding(request: Request, user_id: str) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/auth/zhihu/binding", params={"user_id": user_id})


@app.delete("/api/v1/auth/zhihu/binding")
def auth_zhihu_unbind(request: Request, user_id: str) -> JSONResponse:
    return run_proxy(request, "profile", "DELETE", "/auth/zhihu/binding", params={"user_id": user_id})


@app.get("/api/v1/llm/config/me")
def get_llm_config(request: Request) -> JSONResponse:
    return run_proxy(request, "llm", "GET", "/llm/config/me")


@app.get("/api/v1/llm/quota/me")
def get_llm_quota(request: Request) -> JSONResponse:
    return run_proxy(request, "llm", "GET", "/llm/quota/me")


@app.put("/api/v1/profile/me")
def update_profile(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "PUT", "/profiles/me", payload=payload)


@app.post("/api/v1/profile/onboarding")
def save_profile_onboarding(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "profile", "POST", "/profiles/onboarding", payload=payload)


@app.get("/api/v1/profile/interests")
def list_profile_interests(request: Request) -> JSONResponse:
    return run_proxy(request, "profile", "GET", "/profiles/me/interests")


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


@app.get("/api/v1/content")
def content_bootstrap(request: Request) -> JSONResponse:
    return run_proxy(request, "content", "GET", "/content")


@app.get("/api/v1/content/cards")
def content_cards(request: Request, categoryId: str | None = None) -> JSONResponse:
    return run_proxy(request, "content", "GET", "/content/cards", params={"category_id": categoryId})


@app.get("/api/v1/content/cards/{card_id}")
def content_card(request: Request, card_id: str) -> JSONResponse:
    return run_proxy(request, "content", "GET", f"/content/cards/{card_id}")


@app.get("/api/v1/content/cards/{card_id}/sources/{source_id}")
def content_card_source(request: Request, card_id: str, source_id: str) -> JSONResponse:
    return run_proxy(request, "content", "GET", f"/content/cards/{card_id}/sources/{source_id}")


@app.post("/api/v1/content/categories/{category_id}/refresh")
def refresh_content_category(request: Request, category_id: str) -> JSONResponse:
    return run_proxy(request, "content", "POST", f"/content/categories/{category_id}/refresh")


@app.post("/api/v1/content/cards/{card_id}/summarize")
def summarize_content_card(request: Request, card_id: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    return run_proxy(request, "content", "POST", f"/content/cards/{card_id}/summarize", payload=payload)


@app.get("/api/v1/seeds")
def list_seeds(request: Request) -> JSONResponse:
    return run_proxy(request, "seed", "GET", "/seeds")


@app.post("/api/v1/seeds")
def create_seed(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", "/seeds", payload=payload)


@app.post("/api/v1/seeds/from-card")
def create_seed_from_card(request: Request, payload: dict[str, Any]) -> JSONResponse:
    return run_proxy(request, "seed", "POST", "/seeds/from-card", payload=payload)


@app.get("/api/v1/seeds/{seed_id}")
def get_seed(request: Request, seed_id: str) -> JSONResponse:
    return run_proxy(request, "seed", "GET", f"/seeds/{seed_id}")


@app.patch("/api/v1/seeds/{seed_id}")
def update_seed(request: Request, seed_id: str, payload: dict[str, Any]) -> JSONResponse:
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
    return run_proxy(request, "llm", "POST", f"/llm/tasks/{task_type}", payload=payload)


@app.post("/api/v1/sprout/start")
def start_sprout(request: Request, payload: dict[str, Any] | None = None) -> JSONResponse:
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
