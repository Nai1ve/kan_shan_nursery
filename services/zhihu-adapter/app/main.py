from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .service import QuotaExceeded, ZhihuAdapterService


app = FastAPI(title="Kanshan Zhihu Adapter", version="0.1.0")
service = ZhihuAdapterService()


def handle_error(error: Exception) -> None:
    if isinstance(error, QuotaExceeded):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "ZHIHU_QUOTA_EXCEEDED",
                "message": str(error),
                "endpoint": error.endpoint,
                "limit": error.limit,
            },
        )
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "zhihu-adapter"}


@app.get("/zhihu/hot-list")
def hot_list(limit: int = 30) -> dict[str, Any]:
    try:
        return service.hot_list(limit)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/zhihu-search")
def zhihu_search(query: str, count: int = 10) -> dict[str, Any]:
    try:
        return service.zhihu_search(query, count)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/global-search")
def global_search(query: str, count: int = 10) -> dict[str, Any]:
    try:
        return service.global_search(query, count)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.post("/zhihu/direct-answer")
def direct_answer(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.direct_answer(payload)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/zhihu/ring-detail")
def ring_detail(ring_id: str, page_num: int = 1, page_size: int = 20) -> dict[str, Any]:
    try:
        return service.ring_detail(ring_id, page_num, page_size)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/comments")
def comments(content_type: str, content_token: str) -> dict[str, Any]:
    try:
        return service.comments(content_type, content_token)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/story-list")
def story_list() -> dict[str, Any]:
    try:
        return service.story_list()
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/story-detail")
def story_detail(work_id: str) -> dict[str, Any]:
    try:
        return service.story_detail(work_id)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/following-feed")
def following_feed() -> dict[str, Any]:
    try:
        return service.following_feed()
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/user-followed")
def user_followed(page: int = 0, per_page: int = 10) -> dict[str, Any]:
    try:
        return service.user_followed(page, per_page)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.get("/zhihu/user-followers")
def user_followers(page: int = 0, per_page: int = 10) -> dict[str, Any]:
    try:
        return service.user_followers(page, per_page)
    except Exception as error:  # pragma: no cover
        handle_error(error)
        raise


@app.post("/zhihu/publish/mock-or-live")
def publish_pin(payload: dict[str, Any]) -> dict[str, Any]:
    return service.publish_pin(payload)


@app.post("/zhihu/comment/create")
def create_comment(payload: dict[str, Any]) -> dict[str, Any]:
    return service.create_comment(payload)


@app.post("/zhihu/reaction")
def reaction(payload: dict[str, Any]) -> dict[str, Any]:
    return service.reaction(payload)
