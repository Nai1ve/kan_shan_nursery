from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import mappers, mock_data
from .cache import CacheBackend, build_cache
from .errors import (
    QuotaExceeded,
    ZhihuApiError,
    ZhihuInvalidRequest,
    ZhihuRingNotWritable,
)
from .live_client import ClientBundle
from .security import stable_hash
from .settings import Settings, get_settings


logger = logging.getLogger("kanshan.zhihu.service")


TTL_SECONDS = {
    "hot_list": 15 * 60,
    "zhihu_search": 60 * 60,
    "global_search": 60 * 60,
    "direct_answer": 6 * 60 * 60,
    "ring_detail": 10 * 60,
    "comment_list": 10 * 60,
    "story_list": 6 * 60 * 60,
    "story_detail": 6 * 60 * 60,
    "user_info": 30 * 60,
    "following_feed": 10 * 60,
    "user_followed": 30 * 60,
    "user_followers": 30 * 60,
}


class ZhihuAdapterService:
    def __init__(
        self,
        settings: Settings | None = None,
        cache: CacheBackend | None = None,
        clients: ClientBundle | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or build_cache(self.settings)
        self.clients = clients or ClientBundle(self.settings)

    @property
    def _quota_limits(self) -> dict[str, int]:
        q = self.settings.zhihu.quota
        return {
            "hot_list": q.hot_list,
            "zhihu_search": q.zhihu_search,
            "global_search": q.global_search,
            "direct_answer": q.direct_answer,
        }

    def _live_enabled(self) -> bool:
        return self.settings.provider_mode == "live"

    def _result(self, items: Any, cache_key: str, hit: bool, endpoint: str, fallback: bool = False) -> dict[str, Any]:
        limit = self._quota_limits.get(endpoint)
        used = self.cache.get_quota(endpoint, self.settings.demo_user_id)
        return {
            "items": items,
            "cache": {
                "hit": hit,
                "key": cache_key,
                "ttlSeconds": TTL_SECONDS.get(endpoint, 0),
                "fallback": fallback,
            },
            "quota": {
                "endpoint": endpoint,
                "usedToday": used,
                "limitToday": limit,
                "warning": bool(limit and used >= int(limit * 0.8)),
            },
        }

    def _cached(self, endpoint: str, cache_key: str, loader: Callable[[], Any]) -> dict[str, Any]:
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info(
                "zhihu_cache_hit",
                extra={"endpoint": endpoint, "cacheKey": cache_key, "providerMode": self.settings.provider_mode},
            )
            return self._result(cached, cache_key, True, endpoint)

        limit = self._quota_limits.get(endpoint)
        used = self.cache.get_quota(endpoint, self.settings.demo_user_id)
        if limit is not None and used >= limit:
            logger.warning(
                "zhihu_quota_exceeded",
                extra={"endpoint": endpoint, "limit": limit, "usedToday": used},
            )
            raise QuotaExceeded(endpoint, limit)

        logger.info(
            "zhihu_call_started",
            extra={"endpoint": endpoint, "cacheKey": cache_key, "providerMode": self.settings.provider_mode},
        )
        try:
            items = loader()
        except ZhihuApiError as error:
            logger.error(
                "zhihu_call_failed",
                extra={
                    "endpoint": endpoint,
                    "errorCode": error.code,
                    "errorMessage": error.message,
                },
            )
            raise

        self.cache.set(cache_key, items, TTL_SECONDS.get(endpoint, 60))
        new_used = used
        if limit is not None:
            new_used = self.cache.increment_quota(endpoint, self.settings.demo_user_id)
        logger.info(
            "zhihu_call_succeeded",
            extra={"endpoint": endpoint, "cacheKey": cache_key, "quotaUsedToday": new_used},
        )
        return self._result(items, cache_key, False, endpoint)

    # ---- Data Platform endpoints --------------------------------------------------

    def hot_list(self, limit: int = 30) -> dict[str, Any]:
        normalized_limit = 30 if limit <= 0 or limit > 30 else limit
        key = f"zhihu:hot_list:{normalized_limit}"
        return self._cached(
            "hot_list",
            key,
            lambda: mappers.map_hot_list(
                self.clients.data_platform.get("/api/v1/content/hot_list", {"Limit": normalized_limit})
                if self._live_enabled()
                else mock_data.hot_list()
            )[:normalized_limit],
        )

    def zhihu_search(self, query: str, count: int = 10) -> dict[str, Any]:
        if not query:
            raise ZhihuInvalidRequest("query is required")
        normalized_count = 10 if count <= 0 else min(count, 10)
        key = f"zhihu:zhihu_search:{stable_hash(query)}:{normalized_count}"
        return self._cached(
            "zhihu_search",
            key,
            lambda: mappers.map_search(
                self.clients.data_platform.get(
                    "/api/v1/content/zhihu_search", {"Query": query, "Count": normalized_count}
                )
                if self._live_enabled()
                else mock_data.zhihu_search(query, normalized_count),
                "zhihu_search",
            ),
        )

    def global_search(self, query: str, count: int = 10) -> dict[str, Any]:
        if not query:
            raise ZhihuInvalidRequest("query is required")
        normalized_count = 10 if count <= 0 else min(count, 20)
        key = f"zhihu:global_search:{stable_hash(query)}:{normalized_count}"
        return self._cached(
            "global_search",
            key,
            lambda: mappers.map_search(
                self.clients.data_platform.get(
                    "/api/v1/content/global_search", {"Query": query, "Count": normalized_count}
                )
                if self._live_enabled()
                else mock_data.global_search(query, normalized_count),
                "global_search",
            ),
        )

    def direct_answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model", self.settings.zhihu.data_platform.default_model)
        messages = payload.get("messages", [])
        stream = bool(payload.get("stream", False))
        if stream:
            raise ZhihuInvalidRequest("P0 only supports stream=false")
        if not messages:
            raise ZhihuInvalidRequest("messages must not be empty")
        key = (
            f"zhihu:direct_answer:{model}:"
            f"{stable_hash(json.dumps(messages, ensure_ascii=False, sort_keys=True))}:stream_false"
        )
        request_payload = {"model": model, "messages": messages, "stream": False}
        result = self._cached(
            "direct_answer",
            key,
            lambda: mappers.map_direct_answer(
                self.clients.data_platform.post("/v1/chat/completions", request_payload)
                if self._live_enabled()
                else mock_data.direct_answer(model)
            ),
        )
        return {**result["items"], "cache": result["cache"], "quota": result["quota"]}

    # ---- Community endpoints ------------------------------------------------------

    def ring_detail(self, ring_id: str, page_num: int = 1, page_size: int = 20) -> dict[str, Any]:
        normalized_size = min(max(page_size, 1), 50)
        key = f"zhihu:ring_detail:{ring_id}:{page_num}:{normalized_size}"
        return self._cached(
            "ring_detail",
            key,
            lambda: mappers.map_ring_detail(
                self.clients.community.get(
                    "/openapi/ring/detail",
                    {"ring_id": ring_id, "page_num": page_num, "page_size": normalized_size},
                )
                if self._live_enabled()
                else mock_data.ring_detail()
            ),
        )

    def comments(self, content_type: str, content_token: str) -> dict[str, Any]:
        key = f"zhihu:comment_list:{content_type}:{content_token}"
        return self._cached(
            "comment_list",
            key,
            lambda: (
                self.clients.community.get(
                    "/openapi/comment/list",
                    {"content_type": content_type, "content_token": content_token},
                )
                if self._live_enabled()
                else mock_data.comments()
            )
            .get("data", {})
            .get("comments", []),
        )

    def story_list(self) -> dict[str, Any]:
        return self._cached(
            "story_list",
            "zhihu:story_list",
            lambda: mappers.map_story_list(
                self.clients.community.get("/openapi/hackathon_story/list", {})
                if self._live_enabled()
                else mock_data.story_list()
            ),
        )

    def story_detail(self, work_id: str) -> dict[str, Any]:
        if not work_id:
            raise ZhihuInvalidRequest("work_id is required")
        key = f"zhihu:story_detail:{work_id}"
        return self._cached(
            "story_detail",
            key,
            lambda: mappers.map_story_detail(
                self.clients.community.get("/openapi/hackathon_story/detail", {"work_id": work_id})
                if self._live_enabled()
                else mock_data.story_detail(work_id)
            ),
        )

    def publish_pin(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_writable_ring(payload.get("ring_id"))
        if self._live_enabled():
            return self.clients.community.post("/openapi/publish/pin", payload)
        return {"mode": self.settings.provider_mode, "contentToken": "mock-pin-token", "request": payload}

    def create_comment(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("content_token") or not payload.get("content_type"):
            raise ZhihuInvalidRequest("content_token and content_type are required")
        if self._live_enabled():
            return self.clients.community.post("/openapi/comment/create", payload)
        return {"mode": self.settings.provider_mode, "commentId": "mock-comment-id", "request": payload}

    def reaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("action_type") != "like":
            raise ZhihuInvalidRequest("only action_type=like is supported")
        if self._live_enabled():
            return self.clients.community.post("/openapi/reaction", payload)
        return {"mode": self.settings.provider_mode, "success": True, "request": payload}

    # ---- OAuth endpoints ----------------------------------------------------------

    def authorize_url(self, state: str | None = None) -> dict[str, Any]:
        return {"url": self.clients.oauth.authorize_url(state=state), "redirectUri": self.settings.zhihu.oauth.redirect_uri}

    def exchange_oauth_code(self, code: str) -> dict[str, Any]:
        if not code:
            raise ZhihuInvalidRequest("code is required")
        logger.info(
            "zhihu_oauth_exchange_started",
            extra={"providerMode": self.settings.provider_mode, "codeHash": stable_hash(code)},
        )
        token = self.clients.oauth.exchange_code_for_token(code)
        logger.info(
            "zhihu_oauth_exchange_succeeded",
            extra={
                "providerMode": self.settings.provider_mode,
                "responseKeys": sorted(list(token.keys())) if isinstance(token, dict) else [],
                "tokenType": token.get("token_type") if isinstance(token, dict) else None,
                "expiresIn": token.get("expires_in") if isinstance(token, dict) else None,
            },
        )
        return token

    def user_info(self, access_token: str | None = None) -> dict[str, Any]:
        logger.info(
            "zhihu_user_info_started",
            extra={
                "providerMode": self.settings.provider_mode,
                "hasAccessToken": bool(access_token),
                "accessTokenHash": stable_hash(access_token) if access_token else None,
            },
        )
        key = f"zhihu:user:{self.settings.demo_user_id}:{stable_hash(access_token or 'configured')}"
        result = self._cached(
            "user_info",
            key,
            lambda: mappers.map_oauth_user(
                self.clients.oauth.get("/user", access_token=access_token)
                if self._live_enabled()
                else {
                    "uid": 1,
                    "fullname": "看山测试用户",
                    "gender": "unknown",
                    "headline": "AI Coding 观察者",
                    "description": "关注 Agent 与内容创作。",
                    "avatar_path": "",
                    "email": "",
                    "phone_no": "",
                }
            ),
        )
        items = result.get("items", []) if isinstance(result, dict) else []
        first_keys = sorted(list(items[0].keys())) if isinstance(items, list) and items and isinstance(items[0], dict) else []
        logger.info(
            "zhihu_user_info_succeeded",
            extra={
                "providerMode": self.settings.provider_mode,
                "cacheHit": bool(result.get("cache", {}).get("hit")) if isinstance(result, dict) else False,
                "itemsCount": len(items) if isinstance(items, list) else 0,
                "firstItemKeys": first_keys,
            },
        )
        return result

    def following_feed(self, access_token: str | None = None) -> dict[str, Any]:
        key = f"zhihu:user_moments:{self.settings.demo_user_id}:{stable_hash(access_token or 'configured')}"
        return self._cached(
            "following_feed",
            key,
            lambda: mappers.map_following_feed(
                self.clients.oauth.get("/user/moments", access_token=access_token)
                if self._live_enabled()
                else mock_data.following_feed()
            ),
        )

    def user_followed(self, page: int = 0, per_page: int = 10, access_token: str | None = None) -> dict[str, Any]:
        normalized_per_page = min(max(per_page, 1), 50)
        key = f"zhihu:user_followed:{self.settings.demo_user_id}:{page}:{normalized_per_page}:{stable_hash(access_token or 'configured')}"
        return self._cached(
            "user_followed",
            key,
            lambda: mappers.map_oauth_users(
                self.clients.oauth.get("/user/followed", {"page": page, "per_page": normalized_per_page}, access_token=access_token)
                if self._live_enabled()
                else [
                    {"uid": 1, "hash_id": "mock-author", "fullname": "关注作者", "headline": "AI Coding 观察者"},
                ]
            ),
        )

    def user_followers(self, page: int = 0, per_page: int = 10, access_token: str | None = None) -> dict[str, Any]:
        normalized_per_page = min(max(per_page, 1), 50)
        key = f"zhihu:user_followers:{self.settings.demo_user_id}:{page}:{normalized_per_page}:{stable_hash(access_token or 'configured')}"
        return self._cached(
            "user_followers",
            key,
            lambda: mappers.map_oauth_users(
                self.clients.oauth.get("/user/followers", {"page": page, "per_page": normalized_per_page}, access_token=access_token)
                if self._live_enabled()
                else [
                    {"uid": 2, "hash_id": "mock-reader", "fullname": "读者 A", "headline": "技术读者"},
                ]
            ),
        )

    # ---- guards -------------------------------------------------------------------

    def _require_writable_ring(self, ring_id: str | None) -> None:
        whitelist = self.settings.zhihu.community.writable_ring_ids
        if not whitelist:
            return
        if not ring_id or str(ring_id) not in whitelist:
            raise ZhihuRingNotWritable(
                f"ring_id not in writable list: {ring_id}",
                detail={"writableRingIds": list(whitelist)},
            )
