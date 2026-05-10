from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .service import ArticleNotFound, FeedbackService


app = FastAPI(title="Kanshan Feedback Service", version="0.1.0")
service = FeedbackService()


def handle_error(error: Exception) -> None:
    if isinstance(error, ArticleNotFound):
        raise HTTPException(status_code=404, detail={"code": "ARTICLE_NOT_FOUND", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "feedback-service"}


@app.get("/feedback/articles")
def list_articles(interest_id: str | None = None) -> dict[str, Any]:
    return service.list_articles(interest_id)


@app.get("/feedback/articles/{article_id}")
def get_article(article_id: str) -> dict[str, Any]:
    try:
        return service.get_article(article_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/sync")
def sync(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return service.sync(payload)


@app.get("/feedback/articles/{article_id}/comments-summary")
def comments_summary(article_id: str) -> dict[str, Any]:
    try:
        return service.comments_summary(article_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/{article_id}/second-seed")
def second_seed(article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.second_seed(article_id, payload)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/{article_id}/memory-update-request")
def memory_update_request(article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.memory_update_request(article_id, payload)
    except Exception as error:
        handle_error(error)
        raise
