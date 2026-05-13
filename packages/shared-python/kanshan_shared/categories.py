"""Canonical interest/category definitions — single source of truth.

All backend services and the frontend API must import categories from here.
Do NOT duplicate category definitions in individual services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CategoryDef:
    id: str
    name: str
    kind: str  # "interest" | "following" | "serendipity"
    description: str = ""
    knowledge_level: str = ""
    preferred_perspective: list[str] = field(default_factory=list)
    evidence_preference: str = ""
    writing_reminder: str = ""
    default_queries: list[str] = field(default_factory=list)


INTEREST_CATEGORIES: list[CategoryDef] = [
    CategoryDef(
        id="shuma", name="数码科技", kind="interest",
        description="设备、软件、AI、消费电子",
        knowledge_level="中级", preferred_perspective=["设备", "软件", "AI", "消费电子"],
        evidence_preference="案例优先",
        writing_reminder="不要只讲参数和发布会，需要补充实际使用场景和购买决策分析。",
        default_queries=["AI 编程", "数码科技"],
    ),
    CategoryDef(
        id="zhichang", name="职场教育", kind="interest",
        description="职业成长、学习路径、技能提升",
        knowledge_level="进阶", preferred_perspective=["职业判断", "学习路径", "个人经历"],
        evidence_preference="个人经验 + 案例",
        writing_reminder="允许表达鲜明立场，但要回应焦虑和反方质疑。",
        default_queries=["职场成长", "职业发展"],
    ),
    CategoryDef(
        id="chuangzuo", name="创作表达", kind="interest",
        description="写作方法、内容策略、表达技巧",
        knowledge_level="中级", preferred_perspective=["表达结构", "社区语境", "读者反馈"],
        evidence_preference="案例 + 反馈",
        writing_reminder="避免模板化写作，强调作者主体性和观点形成过程。",
        default_queries=["写作方法论", "内容创作"],
    ),
    CategoryDef(
        id="shenghuo", name="生活方式", kind="interest",
        description="日常生活、健康、兴趣爱好",
        knowledge_level="入门", preferred_perspective=["生活经验", "实用建议"],
        evidence_preference="个人经验优先",
        writing_reminder="保持真实感，避免泛泛而谈的生活建议。",
        default_queries=["生活方式", "极简生活"],
    ),
    CategoryDef(
        id="shehui", name="社会人文", kind="interest",
        description="社会观察、人文思考、文化评论",
        knowledge_level="中级", preferred_perspective=["社会观察", "人文思考"],
        evidence_preference="资料 + 观点平衡",
        writing_reminder="需要有数据或案例支撑，避免纯情绪化表达。",
        default_queries=["社会观察", "教育公平"],
    ),
    CategoryDef(
        id="bendi", name="本地城市", kind="interest",
        description="本地生活、城市观察、区域话题",
        knowledge_level="入门", preferred_perspective=["本地生活", "城市观察"],
        evidence_preference="个人体验优先",
        writing_reminder="需要真实的本地体验，避免通用化描述。",
        default_queries=["城市生活", "本地生活"],
    ),
    CategoryDef(
        id="yule", name="文娱体育", kind="interest",
        description="影视、音乐、游戏、运动",
        knowledge_level="入门", preferred_perspective=["影视", "音乐", "游戏", "运动"],
        evidence_preference="个人体验 + 评论",
        writing_reminder="允许有情绪表达，但需要有具体观点。",
        default_queries=["文娱体育", "热门话题"],
    ),
    CategoryDef(
        id="caijing", name="财经商业", kind="interest",
        description="投资、理财、商业分析",
        knowledge_level="中级", preferred_perspective=["投资", "理财", "商业分析"],
        evidence_preference="数据 + 案例",
        writing_reminder="需要谨慎，不做投资建议，只讨论分析方法。",
        default_queries=["财经商业", "宏观经济"],
    ),
    CategoryDef(
        id="jiankang", name="健康医学", kind="interest",
        description="身心健康、医疗科普",
        knowledge_level="入门", preferred_perspective=["身心健康", "医疗科普"],
        evidence_preference="论文 + 案例",
        writing_reminder="要谨慎，不做医疗建议，只讨论科普知识。",
        default_queries=["健康医学", "生活健康"],
    ),
    CategoryDef(
        id="qiche", name="汽车出行", kind="interest",
        description="新能源、驾驶、出行方式",
        knowledge_level="入门", preferred_perspective=["新能源", "驾驶", "出行方式"],
        evidence_preference="个人体验优先",
        writing_reminder="需要真实用车体验，避免纯参数对比。",
        default_queries=["汽车出行", "新能源车"],
    ),
    CategoryDef(
        id="lishi", name="历史考古", kind="interest",
        description="历史事件、文化遗迹、考古发现",
        knowledge_level="中级", preferred_perspective=["历史事件", "文化遗迹", "考古发现"],
        evidence_preference="资料 + 观点",
        writing_reminder="需要有史料支撑，避免戏说。",
        default_queries=["历史考古", "历史故事"],
    ),
    CategoryDef(
        id="huanjing", name="环境自然", kind="interest",
        description="环保、自然生态、户外探索",
        knowledge_level="入门", preferred_perspective=["环保", "自然生态", "户外探索"],
        evidence_preference="个人体验 + 数据",
        writing_reminder="需要有实际体验或数据支撑。",
        default_queries=["环境保护", "自然观察"],
    ),
]

SPECIAL_CATEGORIES: set[str] = {"following", "serendipity"}

SPECIAL_CATEGORY_DEFS: list[CategoryDef] = [
    CategoryDef(id="following", name="关注流精选", kind="following", description="社交输入"),
    CategoryDef(id="serendipity", name="偶遇输入", kind="serendipity", description="远端关联"),
]

ALL_CATEGORIES: list[CategoryDef] = INTEREST_CATEGORIES + SPECIAL_CATEGORY_DEFS

CATEGORY_MAP: dict[str, CategoryDef] = {cat.id: cat for cat in ALL_CATEGORIES}


def get_interest_names() -> dict[str, str]:
    """Return {interest_id: interest_name} mapping for all interest categories."""
    return {cat.id: cat.name for cat in INTEREST_CATEGORIES}
