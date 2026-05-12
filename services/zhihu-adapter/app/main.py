from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Make kanshan_shared importable when running uvicorn without installing the package.
# In Docker, shared-python is installed via pip, so no sys.path manipulation needed.
try:
    _SHARED_ROOT = Path(__file__).resolve().parents[3] / "packages" / "shared-python"
except (IndexError, OSError):
    _SHARED_ROOT = None
if _SHARED_ROOT and str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from kanshan_shared import configure_logging, get_logger, load_config

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .errors import ZhihuApiError
from .service import ZhihuAdapterService


_config = load_config()

configure_logging("zhihu-adapter", _config.logging)
logger = get_logger("kanshan.zhihu.main")

app = FastAPI(title="Kanshan Zhihu Adapter", version="0.2.0")
service = ZhihuAdapterService()


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or ""


def _zhihu_http_exception(error: ZhihuApiError) -> HTTPException:
    return HTTPException(
        status_code=error.http_status,
        detail={"code": error.code, "message": error.message, "detail": error.detail},
    )


def _handle(request: Request, action: str, fn):
    request_id = _request_id(request)
    logger.info("zhihu_endpoint_called", extra={"requestId": request_id, "endpoint": action})
    try:
        return fn()
    except ZhihuApiError as error:
        logger.warning(
            "zhihu_endpoint_error",
            extra={
                "requestId": request_id,
                "endpoint": action,
                "errorCode": error.code,
                "httpStatus": error.http_status,
            },
        )
        raise _zhihu_http_exception(error)
    except ValueError as error:
        logger.warning(
            "zhihu_endpoint_invalid",
            extra={"requestId": request_id, "endpoint": action, "errorMessage": str(error)},
        )
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "zhihu-adapter"}


@app.get("/zhihu/hot-list")
def hot_list(request: Request, limit: int = 30) -> dict[str, Any]:
    return _handle(request, "hot_list", lambda: service.hot_list(limit))


@app.get("/zhihu/zhihu-search")
def zhihu_search(request: Request, query: str = Query(...), count: int = 10) -> dict[str, Any]:
    return _handle(request, "zhihu_search", lambda: service.zhihu_search(query, count))


@app.get("/zhihu/global-search")
def global_search(request: Request, query: str = Query(...), count: int = 10) -> dict[str, Any]:
    return _handle(request, "global_search", lambda: service.global_search(query, count))


@app.post("/zhihu/direct-answer")
def direct_answer(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    return _handle(request, "direct_answer", lambda: service.direct_answer(payload))


@app.get("/zhihu/ring-detail")
def ring_detail(request: Request, ring_id: str, page_num: int = 1, page_size: int = 20) -> dict[str, Any]:
    return _handle(request, "ring_detail", lambda: service.ring_detail(ring_id, page_num, page_size))


@app.get("/zhihu/comments")
def comments(request: Request, content_type: str, content_token: str) -> dict[str, Any]:
    return _handle(request, "comments", lambda: service.comments(content_type, content_token))


@app.get("/zhihu/story-list")
def story_list(request: Request) -> dict[str, Any]:
    return _handle(request, "story_list", lambda: service.story_list())


@app.get("/zhihu/story-detail")
def story_detail(request: Request, work_id: str) -> dict[str, Any]:
    return _handle(request, "story_detail", lambda: service.story_detail(work_id))


@app.get("/zhihu/user")
def user_info(request: Request) -> dict[str, Any]:
    return _handle(request, "user_info", lambda: service.user_info())


@app.get("/zhihu/following-feed")
def following_feed(request: Request) -> dict[str, Any]:
    return _handle(request, "following_feed", lambda: service.following_feed())


@app.get("/zhihu/user-followed")
def user_followed(request: Request, page: int = 0, per_page: int = 10) -> dict[str, Any]:
    return _handle(request, "user_followed", lambda: service.user_followed(page, per_page))


@app.get("/zhihu/user-followers")
def user_followers(request: Request, page: int = 0, per_page: int = 10) -> dict[str, Any]:
    return _handle(request, "user_followers", lambda: service.user_followers(page, per_page))


@app.post("/zhihu/publish/mock-or-live")
def publish_pin(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    return _handle(request, "publish_pin", lambda: service.publish_pin(payload))


@app.post("/zhihu/comment/create")
def create_comment(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    return _handle(request, "create_comment", lambda: service.create_comment(payload))


@app.post("/zhihu/reaction")
def reaction(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    return _handle(request, "reaction", lambda: service.reaction(payload))


# ---- OAuth flow --------------------------------------------------------------

@app.get("/zhihu/oauth/authorize")
def oauth_authorize(request: Request, redirect: bool = False) -> Any:
    """Return the Zhihu authorize URL.

    With ``redirect=true`` the adapter returns an HTTP 302 to that URL so
    the browser can navigate directly (used by the frontend "绑定知乎"
    button). Without it (default) the adapter returns JSON for backend
    introspection.
    """
    info = _handle(request, "oauth_authorize", lambda: service.authorize_url())
    if redirect:
        return RedirectResponse(url=info["url"])
    return info


@app.get("/zhihu/oauth/callback")
def oauth_callback(request: Request, code: str | None = None, error: str | None = None) -> Any:
    """Exchange the authorization code for an access_token.

    The frontend redirects the user to this endpoint after the Zhihu
    authorize page sends them back. The adapter does not persist the
    token to disk; for v0.6 we render a minimal HTML so the operator
    can copy the access_token into ``services/config.yaml`` under
    ``zhihu.oauth.access_token``. A future release can write back to
    profile-service or to a session store automatically.
    """
    if error:
        raise HTTPException(status_code=400, detail={"code": "OAUTH_DENIED", "message": error})
    if not code:
        raise HTTPException(status_code=400, detail={"code": "OAUTH_CODE_MISSING", "message": "code is required"})
    token = _handle(request, "oauth_callback", lambda: service.exchange_oauth_code(code))
    body = (
        "<!doctype html>"
        "<meta charset='utf-8'>"
        "<title>看山小苗圃 · 知乎授权完成</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:640px;margin:48px auto;padding:0 24px;color:#1f2937}"
        "h1{font-size:20px}code{background:#f3f4f6;padding:2px 6px;border-radius:4px;font-size:13px}"
        "pre{background:#f9fafb;padding:16px;border-radius:8px;overflow:auto;font-size:12px}</style>"
        "<h1>知乎授权已完成</h1>"
        "<p>请把下面的 <code>access_token</code> 写入 <code>services/config.yaml</code> 的 "
        "<code>zhihu.oauth.access_token</code> 字段（已通过 .gitignore 保护，不会被提交）。</p>"
        f"<pre>{token}</pre>"
        "<p>写入完成后回到看山小苗圃页面即可继续使用关注流 / 关注列表 / 关注动态等 OAuth 能力。</p>"
    )
    return HTMLResponse(content=body)
