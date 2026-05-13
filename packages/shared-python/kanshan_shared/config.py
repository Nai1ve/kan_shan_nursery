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

try:
    import yaml  # PyYAML
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "PyYAML is required. Install with `pip install PyYAML` "
        "(or run pip install -r services/<svc>/requirements.txt)."
    ) from exc


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
class ServiceUrlsConfig:
    """Inter-service URLs for gateway and content service."""
    profile: str = "http://127.0.0.1:8010"
    content: str = "http://127.0.0.1:8020"
    seed: str = "http://127.0.0.1:8030"
    sprout: str = "http://127.0.0.1:8040"
    writing: str = "http://127.0.0.1:8050"
    feedback: str = "http://127.0.0.1:8060"
    zhihu: str = "http://127.0.0.1:8070"
    llm: str = "http://127.0.0.1:8080"


@dataclass
class LLMQuotaConfig:
    """Per-task-type daily quota limits for LLM usage."""
    summarize_content: int = 50
    answer_seed_question: int = 30
    supplement_material: int = 30
    sprout_opportunities: int = 20
    argument_blueprint: int = 15
    generate_outline: int = 15
    draft: int = 10
    roundtable_review: int = 10
    feedback_summary: int = 10
    profile_memory_synthesis: int = 5
    extract_controversies: int = 20
    generate_writing_angles: int = 20


@dataclass
class LLMConfig:
    """LLM service specific config."""
    provider_mode: str = "mock"
    default_model: str = "zhida-thinking-1p5"
    prompt_version: str = "v1"
    schema_version: str = "v1"
    cache_backend: str = "memory"
    cache_ttl_seconds: int = 21600
    request_timeout_seconds: int = 20
    trace_dir: str = "output/llm-trace"
    trace_enabled: bool = True
    quota: LLMQuotaConfig = field(default_factory=LLMQuotaConfig)


@dataclass
class OpenAICompatConfig:
    """OpenAI-compatible API config."""
    base_url: str = ""
    api_key: str = ""
    model: str = "gpt-4o-mini"


@dataclass
class KanshanConfig:
    provider_mode: str = "mock"
    database_url: str = "postgresql+psycopg://kanshan:kanshan_dev_password@127.0.0.1:5432/kanshan"
    storage_backend: str = "memory"
    cors_origins: list[str] = field(default_factory=lambda: ["http://127.0.0.1:3000", "http://localhost:3000"])
    zhihu: ZhihuConfig = field(default_factory=ZhihuConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    service_urls: ServiceUrlsConfig = field(default_factory=ServiceUrlsConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    openai_compat: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)


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
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping, got {type(data).__name__}")
    return data


def _pick(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        return value
    return None


def _get_any(mapping: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for any accepted config key.

    The official docs and local notes have used a few naming styles over
    time (`access_secret`, `accessSecret`, `access-secret`). Accepting the
    aliases here keeps `services/config.yaml` forgiving without leaking that
    tolerance into each service.
    """
    return _pick(*(mapping.get(key) for key in keys))


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


def _build_llm_quota(raw: Any) -> LLMQuotaConfig:
    if not raw or not isinstance(raw, dict):
        return LLMQuotaConfig()
    defaults = LLMQuotaConfig()
    kwargs: dict[str, int] = {}
    for field_name in defaults.__dataclass_fields__:
        if field_name in raw:
            kwargs[field_name] = int(raw[field_name] or getattr(defaults, field_name))
    return LLMQuotaConfig(**kwargs)


def _parse_cors_origins(env_value: str | None, yaml_value: Any) -> list[str]:
    """Parse CORS origins from env var (comma-separated) or YAML (list)."""
    defaults = ["http://127.0.0.1:3000", "http://localhost:3000"]
    if env_value:
        return [o.strip() for o in env_value.split(",") if o.strip()]
    if yaml_value and isinstance(yaml_value, list):
        return [str(o) for o in yaml_value]
    return defaults


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
    service_urls_raw = raw.get("service_urls") or {}
    llm_raw = raw.get("llm") or {}
    openai_compat_raw = raw.get("openai_compat") or {}

    config = KanshanConfig(
        provider_mode=_pick(
            os.getenv("PROVIDER_MODE"),
            os.getenv("ZHIHU_PROVIDER_MODE"),
            raw.get("provider_mode"),
            "mock",
        ),
        database_url=_pick(
            os.getenv("DATABASE_URL"),
            raw.get("database_url"),
            "postgresql+psycopg://kanshan:kanshan_dev_password@127.0.0.1:5432/kanshan",
        ),
        storage_backend=_pick(
            os.getenv("STORAGE_BACKEND"),
            raw.get("storage_backend"),
            "memory",
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
                    _get_any(data_raw, "access_secret", "accessSecret", "access-secret", "secret"),
                    "",
                ) or "",
                base_url=_pick(
                    os.getenv("ZHIHU_DATA_PLATFORM_BASE_URL"),
                    _get_any(data_raw, "base_url", "baseUrl", "base-url"),
                    "https://developer.zhihu.com",
                ),
                default_model=_pick(
                    os.getenv("LLM_DEFAULT_MODEL"),
                    _get_any(data_raw, "default_model", "defaultModel", "default-model"),
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
        cors_origins=_parse_cors_origins(
            os.getenv("CORS_ORIGINS"),
            raw.get("cors_origins"),
        ),
        cache=CacheConfig(
            backend=_pick(
                os.getenv("ZHIHU_CACHE_BACKEND"),
                os.getenv("LLM_CACHE_BACKEND"),
                cache_raw.get("backend"),
                # When deployed in Docker the yaml is not always mounted, but
                # REDIS_URL is always set by compose. Promote to ``redis`` in
                # that case so zhihu-adapter / llm-service stop silently
                # falling back to in-memory caching.
                "redis" if os.getenv("REDIS_URL") else "memory",
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
        service_urls=ServiceUrlsConfig(
            profile=_pick(os.getenv("PROFILE_SERVICE_URL"), service_urls_raw.get("profile"), "http://127.0.0.1:8010"),
            content=_pick(os.getenv("CONTENT_SERVICE_URL"), service_urls_raw.get("content"), "http://127.0.0.1:8020"),
            seed=_pick(os.getenv("SEED_SERVICE_URL"), service_urls_raw.get("seed"), "http://127.0.0.1:8030"),
            sprout=_pick(os.getenv("SPROUT_SERVICE_URL"), service_urls_raw.get("sprout"), "http://127.0.0.1:8040"),
            writing=_pick(os.getenv("WRITING_SERVICE_URL"), service_urls_raw.get("writing"), "http://127.0.0.1:8050"),
            feedback=_pick(os.getenv("FEEDBACK_SERVICE_URL"), service_urls_raw.get("feedback"), "http://127.0.0.1:8060"),
            zhihu=_pick(os.getenv("ZHIHU_ADAPTER_URL"), service_urls_raw.get("zhihu"), "http://127.0.0.1:8070"),
            llm=_pick(os.getenv("LLM_SERVICE_URL"), service_urls_raw.get("llm"), "http://127.0.0.1:8080"),
        ),
        llm=LLMConfig(
            provider_mode=_pick(os.getenv("LLM_PROVIDER_MODE"), llm_raw.get("provider_mode"), "mock"),
            default_model=_pick(os.getenv("LLM_DEFAULT_MODEL"), llm_raw.get("default_model"), "zhida-thinking-1p5"),
            prompt_version=_pick(os.getenv("LLM_PROMPT_VERSION"), llm_raw.get("prompt_version"), "v1"),
            schema_version=_pick(os.getenv("LLM_SCHEMA_VERSION"), llm_raw.get("schema_version"), "v1"),
            cache_backend=_pick(os.getenv("LLM_CACHE_BACKEND"), llm_raw.get("cache_backend"), "memory"),
            cache_ttl_seconds=int(_pick(os.getenv("LLM_CACHE_TTL_SECONDS"), llm_raw.get("cache_ttl_seconds"), 21600) or 21600),
            request_timeout_seconds=int(_pick(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS"), llm_raw.get("request_timeout_seconds"), 20) or 20),
            trace_dir=_pick(os.getenv("LLM_TRACE_DIR"), llm_raw.get("trace_dir"), "output/llm-trace"),
            trace_enabled=_pick(os.getenv("LLM_TRACE_ENABLED"), llm_raw.get("trace_enabled"), "1") in ("1", "true", "True"),
            quota=_build_llm_quota(llm_raw.get("quota")),
        ),
        openai_compat=OpenAICompatConfig(
            base_url=_pick(os.getenv("OPENAI_COMPAT_BASE_URL"), openai_compat_raw.get("base_url"), ""),
            api_key=_pick(os.getenv("OPENAI_COMPAT_API_KEY"), openai_compat_raw.get("api_key"), ""),
            model=_pick(os.getenv("OPENAI_COMPAT_MODEL"), openai_compat_raw.get("model"), "gpt-4o-mini"),
        ),
    )
    return config
