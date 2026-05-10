"""LLM provider abstraction.

All providers expose the same interface so the router can select them by
config. Adding a new provider should not require any change in business
services — they only see ``POST /llm/tasks/{task_type}``.
"""

from .base import Provider, ProviderError, ProviderResult
from .mock import MockProvider, run_mock_task
from .openai_compat import OpenAICompatProvider
from .zhihu_direct import ZhihuDirectProvider

__all__ = [
    "Provider",
    "ProviderError",
    "ProviderResult",
    "MockProvider",
    "OpenAICompatProvider",
    "ZhihuDirectProvider",
    "run_mock_task",
]
