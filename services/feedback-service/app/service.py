from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .mock_data import COMMENT_SUMMARIES, FEEDBACK_ARTICLES, MOCK_ANALYSES, MOCK_COMMENTS


class ArticleNotFound(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class FeedbackService:
    def __init__(self, storage: Any = None, llm_client: Any = None, seed_client: Any = None, profile_client: Any = None) -> None:
        self._storage = storage  # If None, use in-memory dict
        self._llm_client = llm_client
        self._seed_client = seed_client
        self._profile_client = profile_client
        if self._storage:
            self._storage.load_initial_articles([dict(item) for item in FEEDBACK_ARTICLES])
        self._articles: dict[str, dict[str, Any]] = {item["id"]: dict(item) for item in FEEDBACK_ARTICLES}
        self._snapshots: dict[str, list[dict[str, Any]]] = {}  # article_id -> [snapshots]
        self._analyses: dict[str, dict[str, Any]] = {}  # article_id -> analysis

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

    def _save_snapshot(self, article_id: str, metrics: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
        snapshot_id = _create_id("snapshot")
        if self._storage:
            return self._storage.save_snapshot(snapshot_id, article_id, metrics, comments)
        snapshot = {
            "snapshotId": snapshot_id,
            "articleId": article_id,
            "capturedAt": _now_iso(),
            "metrics": metrics,
            "comments": comments,
        }
        self._snapshots.setdefault(article_id, []).append(snapshot)
        return snapshot

    def _get_latest_snapshot(self, article_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get_latest_snapshot(article_id)
        snapshots = self._snapshots.get(article_id, [])
        return snapshots[-1] if snapshots else None

    def _save_analysis(self, article_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        analysis_id = _create_id("analysis")
        if self._storage:
            return self._storage.save_analysis(analysis_id, article_id, analysis)
        analysis["articleId"] = article_id
        analysis["generatedAt"] = _now_iso()
        self._analyses[article_id] = analysis
        return analysis

    def _get_analysis(self, article_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get_analysis(article_id)
        return self._analyses.get(article_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_articles(self, interest_id: str | None = None) -> dict[str, Any]:
        items = self._list_articles_from_store()
        if interest_id:
            items = [item for item in items if item.get("interestId") == interest_id]
        return {"items": items}

    def get_article(self, article_id: str) -> dict[str, Any]:
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)
        return {
            "article": article,
            "snapshots": self._snapshots.get(article_id, []) if not self._storage else [],
            "latestAnalysis": self._get_analysis(article_id),
        }

    def create_from_writing_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        article_id = _create_id("article")
        now = _now_iso()
        article = {
            "id": article_id,
            "userId": payload.get("userId", "demo-user"),
            "writingSessionId": payload.get("writingSessionId"),
            "seedId": payload.get("seedId"),
            "interestId": payload.get("interestId"),
            "title": payload.get("title", "未命名文章"),
            "coreClaim": payload.get("coreClaim", ""),
            "contentExcerpt": payload.get("contentExcerpt", ""),
            "articleType": payload.get("articleType", "article"),
            "publishMode": payload.get("publishMode", "mock"),
            "platformContentId": payload.get("platformContentId"),
            "ringId": payload.get("ringId"),
            "url": payload.get("url"),
            "publishedAt": payload.get("publishedAt", now),
            "status": "tracking",
            "statusTone": "blue",
            "performanceSummary": "文章已发布，等待读者反馈。",
            "commentInsights": [],
            "memoryAction": "等待反馈分析",
            "metrics": [],
            "latestMetrics": None,
            "latestAnalysis": None,
            "linkedSeedId": payload.get("seedId"),
        }
        self._save_article_to_store(article_id, article)
        return article

    def refresh_feedback(self, article_id: str) -> dict[str, Any]:
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)

        publish_mode = article.get("publishMode", "mock")
        if publish_mode == "mock":
            # Use mock data
            mock_comments = MOCK_COMMENTS.get(article_id, [])
            existing_metrics = article.get("latestMetrics") or {
                "readCount": 1000,
                "likeCount": 50,
                "commentCount": len(mock_comments),
                "favoriteCount": 30,
                "shareCount": 10,
                "metricSource": "mock",
            }
            existing_metrics["capturedAt"] = _now_iso()
            existing_metrics["metricSource"] = "mock"
        else:
            # TODO: call zhihu-adapter for real data (P1)
            mock_comments = []
            existing_metrics = article.get("latestMetrics") or {
                "likeCount": 0,
                "commentCount": 0,
                "metricSource": "unavailable",
            }
            existing_metrics["capturedAt"] = _now_iso()

        # Create snapshot
        snapshot = self._save_snapshot(article_id, existing_metrics, mock_comments)

        # Update article's latest metrics
        article["latestMetrics"] = existing_metrics
        self._save_article_to_store(article_id, article)

        return snapshot

    def analyze_feedback(self, article_id: str) -> dict[str, Any]:
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)

        # Get latest snapshot or use mock
        snapshot = self._get_latest_snapshot(article_id)
        if not snapshot:
            # Auto-refresh if no snapshot exists
            self.refresh_feedback(article_id)
            snapshot = self._get_latest_snapshot(article_id)

        metrics = snapshot.get("metrics", {}) if snapshot else {}
        comments = snapshot.get("comments", []) if snapshot else []

        # Call LLM if available
        if self._llm_client:
            try:
                result = self._llm_client.feedback_summary(
                    article=article,
                    metrics=metrics,
                    comments=comments,
                )
                analysis = {
                    "articleId": article_id,
                    "performanceSummary": result.get("summary", ""),
                    "readerSignals": result.get("signals", []),
                    "positiveFeedback": result.get("positiveFeedback", []),
                    "negativeFeedback": result.get("negativeFeedback", []),
                    "openQuestions": result.get("openQuestions", []),
                    "counterArguments": result.get("counterArguments", []),
                    "missingMaterials": result.get("missingMaterials", []),
                    "articlePortrait": result.get("articlePortrait", {
                        "strongestPoint": "",
                        "weakestPoint": "",
                        "readerProfile": "",
                        "controversyMap": [],
                        "styleFeedback": "",
                        "nextImprovement": "",
                    }),
                    "secondArticleIdeas": result.get("secondArticleIdeas", []),
                    "seedCandidates": result.get("seedCandidates", []),
                    "memoryUpdateCandidates": result.get("memoryUpdateCandidates", []),
                }
                self._save_analysis(article_id, analysis)
                # Update article status
                article["status"] = "analyzed"
                self._save_article_to_store(article_id, article)
                return analysis
            except Exception as e:
                import logging
                logging.getLogger("kanshan.feedback").warning("feedback_analysis_failed", extra={"error": str(e)})

        # Fallback to mock analysis
        mock_analysis = MOCK_ANALYSES.get(article_id)
        if mock_analysis:
            self._save_analysis(article_id, dict(mock_analysis))
            article["status"] = "analyzed"
            self._save_article_to_store(article_id, article)
            return dict(mock_analysis)

        # Minimal fallback
        summary = COMMENT_SUMMARIES.get(article_id, {})
        analysis = {
            "articleId": article_id,
            "performanceSummary": article.get("performanceSummary", ""),
            "readerSignals": [],
            "positiveFeedback": summary.get("supportingViews", []),
            "negativeFeedback": summary.get("counterArguments", []),
            "openQuestions": [],
            "counterArguments": summary.get("counterArguments", []),
            "missingMaterials": summary.get("supplementaryMaterials", []),
            "articlePortrait": {
                "strongestPoint": "",
                "weakestPoint": "",
                "readerProfile": "",
                "controversyMap": [],
                "styleFeedback": "",
                "nextImprovement": "",
            },
            "secondArticleIdeas": [],
            "seedCandidates": [],
            "memoryUpdateCandidates": [],
        }
        self._save_analysis(article_id, analysis)
        article["status"] = "analyzed"
        self._save_article_to_store(article_id, article)
        return analysis

    def sync(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        if payload.get("article"):
            article = {**payload["article"]}
            article.setdefault("id", _create_id("article"))
            article.setdefault("commentInsights", [])
            article.setdefault("metrics", [])
            article.setdefault("statusTone", "blue")
            article.setdefault("status", "tracking")
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
        """Legacy endpoint - combines refresh and analyze. Kept for backward compatibility."""
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)
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
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)

        # Try to get seed candidates from analysis
        analysis = self._get_analysis(article_id)
        candidates = analysis.get("seedCandidates", []) if analysis else []
        summary = COMMENT_SUMMARIES.get(article_id, {})

        if candidates:
            candidate = candidates[0]
            seed_payload = {
                "title": candidate.get("title", f"来自反馈：{article['title']}"),
                "interestId": article.get("interestId"),
                "coreClaim": candidate.get("coreClaim", ""),
                "userNote": candidate.get("reason", ""),
                "possibleAngles": [c.get("title", "") for c in candidates],
                "counterArguments": candidate.get("suggestedMaterials", {}).get("counterargument", []),
                "requiredMaterials": candidate.get("suggestedMaterials", {}).get("evidence", []),
                "sourceTitle": article.get("title", ""),
                "sourceType": "feedback_comment",
                "source": "历史反馈",
                "sourceArticleId": article_id,
                "sourceCommentIds": candidate.get("sourceCommentIds", []),
            }
        else:
            # Fallback to legacy behavior
            angles = summary.get("secondArticleAngles", [])
            preferred_angle = (payload or {}).get("angle") or (angles[0] if angles else article.get("title", ""))
            seed_payload = {
                "title": f"来自反馈：{preferred_angle}",
                "interestId": article.get("interestId"),
                "coreClaim": preferred_angle,
                "userNote": f"基于文章《{article.get('title', '')}》的读者反馈形成的二次观点种子。",
                "possibleAngles": angles or [preferred_angle],
                "counterArguments": summary.get("counterArguments", []),
                "requiredMaterials": summary.get("supplementaryMaterials", []),
                "sourceTitle": article.get("title", ""),
                "sourceType": "feedback_article",
                "source": "历史反馈",
                "sourceArticleId": article_id,
            }

        # Call seed-service if available
        if self._seed_client:
            try:
                result = self._seed_client.create_from_feedback(seed_payload)
                return {
                    "articleId": article_id,
                    "seed": result,
                    "schemaVersion": "feedback.second-seed.v1",
                }
            except Exception as e:
                import logging
                logging.getLogger("kanshan.feedback").warning("seed_service_call_failed", extra={"error": str(e)})

        # Fallback: return payload for frontend to handle
        return {
            "articleId": article_id,
            "seedPayload": seed_payload,
            "schemaVersion": "feedback.second-seed.v1",
        }

    def memory_update_request(self, article_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        article = self._get_article_from_store(article_id)
        if not article:
            raise ArticleNotFound(article_id)

        # Try to get memory candidates from analysis
        analysis = self._get_analysis(article_id)
        candidates = analysis.get("memoryUpdateCandidates", []) if analysis else []

        if candidates:
            candidate = candidates[0]
            request_body = {
                "interestId": candidate.get("interestId", article.get("interestId")),
                "targetField": candidate.get("targetField", "writingReminder"),
                "suggestedValue": candidate.get("suggestedValue", ""),
                "reason": candidate.get("reason", ""),
                "sourceArticleId": article_id,
            }
        else:
            # Fallback to legacy behavior
            request_body = {
                "interestId": article.get("interestId"),
                "targetField": "writingReminder",
                "suggestedValue": article.get("memoryAction", "补充读者反馈中的反方质疑和真实案例需求。"),
                "reason": article.get("memoryAction", "文章反馈显示需要更多真实案例。"),
                "sourceArticleId": article_id,
            }

        # Call profile-service if available
        if self._profile_client:
            try:
                result = self._profile_client.create_memory_update_request(request_body)
                return {
                    "articleId": article_id,
                    "memoryUpdateRequest": result,
                    "note": "已提交到 profile-service，需要用户确认后生效。",
                }
            except Exception as e:
                import logging
                logging.getLogger("kanshan.feedback").warning("profile_service_call_failed", extra={"error": str(e)})

        # Fallback: return request for frontend to handle
        request_body["id"] = _create_id("memreq")
        request_body["status"] = "pending"
        request_body["createdAt"] = _now_iso()
        return {
            "articleId": article_id,
            "memoryUpdateRequest": request_body,
            "note": "仅生成更新建议，不自动写入 Memory。需要前端通过 profile-service 的 apply 接口确认。",
        }
