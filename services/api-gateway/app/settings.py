from __future__ import annotations

import os
from dataclasses import dataclass


def _ready_services() -> set[str]:
    raw = os.getenv(
        "GATEWAY_READY_SERVICES",
        "profile,seed,zhihu,llm,content,sprout,writing,feedback",
    )
    return {item.strip() for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    profile_service_url: str = "http://127.0.0.1:8010"
    content_service_url: str = "http://127.0.0.1:8020"
    seed_service_url: str = "http://127.0.0.1:8030"
    sprout_service_url: str = "http://127.0.0.1:8040"
    writing_service_url: str = "http://127.0.0.1:8050"
    feedback_service_url: str = "http://127.0.0.1:8060"
    zhihu_adapter_url: str = "http://127.0.0.1:8070"
    llm_service_url: str = "http://127.0.0.1:8080"
    request_timeout_seconds: float = 20
    demo_user_id: str = "demo-user"
    ready_services: frozenset[str] = frozenset(
        {"profile", "seed", "zhihu", "llm", "content", "sprout", "writing", "feedback"}
    )


def get_settings() -> Settings:
    return Settings(
        profile_service_url=os.getenv("PROFILE_SERVICE_URL", "http://127.0.0.1:8010"),
        content_service_url=os.getenv("CONTENT_SERVICE_URL", "http://127.0.0.1:8020"),
        seed_service_url=os.getenv("SEED_SERVICE_URL", "http://127.0.0.1:8030"),
        sprout_service_url=os.getenv("SPROUT_SERVICE_URL", "http://127.0.0.1:8040"),
        writing_service_url=os.getenv("WRITING_SERVICE_URL", "http://127.0.0.1:8050"),
        feedback_service_url=os.getenv("FEEDBACK_SERVICE_URL", "http://127.0.0.1:8060"),
        zhihu_adapter_url=os.getenv("ZHIHU_ADAPTER_URL", "http://127.0.0.1:8070"),
        llm_service_url=os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:8080"),
        request_timeout_seconds=float(os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "20")),
        demo_user_id=os.getenv("DEMO_USER_ID", "demo-user"),
        ready_services=frozenset(_ready_services()),
    )
