import json
import time
import urllib.parse
import urllib.request
from typing import Any

from .security import sign_community_request
from .settings import Settings


class LiveClientError(Exception):
    pass


def _read_json(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:  # pragma: no cover - live path depends on network and credentials
        raise LiveClientError(str(error)) from error


class LiveZhihuClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def data_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.zhihu_access_secret:
            raise LiveClientError("ZHIHU_ACCESS_SECRET is required for Data Platform live mode")
        url = f"{self.settings.data_platform_base_url}{path}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.settings.zhihu_access_secret}",
                "X-Request-Timestamp": str(int(time.time())),
                "Content-Type": "application/json",
            },
            method="GET",
        )
        return _read_json(request)

    def data_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.zhihu_access_secret:
            raise LiveClientError("ZHIHU_ACCESS_SECRET is required for Data Platform live mode")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.data_platform_base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.zhihu_access_secret}",
                "X-Request-Timestamp": str(int(time.time())),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return _read_json(request)

    def community_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = self._community_headers()
        url = f"{self.settings.community_base_url}{path}?{urllib.parse.urlencode(params)}"
        return _read_json(urllib.request.Request(url, headers=headers, method="GET"))

    def community_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {**self._community_headers(), "Content-Type": "application/json"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(f"{self.settings.community_base_url}{path}", data=body, headers=headers, method="POST")
        return _read_json(request)

    def oauth_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.zhihu_access_token:
            raise LiveClientError("ZHIHU_ACCESS_TOKEN is required for OAuth live mode")
        query = urllib.parse.urlencode(params or {})
        suffix = f"?{query}" if query else ""
        request = urllib.request.Request(
            f"{self.settings.community_base_url}{path}{suffix}",
            headers={"Authorization": f"Bearer {self.settings.zhihu_access_token}"},
            method="GET",
        )
        return _read_json(request)

    def _community_headers(self) -> dict[str, str]:
        if not self.settings.zhihu_app_key or not self.settings.zhihu_app_secret:
            raise LiveClientError("ZHIHU_APP_KEY and ZHIHU_APP_SECRET are required for Community live mode")
        timestamp = str(int(time.time()))
        log_id = f"zhihu_adapter_{time.time_ns()}"
        return {
            "X-App-Key": self.settings.zhihu_app_key,
            "X-Timestamp": timestamp,
            "X-Log-Id": log_id,
            "X-Sign": sign_community_request(self.settings.zhihu_app_secret, self.settings.zhihu_app_key, timestamp, log_id, ""),
            "X-Extra-Info": "",
        }
