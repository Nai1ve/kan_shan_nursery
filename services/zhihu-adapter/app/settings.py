import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider_mode: str = "mock"
    community_base_url: str = "https://openapi.zhihu.com"
    data_platform_base_url: str = "https://developer.zhihu.com"
    zhihu_app_key: str = ""
    zhihu_app_secret: str = ""
    zhihu_access_token: str = ""
    zhihu_access_secret: str = ""
    cache_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    demo_user_id: str = "demo-user"


def get_settings() -> Settings:
    return Settings(
        provider_mode=os.getenv("PROVIDER_MODE", os.getenv("ZHIHU_PROVIDER_MODE", "mock")),
        community_base_url=os.getenv("ZHIHU_COMMUNITY_BASE_URL", "https://openapi.zhihu.com"),
        data_platform_base_url=os.getenv("ZHIHU_DATA_PLATFORM_BASE_URL", "https://developer.zhihu.com"),
        zhihu_app_key=os.getenv("ZHIHU_APP_KEY", ""),
        zhihu_app_secret=os.getenv("ZHIHU_APP_SECRET", ""),
        zhihu_access_token=os.getenv("ZHIHU_ACCESS_TOKEN", ""),
        zhihu_access_secret=os.getenv("ZHIHU_ACCESS_SECRET", ""),
        cache_backend=os.getenv("ZHIHU_CACHE_BACKEND", "memory"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        demo_user_id=os.getenv("DEMO_USER_ID", "demo-user"),
    )
