from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import DownstreamClient, UrlLibDownstreamClient
from .errors import DownstreamHttpError, ServiceNotReady
from .settings import Settings, get_settings


@dataclass(frozen=True)
class ServiceTarget:
    name: str
    base_url: str
    ready: bool


class GatewayService:
    def __init__(self, settings: Settings | None = None, client: DownstreamClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or UrlLibDownstreamClient()
        self.targets = self._build_targets(self.settings)

    def health(self, request_id: str) -> dict[str, Any]:
        return self.success(
            request_id,
            {
                "status": "ok",
                "service": "api-gateway",
                "demoUserId": self.settings.demo_user_id,
                "downstream": {
                    name: {"baseUrl": target.base_url, "ready": target.ready}
                    for name, target in self.targets.items()
                },
            },
        )

    def proxy(
        self,
        request_id: str,
        service_name: str,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        target = self.targets[service_name]
        if not target.ready:
            raise ServiceNotReady(service_name)
        status_code, data = self.client.request(
            method,
            service_name,
            target.base_url,
            path,
            request_id,
            params,
            payload,
            self.settings.request_timeout_seconds,
            session_id,
        )
        if status_code >= 400:
            raise DownstreamHttpError(service_name, status_code, data)
        return self.success(request_id, data, {"service": service_name})

    def success(self, request_id: str, data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {"request_id": request_id, "data": data}
        if meta:
            response["meta"] = meta
        return response

    def _build_targets(self, settings: Settings) -> dict[str, ServiceTarget]:
        urls = {
            "profile": settings.profile_service_url,
            "content": settings.content_service_url,
            "seed": settings.seed_service_url,
            "sprout": settings.sprout_service_url,
            "writing": settings.writing_service_url,
            "feedback": settings.feedback_service_url,
            "zhihu": settings.zhihu_adapter_url,
            "llm": settings.llm_service_url,
        }
        return {
            name: ServiceTarget(name=name, base_url=url, ready=name in settings.ready_services)
            for name, url in urls.items()
        }
