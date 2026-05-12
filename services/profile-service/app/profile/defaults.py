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
    ("shuma", "数码科技", "中级", ["设备", "软件", "AI", "消费电子"], "案例优先", "不要只讲参数和发布会，需要补充实际使用场景和购买决策分析。"),
    ("zhichang", "职场教育", "进阶", ["职业判断", "学习路径", "个人经历"], "个人经验 + 案例", "允许表达鲜明立场，但要回应焦虑和反方质疑。"),
    ("chuangzuo", "创作表达", "中级", ["表达结构", "社区语境", "读者反馈"], "案例 + 反馈", "避免模板化写作，强调作者主体性和观点形成过程。"),
    ("shenghuo", "生活方式", "入门", ["生活经验", "实用建议"], "个人经验优先", "保持真实感，避免泛泛而谈的生活建议。"),
    ("shehui", "社会人文", "中级", ["社会观察", "人文思考"], "资料 + 观点平衡", "需要有数据或案例支撑，避免纯情绪化表达。"),
    ("bendi", "本地城市", "入门", ["本地生活", "城市观察"], "个人体验优先", "需要真实的本地体验，避免通用化描述。"),
    ("yule", "文娱体育", "入门", ["影视", "音乐", "游戏", "运动"], "个人体验 + 评论", "允许有情绪表达，但需要有具体观点。"),
    ("caijing", "财经商业", "中级", ["投资", "理财", "商业分析"], "数据 + 案例", "需要谨慎，不做投资建议，只讨论分析方法。"),
    ("jiankang", "健康医学", "入门", ["身心健康", "医疗科普"], "论文 + 案例", "要谨慎，不做医疗建议，只讨论科普知识。"),
    ("qiche", "汽车出行", "入门", ["新能源", "驾驶", "出行方式"], "个人体验优先", "需要真实用车体验，避免纯参数对比。"),
    ("lishi", "历史考古", "中级", ["历史事件", "文化遗迹", "考古发现"], "资料 + 观点", "需要有史料支撑，避免戏说。"),
    ("huanjing", "环境自然", "入门", ["环保", "自然生态", "户外探索"], "个人体验 + 数据", "需要有实际体验或数据支撑。"),
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
