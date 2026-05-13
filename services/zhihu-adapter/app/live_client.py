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
from .security import sign_community_request, stable_hash
from .settings import Settings


logger = logging.getLogger("kanshan.zhihu.live")


class _Transport:
    timeout_seconds: float = 15

    def _do(self, request: urllib.request.Request) -> Any:
        started = time.perf_counter()
        parsed = urllib.parse.urlparse(request.full_url)
        query_keys = sorted(list(urllib.parse.parse_qs(parsed.query).keys()))
        body_keys: list[str] = []
        if request.data:
            try:
                text = request.data.decode("utf-8")
                body_keys = sorted(list(urllib.parse.parse_qs(text).keys()))
                if not body_keys:
                    parsed_json = json.loads(text)
                    if isinstance(parsed_json, dict):
                        body_keys = sorted(list(parsed_json.keys()))
            except Exception:
                body_keys = []

        logger.info(
            "zhihu_upstream_request",
            extra={
                "method": request.get_method(),
                "path": parsed.path,
                "queryKeys": query_keys,
                "bodyKeys": body_keys,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "zhihu_upstream_response",
                    extra={
                        "method": request.get_method(),
                        "path": parsed.path,
                        "status": response.status,
                        "durationMs": duration_ms,
                    },
                )
        except urllib.error.HTTPError as error:
            body = ""
            try:
                body = error.read().decode("utf-8")
            except Exception:  # pragma: no cover
                pass
            duration_ms = int((time.perf_counter() - started) * 1000)
            detail_keys: list[str] = []
            try:
                parsed_error = json.loads(body)
                if isinstance(parsed_error, dict):
                    detail_keys = sorted(list(parsed_error.keys()))
            except Exception:
                detail_keys = []
            logger.warning(
                "zhihu_upstream_http_error",
                extra={
                    "method": request.get_method(),
                    "path": parsed.path,
                    "status": error.code,
                    "durationMs": duration_ms,
                    "errorBodyKeys": detail_keys,
                },
            )
            if error.code in (401, 403):
                raise ZhihuAuthError(f"upstream auth failed: {error.code}", detail={"body": body}) from error
            if error.code == 429:
                raise ZhihuRateLimited("upstream rate limited", detail={"body": body}) from error
            raise ZhihuApiError(f"upstream {error.code}", detail={"body": body}) from error
        except (urllib.error.URLError, TimeoutError) as error:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "zhihu_upstream_network_error",
                extra={"method": request.get_method(), "path": parsed.path, "durationMs": duration_ms, "error": str(error)},
            )
            raise ZhihuUnavailable(f"network: {error}", detail=None) from error

        try:
            parsed_payload = json.loads(payload)
            top_level_keys = sorted(list(parsed_payload.keys())) if isinstance(parsed_payload, dict) else []
            logger.info(
                "zhihu_upstream_payload",
                extra={
                    "method": request.get_method(),
                    "path": parsed.path,
                    "responseTopLevelKeys": top_level_keys,
                    "responseType": type(parsed_payload).__name__,
                },
            )
            return parsed_payload
        except json.JSONDecodeError as error:
            logger.warning(
                "zhihu_upstream_invalid_json",
                extra={"method": request.get_method(), "path": parsed.path, "payloadPrefix": payload[:120]},
            )
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

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> Any:
        token = self._resolve_token(access_token)
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        suffix = f"?{query}" if query else ""
        logger.info(
            "zhihu_oauth_get_prepare",
            extra={
                "path": path,
                "queryKeys": sorted(list((params or {}).keys())),
                "hasAccessToken": bool(token),
                "tokenHash": stable_hash(token) if token else None,
            },
        )
        request = urllib.request.Request(
            f"{self.settings.zhihu.oauth.base_url}{path}{suffix}",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        raw = self._do(request)
        # OAuth list endpoints such as /user/followed and /user/followers
        # return a bare JSON array on success. Only dict responses can carry
        # the documented {code, data} error envelope.
        if isinstance(raw, dict):
            error = from_oauth(raw)
            if error:
                raise error
        return raw

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        oauth = self.settings.zhihu.oauth
        if not (oauth.app_id and oauth.app_key and oauth.redirect_uri):
            raise ZhihuAuthError("OAuth app_id/app_key/redirect_uri missing")
        logger.info(
            "zhihu_oauth_exchange_prepare",
            extra={
                "path": "/access_token",
                "hasCode": bool(code),
                "codeHash": stable_hash(code) if code else None,
                "hasAppId": bool(oauth.app_id),
                "hasAppKey": bool(oauth.app_key),
            },
        )
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

    def authorize_url(self, state: str | None = None) -> str:
        oauth = self.settings.zhihu.oauth
        payload = {
            "redirect_uri": oauth.redirect_uri,
            "app_id": oauth.app_id,
            "response_type": "code",
        }
        if state:
            payload["state"] = state
        params = urllib.parse.urlencode(payload)
        return f"{oauth.base_url}/authorize?{params}"

    def _resolve_token(self, access_token: str | None = None) -> str:
        token = access_token or self.settings.zhihu.oauth.access_token
        if not token:
            raise ZhihuAuthError("OAuth access_token missing; visit /zhihu/oauth/authorize first")
        return token

    def _require_token(self) -> None:
        self._resolve_token()


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
