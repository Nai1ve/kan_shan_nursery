from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .mock_data import COMMENT_SUMMARIES, FEEDBACK_ARTICLES


class ArticleNotFound(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class FeedbackService:
    def __init__(self) -> None:
        self._articles: dict[str, dict[str, Any]] = {item["id"]: dict(item) for item in FEEDBACK_ARTICLES}

    def list_articles(self, interest_id: str | None = None) -> dict[str, Any]:
        items = list(self._articles.values())
        if interest_id:
            items = [item for item in items if item["interestId"] == interest_id]
        return {"items": items}

    def get_article(self, article_id: str) -> dict[str, Any]:
        article = self._articles.get(article_id)
        if not article:
            raise ArticleNotFound(article_id)
        return article

    def sync(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        if payload.get("article"):
            article = {**payload["article"]}
            article.setdefault("id", _create_id("article"))
            article.setdefault("commentInsights", [])
            article.setdefault("metrics", [])
            article.setdefault("statusTone", "blue")
            article.setdefault("status", "待解析")
            article.setdefault("performanceSummary", "新同步的文章，尚未生成表现摘要。")
            article.setdefault("memoryAction", "等待评论摘要")
            self._articles[article["id"]] = article
            return {"items": list(self._articles.values()), "syncedArticleId": article["id"]}
        return {
            "items": list(self._articles.values()),
            "syncedAt": _now_iso(),
            "note": "mock sync: no external call, returning cached articles.",
        }

    def comments_summary(self, article_id: str) -> dict[str, Any]:
        self.get_article(article_id)
        summary = COMMENT_SUMMARIES.get(article_id)
        if summary:
            return {**summary, "articleId": article_id, "schemaVersion": "feedback.comments.v1"}
        return {
            "articleId": article_id,
            "supportingViews": ["mock 暂无支持观点"],
            "counterArguments": ["mock 暂无反方观点"],
            "supplementaryMaterials": ["mock 暂无补充材料"],
            "secondArticleAngles": ["mock 暂无二次角度"],
            "schemaVersion": "feedback.comments.v1",
        }

    def second_seed(self, article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        article = self.get_article(article_id)
        angles = COMMENT_SUMMARIES.get(article_id, {}).get("secondArticleAngles", [])
        preferred_angle = (payload or {}).get("angle") or (angles[0] if angles else article["title"])
        return {
            "articleId": article_id,
            "seedPayload": {
                "title": f"来自反馈：{preferred_angle}",
                "interestId": article["interestId"],
                "coreClaim": preferred_angle,
                "userNote": f"基于文章《{article['title']}》的读者反馈形成的二次观点种子。",
                "possibleAngles": angles or [preferred_angle],
                "counterArguments": COMMENT_SUMMARIES.get(article_id, {}).get("counterArguments", []),
                "requiredMaterials": COMMENT_SUMMARIES.get(article_id, {}).get("supplementaryMaterials", []),
                "sourceTitle": article["title"],
                "sourceType": "feedback_article",
                "source": "历史反馈",
            },
            "schemaVersion": "feedback.second-seed.v1",
        }

    def memory_update_request(self, article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        article = self.get_article(article_id)
        payload = payload or {}
        request_body = {
            "id": _create_id("memreq"),
            "interestId": article["interestId"],
            "articleId": article_id,
            "proposedPatch": payload.get("patch")
            or {
                "writingReminder": article.get("memoryAction", "补充读者反馈中的反方质疑和真实案例需求。"),
            },
            "reason": payload.get("reason") or article.get("memoryAction", "文章反馈显示需要更多真实案例。"),
            "status": "pending",
            "createdAt": _now_iso(),
            "schemaVersion": "feedback.memory-request.v1",
        }
        return {
            "articleId": article_id,
            "memoryUpdateRequest": request_body,
            "note": "仅生成更新建议，不自动写入 Memory。需要前端通过 profile-service 的 apply 接口确认。",
        }
