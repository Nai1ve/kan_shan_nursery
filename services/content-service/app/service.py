from __future__ import annotations

from typing import Any

from .repository import (
    CardNotFound,
    CategoryNotFound,
    ContentRepository,
    SourceNotFound,
)


class ContentService:
    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository or ContentRepository()

    def bootstrap(self) -> dict[str, Any]:
        # Return all cards for bootstrap (frontend filters by category)
        # Don't apply top-N selection here; that's for per-category views
        from . import scheduler as content_scheduler
        cached = content_scheduler.get_cached_cards()
        if cached:
            cards = sorted(cached, key=lambda c: (-(c.get("relevanceScore") or 0), c["id"]))
        else:
            cards = self.repository.list_cards()
        return {
            "categories": self.repository.list_categories(),
            "cards": cards,
        }

    def list_cards(self, category_id: str | None = None) -> dict[str, Any]:
        return {"items": self.repository.list_cards(category_id)}

    def get_card(self, card_id: str) -> dict[str, Any]:
        return self.repository.get_card(card_id)

    def get_source(self, card_id: str, source_id: str) -> dict[str, Any]:
        return self.repository.get_source(card_id, source_id)

    def refresh_category(self, category_id: str) -> dict[str, Any]:
        return self.repository.refresh_category(category_id)

    def summarize_card(self, card_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        card = self.repository.get_card(card_id)
        focus = (payload or {}).get("focus")
        summary_text = card.get("contentSummary", "")
        if focus:
            summary_text = f"[focus={focus}] {summary_text}"
        controversies = card.get("controversies", [])
        writing_angles = card.get("writingAngles", [])
        next_card = self.repository.update_card(
            card_id,
            {
                "contentSummary": summary_text,
                "controversies": controversies or ["mock 摘要：暂未识别明显争议"],
                "writingAngles": writing_angles or ["mock 摘要：暂未生成可写角度"],
            },
        )
        return {
            "cardId": card_id,
            "summary": next_card["contentSummary"],
            "controversies": next_card["controversies"],
            "writingAngles": next_card["writingAngles"],
            "schemaVersion": "content.summarize.v1",
        }
