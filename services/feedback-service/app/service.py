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
    def __init__(self, storage: Any = None, llm_client: Any = None) -> None:
        self._storage = storage  # If None, use in-memory dict
        self._llm_client = llm_client
        if self._storage:
            self._storage.load_initial_articles([dict(item) for item in FEEDBACK_ARTICLES])
        self._articles: dict[str, dict[str, Any]] = {item["id"]: dict(item) for item in FEEDBACK_ARTICLES}

    def _get_article_from_store(self, article_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get_article(article_id)
        return self._articles.get(article_id)

    def _save_article_to_store(self, article_id: str, data: dict[str, Any]) -> None:
        if self._storage:
            self._storage.save_article(article_id, data)
        self._articles[article_id] = data

    def _list_articles_from_store(self) -> list[dict[str, Any]]:
        if self._storage:
            return self._storage.list_articles()
        return list(self._articles.values())

    def list_articles(self, interest_id: str | None = None) -> dict[str, Any]:
        items = self._list_articles_from_store()
        if interest_id:
            items = [item for item in items if item["interestId"] == interest_id]
        return {"items": items}

    def get_article(self, article_id: str) -> dict[str, Any]:
        article = self._get_article_from_store(article_id)
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
            self._save_article_to_store(article["id"], article)
            return {"items": self._list_articles_from_store(), "syncedArticleId": article["id"]}
        return {
            "items": self._list_articles_from_store(),
            "syncedAt": _now_iso(),
            "note": "mock sync: no external call, returning cached articles.",
        }

    def comments_summary(self, article_id: str) -> dict[str, Any]:
        article = self.get_article(article_id)
        if self._llm_client:
            try:
                result = self._llm_client.feedback_summary(
                    article=article,
                    metrics={m.get("label", ""): m.get("value", 0) for m in article.get("metrics", [])},
                    comments=article.get("commentInsights", []),
                )
                signals = result.get("signals", [])
                supporting = [s.get("content", "") for s in signals if s.get("type") == "resonance"]
                counter = [s.get("content", "") for s in signals if s.get("type") == "disagreement"]
                request_more = [s.get("content", "") for s in signals if s.get("type") == "request_more"]
                angles = result.get("secondArticleIdeas", [])
                return {
                    "articleId": article_id,
                    "supportingViews": supporting or ["mock 暂无支持观点"],
                    "counterArguments": counter or ["mock 暂无反方观点"],
                    "supplementaryMaterials": request_more or ["mock 暂无补充材料"],
                    "secondArticleAngles": angles or ["mock 暂无二次角度"],
                    "schemaVersion": "feedback.comments.v1",
                    "llmSummary": result.get("summary", ""),
                }
            except Exception as e:
                import logging
                logging.getLogger("kanshan.feedback").warning("feedback_summary_failed", extra={"error": str(e)})
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
