from __future__ import annotations

from pathlib import Path


TASKS = {
    "summarize-content",
    "extract-controversies",
    "generate-writing-angles",
    "answer-seed-question",
    "supplement-material",
    "sprout-opportunities",
    "argument-blueprint",
    "draft",
    "roundtable-review",
    "feedback-summary",
}

PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(task_type: str, prompt_version: str) -> str:
    if task_type not in TASKS:
        raise ValueError(f"Unsupported taskType: {task_type}")
    path = PROMPT_ROOT / prompt_version / f"{task_type}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "你是看山小苗圃的创作辅助 Agent。"
        "请只基于输入信息输出结构化 JSON，不替用户决定立场。"
    )
