from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


INTERESTS = [
    ("agent", "Agent 工程化", "进阶", ["系统设计", "质量评估", "失败恢复"], "框架 + 案例平衡", "避免停留在概念层，需要给出可落地的评估维度和失败模式。"),
    ("ai-coding", "AI Coding", "中级", ["工程交付", "研发工作流", "程序员成长"], "案例优先", "不要只讲工具趋势，需要补充具体工程场景和使用 AI 编程时的真实判断。"),
    ("rag", "RAG / 检索", "中级", ["检索质量", "文档解析", "评估指标"], "框架 + 数据平衡", "需要把召回、重排、上下文污染和业务失败案例讲清楚。"),
    ("backend", "后端工程", "进阶", ["系统边界", "数据一致性", "工程交付"], "个人经验 + 案例", "适合加入 Java 后端、金融软件和数据同步项目中的真实判断。"),
    ("growth", "程序员成长", "中级", ["职业判断", "学习路径", "个人经历"], "个人经验 + 社区反馈", "允许表达鲜明立场，但要回应焦虑和反方质疑。"),
    ("finance-risk", "金融风控", "中级", ["风险暴露", "可追责", "流程控制"], "案例 + 风险框架", "避免把金融风控类比套得太满，需要说明类比边界。"),
    ("medical-ai", "医学 AI", "入门", ["指标解释", "错误代价", "临床风险"], "论文 + 案例", "要谨慎，不做医疗建议，只讨论评估方法和风险意识。"),
    ("product-design", "产品设计", "中级", ["用户任务", "协作流程", "信息架构"], "产品案例", "需要落到真实工作流，不只讲交互表层。"),
    ("content-creation", "内容创作", "中级", ["表达结构", "社区语境", "读者反馈"], "案例 + 反馈", "要避免模板化写作，强调作者主体性和观点形成过程。"),
    ("following", "关注流精选", "中级", ["关注作者", "圈子讨论", "社交反馈"], "关注关系 + 评论", "关注流是平级输入，只筛选观点密度高、能补充已有种子的内容。"),
    ("serendipity", "偶遇输入", "入门", ["远端关联", "跨域类比", "新信息增益"], "跨域案例 + 边界说明", "偶遇输入不是随机推荐，必须说明和已有兴趣的可解释关联。"),
]


def interest_memory(
    interest_id: str,
    interest_name: str,
    knowledge_level: str,
    preferred_perspective: list[str],
    evidence_preference: str,
    writing_reminder: str,
    feedback_summary: str = "",
) -> dict[str, Any]:
    return {
        "interestId": interest_id,
        "interestName": interest_name,
        "knowledgeLevel": knowledge_level,
        "preferredPerspective": preferred_perspective,
        "evidencePreference": evidence_preference,
        "writingReminder": writing_reminder,
        "feedbackSummary": feedback_summary,
    }


def default_profile() -> dict[str, Any]:
    profile = {
        "nickname": "看山编辑",
        "accountStatus": "已关联知乎账号 · 演示模式",
        "role": "技术创作者 / Java 后端转 AI Agent / 研究生",
        "interests": [item[1] for item in INTERESTS if item[0] not in {"following", "serendipity"}],
        "avoidances": "不要替我决定立场；不要生成空泛、油滑、过度平衡的 AI 味文章；不要只追逐热度而牺牲我的工程视角。",
        "globalMemory": {
            "longTermBackground": "有三年 Java 后端开发经验，做过金融软件与复杂数据同步相关项目；当前关注 AI / LLM / Agent 工程化落地。",
            "contentPreference": "偏好工程复盘、问题拆解、反方质疑、真实案例。更重视“为什么这样设计”，而不是单纯罗列概念。",
            "writingStyle": "清晰、克制、偏工程师复盘视角；允许有观点锋芒，但避免标题党和情绪煽动。需要减少排比和 AI 套话。",
            "recommendationStrategy": "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看，以及能否沉淀为观点种子。",
            "riskReminder": "容易写成逻辑很完整但不够有个人经历的文章；需要在圆桌审稿阶段主动要求补充项目踩坑、个人判断和反方边界。",
        },
        "interestMemories": [interest_memory(*item) for item in INTERESTS],
    }
    for item in profile["interestMemories"]:
        if item["interestId"] == "ai-coding":
            item["feedbackSummary"] = "读者更喜欢真实项目场景，而不是工具功能罗列。"
    return profile


def default_update_requests() -> list[dict[str, Any]]:
    return [
        {
            "id": create_id("memory-request"),
            "interestId": "ai-coding",
            "targetField": "feedbackSummary",
            "suggestedValue": "评论区更关注企业权限、安全审计和团队知识库，后续写 AI Coding 需要补充这些材料。",
            "reason": "来自历史反馈摘要，但需要用户确认后才能写入兴趣 Memory。",
            "status": "pending",
            "createdAt": now_iso(),
        }
    ]


def clone(value: Any) -> Any:
    return deepcopy(value)
