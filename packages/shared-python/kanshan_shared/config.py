"""Layered config loader.

Precedence (lowest → highest):
  1. defaults baked into the dataclasses
  2. services/config.yaml (gitignored, holds credentials)
  3. environment variables (allow per-deploy overrides)

Resolution rules:
  - The yaml file may use either the recommended nested schema (see
    services/config.example.yaml) OR the legacy flat schema
    ``zhihu: { ZHIHU_APP_KEY: ... }``. Both produce the same dataclasses.
  - Missing yaml is fine; services should still be able to start in mock
    mode without any credentials on disk.
  - Empty strings in yaml are treated as "not set" and fall back to env
    or default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._yaml import parse_yaml


REPO_ROOT_HINTS = ("services", "packages", "docs", ".git")


@dataclass
class ZhihuCommunityConfig:
    app_key: str = ""
    app_secret: str = ""
    base_url: str = "https://openapi.zhihu.com"
    writable_ring_ids: tuple[str, ...] = ()
    default_ring_id: str = ""


@dataclass
class ZhihuOAuthConfig:
    app_id: str = ""
    app_key: str = ""
    redirect_uri: str = ""
    base_url: str = "https://openapi.zhihu.com"
    access_token: str = ""
    access_token_expires_at: int = 0


@dataclass
class ZhihuDataPlatformConfig:
    access_secret: str = ""
    base_url: str = "https://developer.zhihu.com"
    default_model: str = "zhida-thinking-1p5"


@dataclass
class ZhihuQuotaConfig:
    hot_list: int = 100
    zhihu_search: int = 1000
    global_search: int = 1000
    direct_answer: int = 100


@dataclass
class ZhihuConfig:
    community: ZhihuCommunityConfig = field(default_factory=ZhihuCommunityConfig)
    oauth: ZhihuOAuthConfig = field(default_factory=ZhihuOAuthConfig)
    data_platform: ZhihuDataPlatformConfig = field(default_factory=ZhihuDataPlatformConfig)
    quota: ZhihuQuotaConfig = field(default_factory=ZhihuQuotaConfig)


@dataclass
class CacheConfig:
    backend: str = "memory"
    redis_url: str = "redis://127.0.0.1:6379/0"


@dataclass
class LoggingConfig:
    jsonl_dir: str = "output/logs"
    console_level: str = "INFO"


@dataclass
class KanshanConfig:
    provider_mode: str = "mock"
    zhihu: ZhihuConfig = field(default_factory=ZhihuConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _find_repo_root(start: Path) -> Path:
    here = start.resolve()
    for candidate in [here, *here.parents]:
        if all((candidate / hint).exists() for hint in (".git",)):
            return candidate
        if (candidate / "services").exists() and (candidate / "packages").exists():
            return candidate
    return here


def _default_config_path() -> Path:
    explicit = os.getenv("KANSHAN_CONFIG_PATH")
    if explicit:
        return Path(explicit)
    return _find_repo_root(Path(__file__)) / "services" / "config.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return parse_yaml(path.read_text(encoding="utf-8"))


def _pick(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        return value
    return None


def _flat_legacy(zhihu_section: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Translate the legacy flat schema (zhihu: {ZHIHU_APP_KEY: ...})."""
    mapping = {
        "ZHIHU_APP_KEY": ("community", "app_key"),
        "ZHIHU_APP_SECRET": ("community", "app_secret"),
        "ZHIHU_ACCESS_TOKEN": ("oauth", "access_token"),
        "ZHIHU_ACCESS_SECRET": ("data_platform", "access_secret"),
    }
    out: dict[str, dict[str, Any]] = {"community": {}, "oauth": {}, "data_platform": {}, "quota": {}}
    for legacy_key, (section, field_name) in mapping.items():
        if legacy_key in zhihu_section and isinstance(zhihu_section[legacy_key], (str, int)):
            out[section][field_name] = zhihu_section[legacy_key]
    return out


def load_config(path: str | Path | None = None) -> KanshanConfig:
    cfg_path = Path(path) if path else _default_config_path()
    raw = _read_yaml(cfg_path)
    zhihu_raw = raw.get("zhihu") or {}

    legacy = _flat_legacy(zhihu_raw)
    community_raw = zhihu_raw.get("community") or legacy.get("community") or {}
    oauth_raw = zhihu_raw.get("oauth") or legacy.get("oauth") or {}
    data_raw = zhihu_raw.get("data_platform") or legacy.get("data_platform") or {}
    quota_raw = zhihu_raw.get("quota") or {}
    cache_raw = raw.get("cache") or {}
    logging_raw = raw.get("logging") or {}

    config = KanshanConfig(
        provider_mode=_pick(
            os.getenv("PROVIDER_MODE"),
            os.getenv("ZHIHU_PROVIDER_MODE"),
            raw.get("provider_mode"),
            "mock",
        ),
        zhihu=ZhihuConfig(
            community=ZhihuCommunityConfig(
                app_key=_pick(os.getenv("ZHIHU_APP_KEY"), community_raw.get("app_key"), "") or "",
                app_secret=_pick(os.getenv("ZHIHU_APP_SECRET"), community_raw.get("app_secret"), "") or "",
                base_url=_pick(
                    os.getenv("ZHIHU_COMMUNITY_BASE_URL"),
                    community_raw.get("base_url"),
                    "https://openapi.zhihu.com",
                ),
                writable_ring_ids=tuple(str(item) for item in (community_raw.get("writable_ring_ids") or [])),
                default_ring_id=_pick(
                    os.getenv("ZHIHU_DEFAULT_RING_ID"),
                    community_raw.get("default_ring_id"),
                    "",
                ) or "",
            ),
            oauth=ZhihuOAuthConfig(
                app_id=_pick(os.getenv("ZHIHU_OAUTH_APP_ID"), oauth_raw.get("app_id"), "") or "",
                app_key=_pick(os.getenv("ZHIHU_OAUTH_APP_KEY"), oauth_raw.get("app_key"), "") or "",
                redirect_uri=_pick(
                    os.getenv("ZHIHU_OAUTH_REDIRECT_URI"),
                    oauth_raw.get("redirect_uri"),
                    "",
                ) or "",
                base_url=_pick(
                    os.getenv("ZHIHU_OAUTH_BASE_URL"),
                    oauth_raw.get("base_url"),
                    "https://openapi.zhihu.com",
                ),
                access_token=_pick(
                    os.getenv("ZHIHU_ACCESS_TOKEN"),
                    oauth_raw.get("access_token"),
                    "",
                ) or "",
                access_token_expires_at=int(
                    _pick(
                        os.getenv("ZHIHU_ACCESS_TOKEN_EXPIRES_AT"),
                        oauth_raw.get("access_token_expires_at"),
                        0,
                    )
                    or 0
                ),
            ),
            data_platform=ZhihuDataPlatformConfig(
                access_secret=_pick(
                    os.getenv("ZHIHU_ACCESS_SECRET"),
                    data_raw.get("access_secret"),
                    "",
                ) or "",
                base_url=_pick(
                    os.getenv("ZHIHU_DATA_PLATFORM_BASE_URL"),
                    data_raw.get("base_url"),
                    "https://developer.zhihu.com",
                ),
                default_model=_pick(
                    os.getenv("LLM_DEFAULT_MODEL"),
                    data_raw.get("default_model"),
                    "zhida-thinking-1p5",
                ),
            ),
            quota=ZhihuQuotaConfig(
                hot_list=int(_pick(os.getenv("ZHIHU_QUOTA_HOT_LIST"), quota_raw.get("hot_list"), 100) or 100),
                zhihu_search=int(
                    _pick(os.getenv("ZHIHU_QUOTA_ZHIHU_SEARCH"), quota_raw.get("zhihu_search"), 1000) or 1000
                ),
                global_search=int(
                    _pick(os.getenv("ZHIHU_QUOTA_GLOBAL_SEARCH"), quota_raw.get("global_search"), 1000) or 1000
                ),
                direct_answer=int(
                    _pick(os.getenv("ZHIHU_QUOTA_DIRECT_ANSWER"), quota_raw.get("direct_answer"), 100) or 100
                ),
            ),
        ),
        cache=CacheConfig(
            backend=_pick(
                os.getenv("ZHIHU_CACHE_BACKEND"),
                os.getenv("LLM_CACHE_BACKEND"),
                cache_raw.get("backend"),
                "memory",
            ),
            redis_url=_pick(os.getenv("REDIS_URL"), cache_raw.get("redis_url"), "redis://127.0.0.1:6379/0"),
        ),
        logging=LoggingConfig(
            jsonl_dir=_pick(
                os.getenv("KANSHAN_LOG_DIR"),
                logging_raw.get("jsonl_dir"),
                "output/logs",
            ),
            console_level=_pick(
                os.getenv("KANSHAN_LOG_LEVEL"),
                logging_raw.get("console_level"),
                "INFO",
            ),
        ),
    )
    return config
