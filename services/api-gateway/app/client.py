from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from .errors import DownstreamUnavailable


class DownstreamClient(Protocol):
    def request(
        self,
        method: str,
        service_name: str,
        base_url: str,
        path: str,
        request_id: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 20,
    ) -> tuple[int, Any]:
        ...


class UrlLibDownstreamClient:
    def request(
        self,
        method: str,
        service_name: str,
        base_url: str,
        path: str,
        request_id: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 20,
    ) -> tuple[int, Any]:
        url = f"{base_url.rstrip('/')}{path}"
        query = urllib.parse.urlencode({key: value for key, value in (params or {}).items() if value is not None})
        if query:
            url = f"{url}?{query}"
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method=method.upper(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Request-Id": request_id,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.status, self._read_json(response.read())
        except urllib.error.HTTPError as error:
            return error.code, self._read_json(error.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise DownstreamUnavailable(service_name, str(exc)) from exc

    def _read_json(self, raw: bytes) -> Any:
        if not raw:
            return None
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
