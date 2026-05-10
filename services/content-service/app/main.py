from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("Install service dependencies with `pip install -r requirements.txt`.") from exc

from .repository import CardNotFound, CategoryNotFound, SourceNotFound
from .service import ContentService


app = FastAPI(title="Kanshan Content Service", version="0.1.0")
service = ContentService()


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
    return service.bootstrap()


@app.get("/content/cards")
def list_cards(category_id: str | None = None) -> dict[str, Any]:
    return service.list_cards(category_id)


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
        return service.refresh_category(category_id)
    except Exception as error:
        handle_error(error)
        raise


@app.post("/content/cards/{card_id}/summarize")
def summarize_card(card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return service.summarize_card(card_id, payload)
    except Exception as error:
        handle_error(error)
        raise
