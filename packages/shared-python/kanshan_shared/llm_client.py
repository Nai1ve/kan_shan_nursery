"""Shared LLM client for calling llm-service tasks.

Usage:
    from kanshan_shared.llm_client import LLMClient

    client = LLMClient("http://127.0.0.1:8080")
    result = client.call_task("summarize-content", {"title": "...", "content": "..."})
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger("kanshan.llm_client")


class LLMClient:
    """Client for calling llm-service tasks."""

    def __init__(self, llm_service_url: str, timeout: float = 30):
        self.base_url = llm_service_url.rstrip("/")
        self.timeout = timeout

    def call_task(self, task_type: str, input_data: dict[str, Any], prompt_version: str = "v1") -> dict[str, Any]:
        """Call a specific LLM task and return the output.

        Args:
            task_type: The task type (e.g., "summarize-content", "answer-seed-question")
            input_data: The input data for the task
            prompt_version: The prompt version to use (default: "v1")

        Returns:
            The task output dictionary

        Raises:
            LLMClientError: If the call fails
        """
        url = f"{self.base_url}/llm/tasks/{task_type}"
        payload = {
            "input": input_data,
            "promptVersion": prompt_version,
        }

        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # Check for error in response
            if "detail" in result:
                raise LLMClientError(f"LLM task failed: {result['detail']}")

            # Extract output
            output = result.get("output")
            if not output:
                raise LLMClientError(f"No output in LLM response: {result}")

            return output

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            raise LLMClientError(f"HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise LLMClientError(f"Connection error: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise LLMClientError(f"Invalid JSON response: {e}") from e

    def summarize_content(self, title: str, content: str, sources: list[dict] | None = None) -> dict[str, Any]:
        """Convenience method for summarize-content task."""
        return self.call_task("summarize-content", {
            "title": title,
            "content": content,
            "sources": sources or [],
        })

    def extract_controversies(self, title: str, content: str) -> dict[str, Any]:
        """Convenience method for extract-controversies task."""
        return self.call_task("extract-controversies", {
            "title": title,
            "content": content,
        })

    def generate_writing_angles(self, title: str, content: str, controversies: list[dict] | None = None) -> dict[str, Any]:
        """Convenience method for generate-writing-angles task."""
        return self.call_task("generate-writing-angles", {
            "title": title,
            "content": content,
            "controversies": controversies or [],
        })

    def answer_seed_question(self, seed: dict[str, Any], question: str, materials: list[dict] | None = None) -> dict[str, Any]:
        """Convenience method for answer-seed-question task."""
        return self.call_task("answer-seed-question", {
            "seed": seed,
            "question": question,
            "materials": materials or [],
        })

    def supplement_material(self, seed: dict[str, Any], material_type: str, existing_materials: list[dict] | None = None) -> dict[str, Any]:
        """Convenience method for supplement-material task."""
        return self.call_task("supplement-material", {
            "seed": seed,
            "materialType": material_type,
            "existingMaterials": existing_materials or [],
        })

    def identify_sprout_opportunities(self, seeds: list[dict], hot_topics: list[dict], user_profile: dict | None = None) -> dict[str, Any]:
        """Convenience method for sprout-opportunities task."""
        return self.call_task("sprout-opportunities", {
            "seeds": seeds,
            "hotTopics": hot_topics,
            "userProfile": user_profile or {},
        })

    def build_argument_blueprint(self, seed: dict, germination: dict, user_memory: dict | None = None) -> dict[str, Any]:
        """Convenience method for argument-blueprint task."""
        return self.call_task("argument-blueprint", {
            "seed": seed,
            "germination": germination,
            "userMemory": user_memory or {},
        })

    def generate_draft(self, blueprint: dict, user_memory: dict | None = None, platform: str = "zhihu_article") -> dict[str, Any]:
        """Convenience method for draft task."""
        return self.call_task("draft", {
            "blueprint": blueprint,
            "userMemory": user_memory or {},
            "platform": platform,
        })

    def roundtable_review(self, draft: dict, user_memory: dict | None = None) -> dict[str, Any]:
        """Convenience method for roundtable-review task."""
        return self.call_task("roundtable-review", {
            "draft": draft,
            "userMemory": user_memory or {},
        })

    def summarize_feedback(self, article: dict, metrics: dict, comments: list[dict], user_memory: dict | None = None) -> dict[str, Any]:
        """Convenience method for feedback-summary task."""
        return self.call_task("feedback-summary", {
            "article": article,
            "metrics": metrics,
            "comments": comments,
            "userMemory": user_memory or {},
        })

    def synthesize_profile_memory(self, user: dict, interactions: dict, current_memory: dict | None = None) -> dict[str, Any]:
        """Convenience method for profile-memory-synthesis task."""
        return self.call_task("profile-memory-synthesis", {
            "user": user,
            "interactions": interactions,
            "currentMemory": current_memory or {},
        })


class LLMClientError(Exception):
    """Error raised by LLMClient."""
    pass
