from __future__ import annotations


import os
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

from .enricher import LlmEnricher
from .repository import CardNotFound, CategoryNotFound, ContentRepository, SourceNotFound
from .scheduler import ContentScheduler
from .service import ContentService
from .snapshot_repository import SnapshotRepository


app = FastAPI(title="Kanshan Content Service", version="0.2.0")
_config = load_config()
configure_logging("content-service", _config.logging)
logger = get_logger("kanshan.content_service.main")

_zhihu_url = _config.service_urls.zhihu
_profile_url = _config.service_urls.profile
_llm_url = _config.service_urls.llm

enricher = LlmEnricher(llm_base_url=_llm_url)
repository = ContentRepository(enricher=enricher, profile_service_url=_profile_url)
snapshot_repo = SnapshotRepository()
service = ContentService(repository=repository, snapshot_repo=snapshot_repo)

# Start background content scheduler
_scheduler = ContentScheduler(zhihu_base_url=_zhihu_url, profile_base_url=_profile_url)
_scheduler.start()


def handle_error(error: Exception) -> None:
    if isinstance(error, CardNotFound):
        raise HTTPException(status_code=404, detail={"code": "CARD_NOT_FOUND", "message": str(error)})
    if isinstance(error, SourceNotFound):
        raise HTTPException(status_code=404, detail={"code": "SOURCE_NOT_FOUND", "message": str(error)})
    if isinstance(error, CategoryNotFound):
        raise HTTPException(status_code=404, detail={"code": "CATEGORY_NOT_FOUND", "message": str(error)})
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(error)})
    raise error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "content-service"}


@app.get("/content")
def bootstrap(
    user_id: str | None = None,
    interest_ids: str | None = None,
) -> dict[str, Any]:
    interests = [item.strip() for item in interest_ids.split(",")] if interest_ids else None
    result = service.bootstrap(user_id=user_id, interest_ids=interests)
    logger.info(
        "content_bootstrap",
        extra={"cardCount": len(result.get("cards", [])), "userId": user_id, "filtered": bool(interests)},
    )
    return result


@app.get("/content/cards")
def list_cards(
    category_id: str | None = None,
    user_id: str | None = None,
    interest_ids: str | None = None,
    limit: int = 2,
    exclude_ids: str | None = None,
) -> dict[str, Any]:
    interests = [item.strip() for item in interest_ids.split(",")] if interest_ids else None
    excludes = [item.strip() for item in exclude_ids.split(",") if item.strip()] if exclude_ids else None
    result = service.list_cards(
        category_id=category_id,
        user_id=user_id,
        interest_ids=interests,
        limit=limit,
        exclude_ids=excludes,
    )
    logger.info("content_card_list", extra={"categoryId": category_id, "userId": user_id, "count": len(result.get("items", []))})
    return result


@app.get("/content/cards/{card_id}")
def get_card(card_id: str) -> dict[str, Any]:
    try:
        return service.get_card(card_id)
    except Exception as error:
        handle_error(error)
        raise


@app.get("/content/cards/{card_id}/sources/{source_id}")
def get_source(card_id: str, source_id: str) -> dict[str, Any]:
    try:
        return service.get_source(card_id, source_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/content/categories/{category_id}/refresh")
def refresh_category(category_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        user_id = (payload or {}).get("user_id")
        exclude_ids = (payload or {}).get("exclude_ids", [])
        limit = int((payload or {}).get("limit") or 2)
        result = service.refresh_category(
            category_id=category_id,
            user_id=user_id,
            exclude_ids=exclude_ids,
            limit=limit,
        )
        logger.info("content_category_refresh", extra={"categoryId": category_id, "userId": user_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/content/cards/{card_id}/summarize")
def summarize_card(card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = service.summarize_card(card_id, payload)
        logger.info("content_summarize", extra={"cardId": card_id})
        return result
    except Exception as error:
        handle_error(error)
        raise


@app.post("/content/cards/{card_id}/enrich")
def enrich_card(card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """On-demand card enrichment (TikTok-style progressive loading)."""
    try:
        user_id = (payload or {}).get("user_id")
        result = service.enrich_card_on_demand(card_id, user_id)
        logger.info("content_enrich", extra={"cardId": card_id, "userId": user_id})
        return result
    except Exception as error:
        handle_error(error)
        raise
