from __future__ import annotations

import os
from dataclasses import dataclass

from kanshan_shared import load_config

_config = load_config()


def _ready_services() -> set[str]:
    raw = os.getenv(
        "GATEWAY_READY_SERVICES",
        "profile,seed,zhihu,llm,content,sprout,writing,feedback",
    )
    return {item.strip() for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    profile_service_url: str = _config.service_urls.profile
    content_service_url: str = _config.service_urls.content
    seed_service_url: str = _config.service_urls.seed
    sprout_service_url: str = _config.service_urls.sprout
    writing_service_url: str = _config.service_urls.writing
    feedback_service_url: str = _config.service_urls.feedback
    zhihu_adapter_url: str = _config.service_urls.zhihu
    llm_service_url: str = _config.service_urls.llm
    request_timeout_seconds: float = float(os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "20"))
    demo_user_id: str = os.getenv("DEMO_USER_ID", "demo-user")
    ready_services: frozenset[str] = frozenset(_ready_services())


def get_settings() -> Settings:
    return Settings()
