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


app = FastAPI(title="Kanshan Content Service", version="0.1.0")
_config = load_config()
configure_logging("content-service", _config.logging)
logger = get_logger("kanshan.content_service.main")

_zhihu_url = os.getenv("ZHIHU_ADAPTER_URL", "http://127.0.0.1:8070")
_profile_url = os.getenv("PROFILE_SERVICE_URL", "http://127.0.0.1:8010")
_llm_url = os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:8080")

enricher = LlmEnricher(llm_base_url=_llm_url)
repository = ContentRepository(enricher=enricher, profile_service_url=_profile_url)
service = ContentService(repository=repository)

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
def bootstrap() -> dict[str, Any]:
    result = service.bootstrap()
    logger.info("content_bootstrap", extra={"cardCount": len(result.get("cards", []))})
    return result


@app.get("/content/cards")
def list_cards(category_id: str | None = None) -> dict[str, Any]:
    result = service.list_cards(category_id)
    logger.info("content_card_list", extra={"categoryId": category_id, "count": len(result.get("cards", []))})
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
def refresh_category(category_id: str) -> dict[str, Any]:
    try:
        result = service.refresh_category(category_id)
        logger.info("content_category_refresh", extra={"categoryId": category_id})
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
