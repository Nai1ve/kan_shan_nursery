from __future__ import annotations

from typing import Any


class GatewayError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500, detail: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ServiceNotReady(GatewayError):
    def __init__(self, service_name: str) -> None:
        super().__init__(
            "SERVICE_NOT_READY",
            f"Service is not ready: {service_name}",
            503,
            {"service": service_name},
        )


class DownstreamUnavailable(GatewayError):
    def __init__(self, service_name: str, reason: str) -> None:
        super().__init__(
            "DOWNSTREAM_UNAVAILABLE",
            f"Downstream service unavailable: {service_name}",
            502,
            {"service": service_name, "reason": reason},
        )


class DownstreamHttpError(GatewayError):
    def __init__(self, service_name: str, status_code: int, detail: Any) -> None:
        super().__init__(
            "DOWNSTREAM_ERROR",
            f"Downstream service returned error: {service_name}",
            status_code if 400 <= status_code < 600 else 502,
            {"service": service_name, "downstreamStatus": status_code, "downstreamDetail": detail},
        )
