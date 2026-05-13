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
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .llm_client import FeedbackLlmClient
from .service import ArticleNotFound, FeedbackService


app = FastAPI(title="Kanshan Feedback Service", version="0.2.0")
_config = load_config()
configure_logging("feedback-service", _config.logging)
logger = get_logger("kanshan.feedback_service.main")

_llm_client = FeedbackLlmClient(base_url=_config.service_urls.llm)

# Optional service clients (import lazily to avoid hard dependency)
_seed_client = None
_profile_client = None

try:
    from .service_clients import ProfileServiceClient, SeedServiceClient
    _seed_client = SeedServiceClient(base_url=_config.service_urls.seed)
    _profile_client = ProfileServiceClient(base_url=_config.service_urls.profile)
except Exception:
    logger.info("service_clients_not_available", extra={"note": "seed/profile calls will fallback to payload-only"})


if _config.storage_backend == "postgres":
    from .database import init_db
    init_db()
    from .pg_storage import PostgresFeedbackStorage
    service = FeedbackService(
        storage=PostgresFeedbackStorage(),
        llm_client=_llm_client,
        seed_client=_seed_client,
        profile_client=_profile_client,
    )
    logger.info("storage_backend_selected", extra={"backend": "postgres"})
else:
    service = FeedbackService(
        llm_client=_llm_client,
        seed_client=_seed_client,
        profile_client=_profile_client,
    )
    logger.info("storage_backend_selected", extra={"backend": "memory"})


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
    result = service.list_articles(interest_id)
    logger.info("feedback_article_list", extra={"interestId": interest_id, "count": len(result.get("items", []))})
    return result


@app.get("/feedback/articles/{article_id}")
def get_article(article_id: str) -> dict[str, Any]:
    try:
        return service.get_article(article_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/from-writing-session")
def create_from_writing_session(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        article = service.create_from_writing_session(payload)
        logger.info("feedback_article_created", extra={"articleId": article["id"], "interestId": article.get("interestId")})
        return article
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/{article_id}/refresh")
def refresh_feedback(article_id: str) -> dict[str, Any]:
    try:
        snapshot = service.refresh_feedback(article_id)
        logger.info("feedback_refreshed", extra={"articleId": article_id, "snapshotId": snapshot.get("snapshotId")})
        return snapshot
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/{article_id}/analyze")
def analyze_feedback(article_id: str) -> dict[str, Any]:
    try:
        analysis = service.analyze_feedback(article_id)
        logger.info("feedback_analyzed", extra={"articleId": article_id})
        return analysis
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
        result = service.second_seed(article_id, payload)
        logger.info("feedback_second_seed", extra={"articleId": article_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/feedback/articles/{article_id}/memory-update-request")
def memory_update_request(article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.memory_update_request(article_id, payload)
        logger.info("feedback_memory_update", extra={"articleId": article_id})
        return result
    except Exception as error:
        handle_error(error)
        raise
