import json
from typing import Any, Callable

from . import mappers, mock_data
from .cache import MemoryCache
from .live_client import LiveZhihuClient
from .security import stable_hash
from .settings import Settings, get_settings


TTL_SECONDS = {
    "hot_list": 15 * 60,
    "zhihu_search": 60 * 60,
    "global_search": 60 * 60,
    "direct_answer": 6 * 60 * 60,
    "ring_detail": 10 * 60,
    "comment_list": 10 * 60,
    "story_list": 6 * 60 * 60,
    "story_detail": 6 * 60 * 60,
    "following_feed": 10 * 60,
    "user_followed": 30 * 60,
    "user_followers": 30 * 60,
}

QUOTA_LIMITS = {
    "hot_list": 100,
    "zhihu_search": 1000,
    "global_search": 1000,
    "direct_answer": 100,
}


class QuotaExceeded(Exception):
    def __init__(self, endpoint: str, limit: int) -> None:
        super().__init__(f"{endpoint} quota exceeded: {limit}/day")
        self.endpoint = endpoint
        self.limit = limit


class ZhihuAdapterService:
    def __init__(self, settings: Settings | None = None, cache: MemoryCache | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or MemoryCache()
        self.live = LiveZhihuClient(self.settings)

    def _live_enabled(self) -> bool:
        return self.settings.provider_mode == "live"

    def _result(self, items: Any, cache_key: str, hit: bool, endpoint: str, fallback: bool = False) -> dict[str, Any]:
        limit = QUOTA_LIMITS.get(endpoint)
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
                "usedToday": self.cache.get_quota(endpoint, self.settings.demo_user_id),
                "limitToday": limit,
                "warning": bool(limit and self.cache.get_quota(endpoint, self.settings.demo_user_id) >= int(limit * 0.8)),
            },
        }

    def _cached(self, endpoint: str, cache_key: str, loader: Callable[[], Any]) -> dict[str, Any]:
        cached = self.cache.get(cache_key)
        if cached is not None:
            return self._result(cached, cache_key, True, endpoint)

        limit = QUOTA_LIMITS.get(endpoint)
        if limit is not None and self.cache.get_quota(endpoint, self.settings.demo_user_id) >= limit:
            raise QuotaExceeded(endpoint, limit)

        items = loader()
        self.cache.set(cache_key, items, TTL_SECONDS.get(endpoint, 60))
        if limit is not None:
            self.cache.increment_quota(endpoint, self.settings.demo_user_id)
        return self._result(items, cache_key, False, endpoint)

    def hot_list(self, limit: int = 30) -> dict[str, Any]:
        normalized_limit = 30 if limit <= 0 or limit > 30 else limit
        key = f"zhihu:hot_list:{normalized_limit}"
        return self._cached(
            "hot_list",
            key,
            lambda: mappers.map_hot_list(
                self.live.data_get("/api/v1/content/hot_list", {"Limit": normalized_limit})
                if self._live_enabled()
                else mock_data.hot_list()
            )[:normalized_limit],
        )

    def zhihu_search(self, query: str, count: int = 10) -> dict[str, Any]:
        normalized_count = 10 if count <= 0 else min(count, 10)
        key = f"zhihu:zhihu_search:{stable_hash(query)}:{normalized_count}"
        return self._cached(
            "zhihu_search",
            key,
            lambda: mappers.map_search(
                self.live.data_get("/api/v1/content/zhihu_search", {"Query": query, "Count": normalized_count})
                if self._live_enabled()
                else mock_data.zhihu_search(query, normalized_count),
                "zhihu_search",
            ),
        )

    def global_search(self, query: str, count: int = 10) -> dict[str, Any]:
        normalized_count = 10 if count <= 0 else min(count, 20)
        key = f"zhihu:global_search:{stable_hash(query)}:{normalized_count}"
        return self._cached(
            "global_search",
            key,
            lambda: mappers.map_search(
                self.live.data_get("/api/v1/content/global_search", {"Query": query, "Count": normalized_count})
                if self._live_enabled()
                else mock_data.global_search(query, normalized_count),
                "global_search",
            ),
        )

    def direct_answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model", "zhida-thinking-1p5")
        messages = payload.get("messages", [])
        stream = bool(payload.get("stream", False))
        if stream:
            raise ValueError("P0 only supports stream=false")
        key = f"zhihu:direct_answer:{model}:{stable_hash(json.dumps(messages, ensure_ascii=False, sort_keys=True))}:stream_false"
        result = self._cached(
            "direct_answer",
            key,
            lambda: mappers.map_direct_answer(
                self.live.data_post("/v1/chat/completions", payload) if self._live_enabled() else mock_data.direct_answer(model)
            ),
        )
        return {
            **result["items"],
            "cache": result["cache"],
            "quota": result["quota"],
        }

    def ring_detail(self, ring_id: str, page_num: int = 1, page_size: int = 20) -> dict[str, Any]:
        normalized_size = min(max(page_size, 1), 50)
        key = f"zhihu:ring_detail:{ring_id}:{page_num}:{normalized_size}"
        return self._cached(
            "ring_detail",
            key,
            lambda: mappers.map_ring_detail(
                self.live.community_get(
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
                self.live.community_get(
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
                self.live.community_get("/openapi/hackathon_story/list", {}) if self._live_enabled() else mock_data.story_list()
            ),
        )

    def story_detail(self, work_id: str) -> dict[str, Any]:
        key = f"zhihu:story_detail:{work_id}"
        return self._cached(
            "story_detail",
            key,
            lambda: mappers.map_story_detail(
                self.live.community_get("/openapi/hackathon_story/detail", {"work_id": work_id})
                if self._live_enabled()
                else mock_data.story_detail(work_id)
            ),
        )

    def following_feed(self) -> dict[str, Any]:
        key = f"zhihu:user_moments:{self.settings.demo_user_id}"
        return self._cached(
            "following_feed",
            key,
            lambda: mappers.map_following_feed(self.live.oauth_get("/user/moments") if self._live_enabled() else mock_data.following_feed()),
        )

    def user_followed(self, page: int = 0, per_page: int = 10) -> dict[str, Any]:
        key = f"zhihu:user_followed:{self.settings.demo_user_id}:{page}:{per_page}"
        items = [{"uid": 1, "hash_id": "mock-author", "fullname": "关注作者", "headline": "AI Coding 观察者"}]
        return self._cached(
            "user_followed",
            key,
            lambda: self.live.oauth_get("/user/followed", {"page": page, "per_page": per_page}) if self._live_enabled() else items,
        )

    def user_followers(self, page: int = 0, per_page: int = 10) -> dict[str, Any]:
        key = f"zhihu:user_followers:{self.settings.demo_user_id}:{page}:{per_page}"
        items = [{"uid": 2, "hash_id": "mock-reader", "fullname": "读者 A", "headline": "技术读者"}]
        return self._cached(
            "user_followers",
            key,
            lambda: self.live.oauth_get("/user/followers", {"page": page, "per_page": per_page}) if self._live_enabled() else items,
        )

    def publish_pin(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._live_enabled():
            return self.live.community_post("/openapi/publish/pin", payload)
        return {"mode": self.settings.provider_mode, "contentToken": "mock-pin-token", "request": payload}

    def create_comment(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._live_enabled():
            return self.live.community_post("/openapi/comment/create", payload)
        return {"mode": self.settings.provider_mode, "commentId": "mock-comment-id", "request": payload}

    def reaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._live_enabled():
            return self.live.community_post("/openapi/reaction", payload)
        return {"mode": self.settings.provider_mode, "success": True, "request": payload}
