"""Shared utilities for Python services.

Only put framework-level helpers here:
- structured logging (jsonl + console)
- config loading (yaml file + env override)
- database engine / session factory
- redis client factory
- request_id / time helpers
- error envelopes

Do not put business logic here.
"""

from .categories import (
    ALL_CATEGORIES,
    CATEGORY_MAP,
    INTEREST_CATEGORIES,
    SPECIAL_CATEGORIES,
    CategoryDef,
    get_interest_names,
)
from .config import KanshanConfig, ZhihuConfig, load_config
from .llm_client import LLMClient, LLMClientError
from .logger import LoggerFactory, configure_logging, get_logger

__all__ = [
    "ALL_CATEGORIES",
    "CATEGORY_MAP",
    "CategoryDef",
    "INTEREST_CATEGORIES",
    "KanshanConfig",
    "SPECIAL_CATEGORIES",
    "ZhihuConfig",
    "get_interest_names",
    "load_config",
    "LLMClient",
    "LLMClientError",
    "LoggerFactory",
    "configure_logging",
    "get_logger",
]

# Optional imports - these require sqlalchemy/redis which may not be installed
# in services that don't need them (e.g., api-gateway)
try:
    from .database import Base, get_engine, get_session_factory
    __all__ += ["Base", "get_engine", "get_session_factory"]
except ImportError:
    pass

try:
    from .redis_client import get_redis_client
    __all__ += ["get_redis_client"]
except ImportError:
    pass
