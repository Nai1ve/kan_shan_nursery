from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


SEED_OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "id": "sprout-moat",
        "seedId": "seed-ai-coding-moat",
        "interestId": "ai-coding",
        "score": 87,
        "tags": [
            {"label": "高时效", "tone": "green"},
            {"label": "发芽指数 87", "tone": "blue"},
        ],
        "activatedSeed": "单纯代码生成工具的护城河很浅。",
        "triggerTopic": "某 AI 编程工具发布企业协作能力，引发工作流入口讨论。",
        "whyWorthWriting": "热点验证之前的判断：当代码生成同质化，竞争重点会转向工作流入口、上下文管理和企业协作数据。",
        "suggestedTitle": "AI 编程工具的护城河，可能不在会写代码",
        "suggestedAngle": "从代码生成商品化切入，讨论 AI 编程产品真正的长期壁垒。",
        "suggestedMaterials": "你过去做复杂系统时的需求边界、状态变化、系统约束和交付责任案例。",
        "status": "new",
    },
    {
        "id": "sprout-quality",
        "seedId": "seed-agent-quality",
        "interestId": "agent",
        "score": 79,
        "tags": [
            {"label": "缺案例", "tone": "orange"},
            {"label": "发芽指数 79", "tone": "blue"},
        ],
        "activatedSeed": "Agent Quality 不能只看任务完成率。",
        "triggerTopic": "多个开发者讨论 Agent 调工具失败后无法复盘。",
        "whyWorthWriting": "话题能连接 Agent 工程化和软件质量体系，适合写成可落地清单。",
        "suggestedTitle": "Agent Quality 到底评估什么？",
        "suggestedAngle": "从失败模式、工具调用、上下文污染和回放能力切入。",
        "suggestedMaterials": "补充一次真实工具调用失败或上下文污染导致错误输出的案例。",
        "status": "new",
    },
]


VALID_STATUSES = {"new", "supplemented", "angle_changed", "dismissed", "writing"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def initial_opportunities() -> list[dict[str, Any]]:
    return [dict(item) for item in SEED_OPPORTUNITIES]
