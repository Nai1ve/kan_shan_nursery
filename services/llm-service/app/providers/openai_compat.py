"""OpenAI-compatible provider.

Calls any OpenAI-compatible chat completions endpoint (e.g. Azure, local LLMs,
third-party proxies). Configuration is read from env vars:
  - OPENAI_COMPAT_BASE_URL
  - OPENAI_COMPAT_API_KEY
  - OPENAI_COMPAT_MODEL (default: gpt-4o-mini)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import urllib.request
import urllib.error

from .base import Provider, ProviderError, ProviderResult

logger = logging.getLogger("kanshan.llm.providers.openai_compat")


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        persona: str | None = None,
    ) -> ProviderResult:
        """Execute a chat completion call and return structured result."""
        start_time = time.time()

        # Enhance prompt to request JSON output
        enhanced_prompt = f"""{prompt}

请以 JSON 格式输出结果。确保输出是有效的 JSON 对象。"""

        # Build messages
        messages = []
        if persona:
            messages.append({"role": "system", "content": persona})
        messages.append({"role": "user", "content": enhanced_prompt})

        # Build request body
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            response_text = self._call_api(body)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Parse response
            result = self._parse_response(response_text, task_type)

            provider_meta = {
                "provider": self.name,
                "model": self.model,
                "latency_ms": elapsed_ms,
                "cached": False,
            }
            if persona:
                provider_meta["persona"] = persona

            return ProviderResult(output=result, provider_meta=provider_meta)

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error("openai_compat_call_failed", extra={
                "task_type": task_type,
                "error": str(e),
                "latency_ms": elapsed_ms,
            })
            raise ProviderError(f"OpenAI compat call failed: {e}") from e

    def _call_api(self, body: dict[str, Any]) -> str:
        """Make HTTP request to OpenAI-compatible endpoint."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise ProviderError(f"HTTP {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise ProviderError(f"Connection error: {e.reason}") from e

    def _parse_response(self, response_text: str, task_type: str) -> dict[str, Any]:
        """Parse OpenAI chat completion response into structured output."""
        try:
            response = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ProviderError(f"Invalid JSON response: {e}") from e

        # Extract content from response
        choices = response.get("choices", [])
        if not choices:
            raise ProviderError("No choices in response")

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise ProviderError("Empty content in response")

        # Try to extract JSON from content (may be wrapped in markdown code block)
        json_str = content
        if "```json" in content:
            # Extract JSON from markdown code block
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
        elif "```" in content:
            # Try generic code block
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()

        # Try to parse as JSON
        try:
            structured = json.loads(json_str)
            if isinstance(structured, dict):
                return structured
        except (json.JSONDecodeError, TypeError):
            pass

        # Return as plain text wrapped in standard structure
        return {
            "content": content,
            "task_type": task_type,
            "model": self.model,
        }


__all__ = ["OpenAICompatProvider"]
