from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import Provider, ProviderError, ProviderResult


class ZhihuDirectProvider:
    name = "zhihu_direct"

    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        persona: str | None = None,
    ) -> ProviderResult:
        system_prompt = prompt
        if persona:
            system_prompt = f"{prompt}\n\n[Persona: {persona}]"
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps({"taskType": task_type, "input": input_data}, ensure_ascii=False),
                },
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/zhihu/direct-answer",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(str(exc)) from exc

        content = raw.get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = _coerce_plain_text(task_type, content, input_data, persona)

        return ProviderResult(
            output=parsed,
            provider_meta={
                "provider": self.name,
                "persona": persona,
                "model": raw.get("model") or self.model,
                "taskId": raw.get("taskId"),
            },
        )


def _coerce_plain_text(
    task_type: str,
    content: str,
    input_data: dict[str, Any],
    persona: str | None,
) -> dict[str, Any]:
    if task_type == "answer-seed-question":
        return {
            "answer": content,
            "statusRecommendation": "answered",
            "materials": [],
            "followUpQuestions": [],
        }
    if task_type == "draft":
        title = input_data.get("title") or (input_data.get("seed") or {}).get("title") or "草稿"
        return {
            "title": title,
            "body": content,
            "aiDisclosureSuggestion": "本文使用 AI 辅助梳理论证结构。",
        }
    if task_type == "roundtable-review":
        role = persona or "logic_reviewer"
        return {
            "reviews": [
                {
                    "role": role,
                    "summary": content[:200],
                    "problems": [],
                    "suggestions": [],
                    "severity": "low",
                }
            ]
        }
    return {"_rawProviderContent": content}


__all__ = ["ZhihuDirectProvider"]
