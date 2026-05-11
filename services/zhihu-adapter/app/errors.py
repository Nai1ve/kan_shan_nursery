"""Structured Zhihu API errors.

The adapter exposes uniform HTTP semantics regardless of which Zhihu
sub-platform raised the error:

  - ZHIHU_AUTH_FAILED   -> 401 (Community status=1+code=101 / OAuth code=401 / Data 20001)
  - ZHIHU_RATE_LIMITED  -> 429 (Community 429 / Data 30001 / local quota)
  - ZHIHU_INVALID_REQUEST -> 400 (Data 10001 / Community param errors)
  - ZHIHU_RING_NOT_WRITABLE -> 400 (local guard; ring_id not in writable list)
  - ZHIHU_UPSTREAM_ERROR -> 502 (Data 90001 / 5xx / unknown)
  - ZHIHU_UNAVAILABLE    -> 502 (network / timeout)
"""

from __future__ import annotations

from typing import Any


class ZhihuApiError(Exception):
    code: str = "ZHIHU_UPSTREAM_ERROR"
    http_status: int = 502

    def __init__(self, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class ZhihuAuthError(ZhihuApiError):
    code = "ZHIHU_AUTH_FAILED"
    http_status = 401


class ZhihuRateLimited(ZhihuApiError):
    code = "ZHIHU_RATE_LIMITED"
    http_status = 429


class ZhihuInvalidRequest(ZhihuApiError):
    code = "ZHIHU_INVALID_REQUEST"
    http_status = 400


class ZhihuRingNotWritable(ZhihuApiError):
    code = "ZHIHU_RING_NOT_WRITABLE"
    http_status = 400


class ZhihuUnavailable(ZhihuApiError):
    code = "ZHIHU_UNAVAILABLE"
    http_status = 502


class QuotaExceeded(ZhihuRateLimited):
    """Local daily quota exhausted before any upstream call."""

    def __init__(self, endpoint: str, limit: int) -> None:
        super().__init__(f"{endpoint} quota exceeded: {limit}/day", detail={"endpoint": endpoint, "limit": limit})
        self.endpoint = endpoint
        self.limit = limit


def from_community(raw: dict[str, Any]) -> ZhihuApiError | None:
    """Translate a Community/OAuth response envelope into an error if any.

    Returns None when status/code is 0 (success). Used by the clients so
    business code only sees structured exceptions.
    """
    if not isinstance(raw, dict):
        return ZhihuApiError("Unexpected community response", detail={"raw": raw})
    status = raw.get("status", raw.get("code", 0))
    if status in (0, "0"):
        return None
    msg = raw.get("msg") or raw.get("message") or "community api error"
    if status in (101, "101"):
        return ZhihuAuthError(msg, detail=raw)
    return ZhihuApiError(msg, detail=raw)


def from_oauth(raw: dict[str, Any]) -> ZhihuApiError | None:
    if not isinstance(raw, dict):
        return ZhihuApiError("Unexpected OAuth response", detail={"raw": raw})
    code = raw.get("code")
    if code in (None, 0, "0"):
        return None
    msg = raw.get("data") or raw.get("message") or "oauth api error"
    if code in (401, "401"):
        return ZhihuAuthError(msg, detail=raw)
    if code in (403, "403"):
        return ZhihuAuthError(msg, detail=raw)
    if code in (404, "404"):
        return ZhihuInvalidRequest(msg, detail=raw)
    return ZhihuApiError(msg, detail=raw)


def from_data_platform(raw: dict[str, Any]) -> ZhihuApiError | None:
    if not isinstance(raw, dict):
        return ZhihuApiError("Unexpected data platform response", detail={"raw": raw})
    code = raw.get("Code", raw.get("code", 0))
    if code in (0, "0"):
        return None
    msg = raw.get("Message") or raw.get("message") or "data platform error"
    if code in (10001, "10001"):
        return ZhihuInvalidRequest(msg, detail=raw)
    if code in (20001, "20001"):
        return ZhihuAuthError(msg, detail=raw)
    if code in (30001, "30001"):
        return ZhihuRateLimited(msg, detail=raw)
    return ZhihuApiError(msg, detail=raw)
