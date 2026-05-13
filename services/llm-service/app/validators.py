from __future__ import annotations

from typing import Any


TASK_REQUIRED_KEYS = {
    "summarize-content": {"summary", "keyPoints", "sourceIds", "nextAction"},
    "extract-controversies": {"controversies"},
    "generate-writing-angles": {"angles"},
    "answer-seed-question": {"answer", "statusRecommendation", "materials", "followUpQuestions"},
    "supplement-material": {"material"},
    "sprout-opportunities": {"opportunities"},
    "argument-blueprint": {"coreClaim", "outline", "counterResponses"},
    "draft": {"title", "body", "aiDisclosureSuggestion"},
    "roundtable-review": {"reviews"},
    "feedback-summary": {"summary", "signals", "secondArticleIdeas"},
    "profile-memory-synthesis": {"globalMemory", "interestMemories"},
}


def validate_request(payload: dict[str, Any], expected_task: str | None = None) -> tuple[str, dict[str, Any], str, str]:
    task_type = payload.get("taskType") or expected_task
    if not task_type:
        raise ValueError("taskType is required")
    if expected_task and task_type != expected_task:
        raise ValueError(f"taskType must be {expected_task}")
    if task_type not in TASK_REQUIRED_KEYS:
        raise ValueError(f"Unsupported taskType: {task_type}")
    input_data = payload.get("input")
    if not isinstance(input_data, dict):
        raise ValueError("input must be an object")
    prompt_version = payload.get("promptVersion", "v1")
    schema_version = payload.get("schemaVersion", "v1")
    return task_type, input_data, prompt_version, schema_version


def validate_output(task_type: str, output: dict[str, Any]) -> None:
    missing = TASK_REQUIRED_KEYS[task_type] - output.keys()
    if missing:
        raise ValueError(f"Task output missing required keys for {task_type}: {sorted(missing)}")
