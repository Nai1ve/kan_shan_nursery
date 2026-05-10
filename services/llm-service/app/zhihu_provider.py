from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .mock_provider import run_mock_task
from .prompts import load_prompt
from .settings import Settings


class ProviderError(Exception):
    pass


def run_zhihu_task(task_type: str, input_data: dict[str, Any], settings: Settings, prompt_version: str) -> dict[str, Any]:
    prompt = load_prompt(task_type, prompt_version)
    payload = {
        "model": settings.default_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps({"taskType": task_type, "input": input_data}, ensure_ascii=False),
            },
        ],
    }
    request = urllib.request.Request(
        f"{settings.zhihu_adapter_url.rstrip('/')}/zhihu/direct-answer",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(str(exc)) from exc

    content = raw.get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = _coerce_plain_text(task_type, content, input_data)
    return {**parsed, "providerMeta": {"model": raw.get("model"), "taskId": raw.get("taskId")}}


def run_with_fallback(task_type: str, input_data: dict[str, Any], settings: Settings, prompt_version: str) -> tuple[dict[str, Any], bool]:
    if settings.provider_mode != "zhihu":
        return run_mock_task(task_type, input_data), False
    try:
        return run_zhihu_task(task_type, input_data, settings, prompt_version), False
    except ProviderError:
        return run_mock_task(task_type, input_data), True


def _coerce_plain_text(task_type: str, content: str, input_data: dict[str, Any]) -> dict[str, Any]:
    if task_type == "answer-seed-question":
        return {"answer": content, "statusRecommendation": "answered", "materials": [], "followUpQuestions": []}
    if task_type == "draft":
        title = input_data.get("title") or (input_data.get("seed") or {}).get("title") or "草稿"
        return {"title": title, "body": content, "aiDisclosureSuggestion": "本文使用 AI 辅助梳理论证结构。"}
    if task_type == "roundtable-review":
        return {
            "reviews": [
                {
                    "role": "logic_reviewer",
                    "summary": content,
                    "problems": [],
                    "suggestions": [],
                    "severity": "low",
                }
            ]
        }
    output = run_mock_task(task_type, input_data)
    output["rawProviderContent"] = content
    return output
