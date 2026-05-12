"""HTTP client for calling zhihu-adapter service."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


class ZhihuClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8070") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            encoded = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            if encoded:
                url = f"{url}?{encoded}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def hot_list(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get Zhihu hot list items."""
        try:
            result = self._get("/zhihu/hot-list", {"limit": str(limit)})
            return result.get("items", [])
        except Exception:
            return []

    def search(self, query: str, count: int = 10) -> list[dict[str, Any]]:
        """Search Zhihu for content matching query."""
        try:
            result = self._get("/zhihu/zhihu-search", {"query": query, "count": str(count)})
            return result.get("items", [])
        except Exception:
            return []
