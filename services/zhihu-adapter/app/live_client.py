"""HTTP transport for the three Zhihu sub-platforms.

We split what used to be one ``LiveZhihuClient`` into three classes so
each one can carry its own auth headers, base URL and error normalisation
without if-branches scattered across ``service.py``.

  - CommunityClient     (HMAC signed, openapi.zhihu.com)
  - OAuthClient         (Bearer access_token, openapi.zhihu.com)
  - DataPlatformClient  (Bearer access_secret, developer.zhihu.com)

The adapter always raises typed exceptions from ``errors.py``; the
business layer never sees urllib.HTTPError directly.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .errors import (
    ZhihuApiError,
    ZhihuAuthError,
    ZhihuRateLimited,
    ZhihuUnavailable,
    from_community,
    from_data_platform,
    from_oauth,
)
from .security import sign_community_request
from .settings import Settings


logger = logging.getLogger("kanshan.zhihu.live")


class _Transport:
    timeout_seconds: float = 15

    def _do(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            body = ""
            try:
                body = error.read().decode("utf-8")
            except Exception:  # pragma: no cover
                pass
            if error.code in (401, 403):
                raise ZhihuAuthError(f"upstream auth failed: {error.code}", detail={"body": body}) from error
            if error.code == 429:
                raise ZhihuRateLimited("upstream rate limited", detail={"body": body}) from error
            raise ZhihuApiError(f"upstream {error.code}", detail={"body": body}) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ZhihuUnavailable(f"network: {error}", detail=None) from error

        try:
            return json.loads(payload)
        except json.JSONDecodeError as error:
            raise ZhihuApiError("invalid json from upstream", detail={"body": payload[:512]}) from error


class CommunityClient(_Transport):
    """openapi.zhihu.com signed by HMAC-SHA256."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_credentials()
        url = self._url(path, params or {})
        request = urllib.request.Request(url, headers=self._signed_headers(), method="GET")
        raw = self._do(request)
        error = from_community(raw)
        if error:
            raise error
        return raw

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_credentials()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.zhihu.community.base_url}{path}",
            data=body,
            headers={**self._signed_headers(), "Content-Type": "application/json"},
            method="POST",
        )
        raw = self._do(request)
        error = from_community(raw)
        if error:
            raise error
        return raw

    def _url(self, path: str, params: dict[str, Any]) -> str:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        suffix = f"?{query}" if query else ""
        return f"{self.settings.zhihu.community.base_url}{path}{suffix}"

    def _signed_headers(self) -> dict[str, str]:
        community = self.settings.zhihu.community
        timestamp = str(int(time.time()))
        log_id = f"zhihu_adapter_{time.time_ns()}"
        return {
            "X-App-Key": community.app_key,
            "X-Timestamp": timestamp,
            "X-Log-Id": log_id,
            "X-Sign": sign_community_request(community.app_secret, community.app_key, timestamp, log_id, ""),
            "X-Extra-Info": "",
        }

    def _require_credentials(self) -> None:
        community = self.settings.zhihu.community
        if not community.app_key or not community.app_secret:
            raise ZhihuAuthError("Community app_key/app_secret missing")


class OAuthClient(_Transport):
    """openapi.zhihu.com authenticated with a Bearer access_token."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_token()
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        suffix = f"?{query}" if query else ""
        request = urllib.request.Request(
            f"{self.settings.zhihu.oauth.base_url}{path}{suffix}",
            headers={"Authorization": f"Bearer {self.settings.zhihu.oauth.access_token}"},
            method="GET",
        )
        raw = self._do(request)
        error = from_oauth(raw)
        if error:
            raise error
        return raw

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        oauth = self.settings.zhihu.oauth
        if not (oauth.app_id and oauth.app_key and oauth.redirect_uri):
            raise ZhihuAuthError("OAuth app_id/app_key/redirect_uri missing")
        body = urllib.parse.urlencode(
            {
                "app_id": oauth.app_id,
                "app_key": oauth.app_key,
                "grant_type": "authorization_code",
                "redirect_uri": oauth.redirect_uri,
                "code": code,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{oauth.base_url}/access_token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        raw = self._do(request)
        if "access_token" not in raw:
            error = from_oauth(raw) or ZhihuApiError("OAuth exchange returned no access_token", detail=raw)
            raise error
        return raw

    def authorize_url(self) -> str:
        oauth = self.settings.zhihu.oauth
        params = urllib.parse.urlencode(
            {
                "redirect_uri": oauth.redirect_uri,
                "app_id": oauth.app_id,
                "response_type": "code",
            }
        )
        return f"{oauth.base_url}/authorize?{params}"

    def _require_token(self) -> None:
        if not self.settings.zhihu.oauth.access_token:
            raise ZhihuAuthError("OAuth access_token missing; visit /zhihu/oauth/authorize first")


class DataPlatformClient(_Transport):
    """developer.zhihu.com authenticated with the data platform Bearer secret."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_secret()
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        suffix = f"?{query}" if query else ""
        request = urllib.request.Request(
            f"{self.settings.zhihu.data_platform.base_url}{path}{suffix}",
            headers=self._headers(),
            method="GET",
        )
        raw = self._do(request)
        error = from_data_platform(raw)
        if error:
            raise error
        return raw

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_secret()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.zhihu.data_platform.base_url}{path}",
            data=body,
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        raw = self._do(request)
        # /v1/chat/completions is OpenAI-compatible: success has no Code key,
        # only the choices array; treat presence of an explicit error envelope
        # as failure.
        if isinstance(raw, dict) and isinstance(raw.get("error"), dict):
            err = raw["error"]
            raise ZhihuApiError(err.get("message", "data platform error"), detail=err)
        error = from_data_platform(raw)
        if error:
            raise error
        return raw

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.zhihu.data_platform.access_secret}",
            "X-Request-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

    def _require_secret(self) -> None:
        if not self.settings.zhihu.data_platform.access_secret:
            raise ZhihuAuthError("Data Platform access_secret missing")


class ClientBundle:
    """Convenience facade so service.py needs only one collaborator."""

    def __init__(self, settings: Settings) -> None:
        self.community = CommunityClient(settings)
        self.oauth = OAuthClient(settings)
        self.data_platform = DataPlatformClient(settings)


# Legacy alias kept while we update tests and call sites in this commit.
LiveZhihuClient = ClientBundle
