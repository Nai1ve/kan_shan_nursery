"""Cross-service HTTP clients for sprout-service.

Each method is independently fail-safe, returning empty defaults on error.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger("kanshan.sprout.data_fetcher")


class SproutDataFetcher:
    """Fetches seeds, cards, and memory from other kanshan services."""

    def __init__(self, service_urls: Any) -> None:
        """Accepts a ServiceUrlsConfig or any object with .seed, .content, .profile attributes."""
        self._seed_url = getattr(service_urls, "seed", "http://127.0.0.1:8030")
        self._content_url = getattr(service_urls, "content", "http://127.0.0.1:8020")
        self._profile_url = getattr(service_urls, "profile", "http://127.0.0.1:8010")

    def _get(
        self,
        base_url: str,
        path: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 8,
    ) -> dict[str, Any]:
        """HTTP GET with JSON response. Raises on error."""
        url = f"{base_url.rstrip('/')}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v)
            if qs:
                url = f"{url}?{qs}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _extract_items(self, data: dict[str, Any]) -> list[dict]:
        """Extract items list from response envelope or direct response."""
        # Gateway envelope: {request_id, data: {items: [...]}}
        inner = data.get("data", data)
        if isinstance(inner, dict):
            items = inner.get("items")
            if isinstance(items, list):
                return items
            # Some endpoints return data directly as a list
            return []
        if isinstance(inner, list):
            return inner
        return []

    def _extract_dict(self, data: dict[str, Any]) -> dict:
        """Extract dict from response envelope."""
        inner = data.get("data", data)
        return inner if isinstance(inner, dict) else {}

    # ------------------------------------------------------------------
    # Individual fetchers
    # ------------------------------------------------------------------

    def fetch_seeds(self, user_id: str) -> list[dict]:
        """GET /seeds?user_id=X from seed-service."""
        try:
            data = self._get(self._seed_url, "/seeds", {"user_id": user_id})
            items = self._extract_items(data)
            logger.info("fetch_seeds_ok", extra={"userId": user_id, "count": len(items)})
            return items
        except Exception as e:
            logger.warning("fetch_seeds_failed", extra={"userId": user_id, "error": str(e)})
            return []

    def fetch_hot_cards(self, limit: int = 10) -> list[dict]:
        """GET /content/cards?limit=N from content-service (system cache, no auth)."""
        try:
            data = self._get(self._content_url, "/content/cards", {"limit": str(limit)})
            items = self._extract_items(data)
            logger.info("fetch_hot_cards_ok", extra={"count": len(items)})
            return items
        except Exception as e:
            logger.warning("fetch_hot_cards_failed", extra={"error": str(e)})
            return []

    def fetch_today_cards(self, user_id: str, limit: int = 10) -> list[dict]:
        """GET /content/cards?user_id=X&limit=N from content-service."""
        try:
            data = self._get(
                self._content_url,
                "/content/cards",
                {"user_id": user_id, "limit": str(limit)},
            )
            items = self._extract_items(data)
            logger.info("fetch_today_cards_ok", extra={"userId": user_id, "count": len(items)})
            return items
        except Exception as e:
            logger.warning("fetch_today_cards_failed", extra={"userId": user_id, "error": str(e)})
            return []

    def fetch_memory(self, session_id: str) -> dict:
        """GET /memory/me from profile-service with x-session-id header."""
        if not session_id:
            return {}
        try:
            data = self._get(
                self._profile_url,
                "/memory/me",
                headers={"x-session-id": session_id},
            )
            result = self._extract_dict(data)
            logger.info("fetch_memory_ok")
            return result
        except Exception as e:
            logger.warning("fetch_memory_failed", extra={"error": str(e)})
            return {}

    # ------------------------------------------------------------------
    # Parallel fetch
    # ------------------------------------------------------------------

    def fetch_all(
        self,
        user_id: str,
        session_id: str | None = None,
        hot_limit: int = 10,
        today_limit: int = 10,
    ) -> dict[str, Any]:
        """Fetch all data in parallel. Returns SproutInput-shaped dict."""
        result: dict[str, Any] = {
            "seeds": [],
            "hotCards": [],
            "todayCards": [],
            "memory": {},
        }

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self.fetch_seeds, user_id): "seeds",
                pool.submit(self.fetch_hot_cards, hot_limit): "hotCards",
                pool.submit(self.fetch_today_cards, user_id, today_limit): "todayCards",
            }
            if session_id:
                futures[pool.submit(self.fetch_memory, session_id)] = "memory"

            for future in as_completed(futures, timeout=10):
                key = futures[future]
                try:
                    result[key] = future.result()
                except Exception as e:
                    logger.warning("fetch_all_task_failed", extra={"key": key, "error": str(e)})

        return result
