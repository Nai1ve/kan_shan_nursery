"""HTTP client for calling zhihu-adapter service."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.content.zhihu_client")


class ZhihuClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8070") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        safe_params = {}
        if params:
            clean_params = {k: v for k, v in params.items() if v}
            safe_params = {
                key: "***" if "token" in key.lower() else value
                for key, value in clean_params.items()
            }
            encoded = urllib.parse.urlencode(clean_params)
            if encoded:
                url = f"{url}?{encoded}"
        logger.debug("zhihu_client_request", extra={"method": "GET", "path": path, "params": safe_params})
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logger.debug("zhihu_client_response", extra={
                "url": path,
                "status": resp.status,
                "hasItems": bool(data.get("items")),
            })
            return data

    def hot_list(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get Zhihu hot list items."""
        logger.info("zhihu_client_hot_list", extra={"limit": limit})
        try:
            result = self._get("/zhihu/hot-list", {"limit": str(limit)})
            items = result.get("items", [])
            logger.info("zhihu_client_hot_list_result", extra={
                "itemCount": len(items),
                "titles": [it.get("title", "")[:30] for it in items[:3]],
            })
            return items
        except Exception as e:
            logger.warning("zhihu_client_hot_list_failed", extra={"error": str(e)})
            return []

    def search(self, query: str, count: int = 10) -> list[dict[str, Any]]:
        """Search Zhihu for content matching query."""
        logger.info("zhihu_client_search", extra={"query": query, "count": count})
        try:
            result = self._get("/zhihu/zhihu-search", {"query": query, "count": str(count)})
            items = result.get("items", [])
            logger.info("zhihu_client_search_result", extra={
                "query": query,
                "itemCount": len(items),
                "titles": [it.get("title", "")[:30] for it in items[:3]],
            })
            return items
        except Exception as e:
            logger.warning("zhihu_client_search_failed", extra={"query": query, "error": str(e)})
            return []

    def global_search(self, query: str, count: int = 10) -> list[dict[str, Any]]:
        """Search the web through zhihu-adapter global_search."""
        logger.info("zhihu_client_global_search", extra={"query": query, "count": count})
        try:
            result = self._get("/zhihu/global-search", {"query": query, "count": str(count)})
            items = result.get("items", [])
            logger.info("zhihu_client_global_search_result", extra={
                "query": query,
                "itemCount": len(items),
                "titles": [it.get("title", "")[:30] for it in items[:3]],
            })
            return items
        except Exception as e:
            logger.warning("zhihu_client_global_search_failed", extra={"query": query, "error": str(e)})
            return []

    def following_feed(self, access_token: str | None = None) -> list[dict[str, Any]]:
        """Get following feed items from zhihu-adapter."""
        logger.info("zhihu_client_following_feed")
        try:
            result = self._get("/zhihu/following-feed", {"access_token": access_token})
            items = result.get("items", [])
            logger.info("zhihu_client_following_feed_result", extra={"itemCount": len(items)})
            return items
        except Exception as e:
            logger.warning("zhihu_client_following_feed_failed", extra={"error": str(e)})
            return []

    def user_followed(self, access_token: str) -> list[dict[str, Any]]:
        """Get user's followed list from zhihu-adapter."""
        logger.info("zhihu_client_user_followed")
        try:
            result = self._get("/zhihu/user-followed", {"access_token": access_token})
            items = result.get("items", [])
            logger.info("zhihu_client_user_followed_result", extra={"itemCount": len(items)})
            return items
        except Exception as e:
            logger.warning("zhihu_client_user_followed_failed", extra={"error": str(e)})
            return []
