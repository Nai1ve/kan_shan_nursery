from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from kanshan_shared.categories import INTEREST_CATEGORIES, CategoryDef


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def interest_memory(cat: CategoryDef, feedback_summary: str = "") -> dict[str, Any]:
    return {
        "interestId": cat.id,
        "interestName": cat.name,
        "knowledgeLevel": cat.knowledge_level,
        "preferredPerspective": cat.preferred_perspective,
        "evidencePreference": cat.evidence_preference,
        "writingReminder": cat.writing_reminder,
        "feedbackSummary": feedback_summary,
    }


def default_profile() -> dict[str, Any]:
    profile = {
        "nickname": "看山编辑",
        "accountStatus": "已关联知乎账号 · 演示模式",
        "role": "技术创作者 / Java 后端转 AI Agent / 研究生",
        "interests": [cat.name for cat in INTEREST_CATEGORIES],
        "avoidances": "不要替我决定立场；不要生成空泛、油滑、过度平衡的 AI 味文章；不要只追逐热度而牺牲我的工程视角。",
        "globalMemory": {
            "longTermBackground": "有三年 Java 后端开发经验，做过金融软件与复杂数据同步相关项目；当前关注 AI / LLM / Agent 工程化落地。",
            "contentPreference": "偏好工程复盘、问题拆解、反方质疑、真实案例。更重视「为什么这样设计」，而不是单纯罗列概念。",
            "writingStyle": "清晰、克制、偏工程师复盘视角；允许有观点锋芒，但避免标题党和情绪煽动。需要减少排比和 AI 套话。",
            "recommendationStrategy": "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看，以及能否沉淀为观点种子。",
            "riskReminder": "容易写成逻辑很完整但不够有个人经历的文章；需要在圆桌审稿阶段主动要求补充项目踩坑、个人判断和反方边界。",
        },
        "interestMemories": [interest_memory(cat) for cat in INTEREST_CATEGORIES],
    }
    return profile


def default_update_requests() -> list[dict[str, Any]]:
    return [
        {
            "id": create_id("memory-request"),
            "interestId": "shuma",
            "targetField": "feedbackSummary",
            "suggestedValue": "评论区更关注企业权限、安全审计和团队知识库，后续写 AI Coding 需要补充这些材料。",
            "reason": "来自历史反馈摘要，但需要用户确认后才能写入兴趣 Memory。",
            "status": "pending",
            "createdAt": now_iso(),
        }
    ]


def clone(value: Any) -> Any:
    return deepcopy(value)
