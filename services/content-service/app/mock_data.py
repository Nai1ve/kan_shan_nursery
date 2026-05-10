from __future__ import annotations

from typing import Any


CREATED_AT = "2026-05-09T09:00:00+08:00"


CATEGORIES: list[dict[str, Any]] = [
    {"id": "agent", "name": "Agent 工程化", "meta": "3 张卡 · 2 条可写", "kind": "interest", "active": True},
    {"id": "ai-coding", "name": "AI Coding", "meta": "3 张卡 · 1 条发芽", "kind": "interest"},
    {"id": "rag", "name": "RAG / 检索", "meta": "3 张卡 · 1 条缺资料", "kind": "interest"},
    {"id": "backend", "name": "后端工程", "meta": "3 张卡 · 2 条经验", "kind": "interest"},
    {"id": "growth", "name": "程序员成长", "meta": "3 张卡 · 2 条观点", "kind": "interest"},
    {"id": "following", "name": "关注流精选", "meta": "3 条社交输入", "kind": "following"},
    {"id": "serendipity", "name": "偶遇输入", "meta": "2 条远端关联", "kind": "serendipity"},
]


_CARD_SPECS: list[dict[str, Any]] = [
    {
        "id": "agent-quality",
        "categoryId": "agent",
        "title": "Agent Quality 到底评估什么？",
        "recommendationReason": "和你近期 Agent 质量系列相关，站内讨论仍停留在表层指标。",
        "contentSummary": "任务完成率被频繁讨论，但工具调用可靠性、上下文治理、失败恢复较少被系统化整理。",
        "controversies": ["Agent 是否需要软件测试式质量体系？", "任务成功率是否足够？"],
        "writingAngles": ["Agent 不是一次问答，而是可控工作流。", "Agent Quality 应该关注失败模式。"],
        "tagLabel": "Agent Quality",
        "featured": False,
    },
    {
        "id": "agent-memory",
        "categoryId": "agent",
        "title": "Agent 的 Memory 不只是聊天记录摘要",
        "recommendationReason": "和观点种子库机制相关，可写产品方法论。",
        "contentSummary": "长期记忆需要区分事实、偏好、任务状态、写作风格和反馈信号。",
        "controversies": ["记忆越多是否越好？", "用户是否应该可见、可编辑？"],
        "writingAngles": ["为什么创作 Agent 需要可编辑 Memory？", "Memory 应该服务于观点发芽。"],
        "tagLabel": "Memory",
        "featured": False,
    },
    {
        "id": "agent-observe",
        "categoryId": "agent",
        "title": "Agent 工程化为什么需要可观测性？",
        "recommendationReason": "多个开发者讨论 Agent 失败后难复盘，适合工程实践文章。",
        "contentSummary": "问题集中在工具调用链路、上下文变更、重试和回放能力。",
        "controversies": ["Agent 失败算模型问题还是系统问题？", "日志是否足够复盘？"],
        "writingAngles": ["Agent 的可观测性应该记录什么？", "为什么 Agent 要能回放失败现场？"],
        "tagLabel": "工程实践",
        "featured": False,
    },
    {
        "id": "ai-coding-growth",
        "categoryId": "ai-coding",
        "title": "AI 编程工具会不会改变程序员的成长路径？",
        "recommendationReason": "近期高热度，与你 Agent、编程、职业转型话题相关。",
        "contentSummary": "讨论集中在 AI 是否会压缩初级岗位，以及程序员是否还需要传统编码训练。",
        "controversies": ["AI 是否会替代初级开发？", "编码能力和工程能力是否会分化？"],
        "writingAngles": ["AI 时代程序员真正需要训练的是什么？", "初级程序员的成长路径是否正在被改写？"],
        "tagLabel": "知乎热榜",
        "featured": True,
    },
    {
        "id": "ai-coding-moat",
        "categoryId": "ai-coding",
        "title": "AI Coding 产品的壁垒到底在哪里？",
        "recommendationReason": "高赞回答都在讨论代码生成是否会同质化，与你已有种子相关。",
        "contentSummary": "模型能力、IDE 入口、私有上下文、企业研发流程接入。",
        "controversies": ["模型能力是否足以形成壁垒？", "上下文积累是否真的难迁移？"],
        "writingAngles": ["AI 编程工具的护城河可能不在会写代码。", "企业需要的是代码生成还是可控交付？"],
        "tagLabel": "知乎搜索",
        "featured": False,
    },
    {
        "id": "ai-coding-leetcode",
        "categoryId": "ai-coding",
        "title": "AI 时代还需要刷 LeetCode 吗？",
        "recommendationReason": "职业成长话题适合知乎回答，可连接你的工程能力判断。",
        "contentSummary": "争论从代码熟练度转向问题建模、边界分析和复杂度判断。",
        "controversies": ["刷题价值是否降低？", "AI 是否会让基础训练失效？"],
        "writingAngles": ["LeetCode 的价值正在从背模板转向建模训练。"],
        "tagLabel": "程序员成长",
        "featured": False,
    },
    {
        "id": "rag-eval",
        "categoryId": "rag",
        "title": "RAG 系统真正难评估的是什么？",
        "recommendationReason": "站内讨论常停留在召回率，缺业务失败案例。",
        "contentSummary": "RAG 质量包含解析、切分、重排、引用和回答可用性。",
        "controversies": ["召回率是否足够？", "重排能否解决所有问题？"],
        "writingAngles": ["RAG 评估应该从失败链路开始。"],
        "tagLabel": "RAG",
        "featured": False,
    },
    {
        "id": "rag-parser",
        "categoryId": "rag",
        "title": "文档解析为什么会拖垮 RAG？",
        "recommendationReason": "工程落地高度相关，适合做技术拆解。",
        "contentSummary": "PDF、表格、图片和权限边界会让知识库在入口处就出问题。",
        "controversies": ["解析失败算算法问题还是工程问题？"],
        "writingAngles": ["RAG 的第一道难题是文档进入系统。"],
        "tagLabel": "文档解析",
        "featured": False,
    },
    {
        "id": "rag-context",
        "categoryId": "rag",
        "title": "上下文越长，RAG 越不重要吗？",
        "recommendationReason": "高争议问题，可通过反方视角写出深度。",
        "contentSummary": "长上下文降低部分检索压力，但没有消除数据治理和证据追踪。",
        "controversies": ["长上下文会替代检索吗？", "引用和权限如何处理？"],
        "writingAngles": ["长上下文不是知识治理。"],
        "tagLabel": "反方观点",
        "featured": False,
    },
    {
        "id": "backend-boundary",
        "categoryId": "backend",
        "title": "后端系统里最难的往往不是写代码",
        "recommendationReason": "承接你的 Java 后端经历，形成个人经验文章。",
        "contentSummary": "复杂系统的难点在边界、状态、兼容性和交付责任。",
        "controversies": ["代码实现和系统交付差距在哪里？"],
        "writingAngles": ["为什么会写代码不等于能交付系统？"],
        "tagLabel": "工程复盘",
        "featured": False,
    },
    {
        "id": "backend-consistency",
        "categoryId": "backend",
        "title": "数据一致性问题为什么总在边界处爆炸？",
        "recommendationReason": "可用金融软件和同步系统经历补充案例。",
        "contentSummary": "分布式系统复杂性来自补偿、幂等、重试和状态同步。",
        "controversies": ["一致性是否只是数据库问题？"],
        "writingAngles": ["数据同步系统最怕什么？"],
        "tagLabel": "分布式",
        "featured": False,
    },
    {
        "id": "backend-refactor",
        "categoryId": "backend",
        "title": "AI 生成代码后，谁来负责系统演进？",
        "recommendationReason": "AI Coding 与后端工程交叉，适合写工程判断文章。",
        "contentSummary": "生成代码只是短期效率，长期维护仍依赖结构、边界和审查。",
        "controversies": ["AI 代码是否增加技术债？"],
        "writingAngles": ["AI 时代代码审查更重要。"],
        "tagLabel": "代码审查",
        "featured": False,
    },
    {
        "id": "growth-junior",
        "categoryId": "growth",
        "title": "初级程序员的训练机会会不会变少？",
        "recommendationReason": "高讨论度问题，适合用稳健立场回应焦虑。",
        "contentSummary": "AI 工具改变任务分配，新人对抽象和验证能力的要求提高。",
        "controversies": ["初级岗位是否减少？"],
        "writingAngles": ["初级程序员要从完成任务转向解释任务。"],
        "tagLabel": "职业成长",
        "featured": False,
    },
    {
        "id": "growth-learning",
        "categoryId": "growth",
        "title": "程序员学习路径要不要重排？",
        "recommendationReason": "和你转 AI Agent 路径相关，有个人视角。",
        "contentSummary": "从语言框架优先转向问题建模、系统设计和工具协作。",
        "controversies": ["基础还重要吗？"],
        "writingAngles": ["AI 时代学习路线不该只追工具。"],
        "tagLabel": "学习路径",
        "featured": False,
    },
    {
        "id": "growth-expression",
        "categoryId": "growth",
        "title": "技术人为什么写不出自己的观点？",
        "recommendationReason": "贴合看山小苗圃产品定位，可作为项目介绍内容。",
        "contentSummary": "技术人常有经验但缺少观点沉淀和表达结构。",
        "controversies": ["表达是不是浪费时间？"],
        "writingAngles": ["不动笔墨不读书在 AI 时代更重要。"],
        "tagLabel": "内容表达",
        "featured": False,
    },
    {
        "id": "following-workflow",
        "categoryId": "following",
        "title": "AI Coding 产品正在从插件走向工作流入口",
        "recommendationReason": "与你代码生成护城河浅的种子强相关，可触发今日发芽。",
        "contentSummary": "未来竞争点不是补全几行代码，而是谁能进入需求、开发、测试、发布的完整链路。",
        "controversies": ["插件级工具是否也能积累足够上下文？"],
        "writingAngles": ["AI 编程产品的壁垒在组织流程。"],
        "tagLabel": "关注作者",
        "featured": False,
    },
    {
        "id": "following-opponent",
        "categoryId": "following",
        "title": "很多人反对 AI 替代初级程序员的简单判断",
        "recommendationReason": "适合作为反方材料，避免文章变成单向输出。",
        "contentSummary": "评论区出现更细分歧：训练路径、任务来源和团队分工正在变化。",
        "controversies": ["初级岗位是否真的减少？"],
        "writingAngles": ["初级成长路径被重塑而非简单消失。"],
        "tagLabel": "圈子讨论",
        "featured": False,
    },
    {
        "id": "following-rag",
        "categoryId": "following",
        "title": "知识库产品作者复盘了 RAG 项目失败原因",
        "recommendationReason": "关注流真实项目复盘，可给 RAG 种子补案例。",
        "contentSummary": "失败点集中在文档质量、权限边界、业务验收和引用可信度。",
        "controversies": ["RAG 失败是技术问题还是业务问题？"],
        "writingAngles": ["RAG 项目失败通常不是模型一个点的问题。"],
        "tagLabel": "关注流",
        "featured": False,
    },
    {
        "id": "serendipity-risk",
        "categoryId": "serendipity",
        "title": "Agent 产品的护城河，不在单次任务完成率",
        "recommendationReason": "和金融风控的风险暴露很像，可形成差异化观点。",
        "contentSummary": "AI 编程进入企业协作场景后，单次效果不再是全部。",
        "controversies": ["单次生成能力是否会快速商品化？"],
        "writingAngles": ["Agent 产品的护城河在持续上下文、风险控制和工作流闭环。"],
        "tagLabel": "偶遇卡片",
        "featured": False,
    },
    {
        "id": "serendipity-medical",
        "categoryId": "serendipity",
        "title": "高召回不等于可交付",
        "recommendationReason": "医学检测的错误代价类比 Agent，不能只看总体成功率。",
        "contentSummary": "Agent 评测开始关注成功率，但失败模式、错误代价和恢复机制讨论不足。",
        "controversies": ["任务成功率是否足够？"],
        "writingAngles": ["Agent 评估应该关注失败模式、错误代价和恢复机制。"],
        "tagLabel": "偶遇卡片",
        "featured": False,
    },
]


def _make_sources(category_id: str, title: str, index: int) -> list[dict[str, Any]]:
    base = title.replace("？", "").replace("?", "")
    category_label = next((c["name"] for c in CATEGORIES if c["id"] == category_id), category_id)
    source_type_top = (
        "关注流" if category_id == "following"
        else "全网搜索" if category_id == "serendipity"
        else "知乎热榜"
    )
    return [
        {
            "sourceId": f"source-{category_id}-{index}-hot",
            "sourceType": source_type_top,
            "sourceUrl": f"https://mock.zhihu.local/{category_id}/{index}/hot",
            "title": f"{base}：热议问题",
            "author": "关注作者" if category_id == "following" else "知乎热榜",
            "publishedAt": "2 小时前",
            "authorityMeta": f"热度 {82 - (index % 5) * 4}",
            "meta": ["2 小时前", f"热度 {82 - (index % 5) * 4}"],
            "rawExcerpt": f"围绕 {base} 的讨论正在升温，评论区出现了支持与反对两类判断。",
            "fullContent": (
                f"问题背景：{base} 在{category_label}相关讨论中持续出现。\n\n"
                f"核心信息：讨论区把问题拆成两层：当前可观察到的趋势，以及趋势能否长期成立。\n\n"
                f"对写作的启发：适合作为文章开头的时效背景，进入写作前还需补充具体案例和反方回应。"
            ),
            "contribution": "提供时效背景和社区分歧入口。",
        },
        {
            "sourceId": f"source-{category_id}-{index}-answer",
            "sourceType": "跨域资料" if category_id == "serendipity" else "知乎高赞回答",
            "sourceUrl": f"https://mock.zhihu.local/{category_id}/{index}/answer",
            "title": f"{category_label}视角下的关键论据",
            "author": "高赞答主",
            "publishedAt": "昨天",
            "authorityMeta": f"赞同 {2 + index % 4}.{(index * 3) % 10}k",
            "meta": ["昨天", f"赞同 {2 + index % 4}.{(index * 3) % 10}k"],
            "rawExcerpt": f"作者从{category_label}角度解释了为什么这个问题不能只看表层结论。",
            "fullContent": (
                f"回答主线：作者从{category_label}的实际场景切入，先界定 {base} 不是单点能力问题。\n\n"
                f"关键论据：把正方观点拆成三个支撑点：真实需求出现、旧方法成本明显、AI 能力需要进入完整流程评估。\n\n"
                f"边界提醒：作者强调不同团队、不同风险场景会得到不同结论。"
            ),
            "contribution": "提供正方论证材料和可引用表述。",
        },
        {
            "sourceId": f"source-{category_id}-{index}-comment",
            "sourceType": "精选评论",
            "sourceUrl": f"https://mock.zhihu.local/{category_id}/{index}/comments",
            "title": f"{base}的反方质疑",
            "author": "圈子评论",
            "publishedAt": "今天",
            "authorityMeta": "精选 18 条",
            "meta": ["今天", "精选 18 条"],
            "rawExcerpt": "评论区集中质疑这个判断是否过度概括，并要求补充真实案例。",
            "fullContent": (
                f"评论焦点：反方主要质疑 {base} 是否被过度概括。\n\n"
                f"典型问题：有人要求补充失败案例，有人认为不同业务场景差异很大。\n\n"
                f"对写作的启发：适合作为文章中我知道这个观点可能被这样反驳的段落来源。"
            ),
            "contribution": "作为后续写作中的反方回应入口。",
        },
    ]


def build_card(spec: dict[str, Any], index: int) -> dict[str, Any]:
    category_id = spec["categoryId"]
    follow_tone = "green" if category_id == "following" else "orange"
    secondary_label = "远端关联" if category_id == "serendipity" else "高质量输入"
    return {
        "id": spec["id"],
        "categoryId": category_id,
        "tags": [
            {"label": spec["tagLabel"], "tone": "blue"},
            {"label": secondary_label, "tone": follow_tone},
        ],
        "title": spec["title"],
        "recommendationReason": spec["recommendationReason"],
        "contentSummary": spec["contentSummary"],
        "controversies": spec["controversies"],
        "writingAngles": spec["writingAngles"],
        "originalSources": _make_sources(category_id, spec["title"], index),
        "relevanceScore": 92 - (index % 8) * 3,
        "authorityScore": 82 - (index % 5) * 4,
        "popularityScore": 76 + (index % 6) * 3,
        "controversyScore": 58 + (index % 7) * 5,
        "createdAt": CREATED_AT,
        "featured": spec.get("featured", False),
    }


def build_initial_cards() -> list[dict[str, Any]]:
    return [build_card(spec, index) for index, spec in enumerate(_CARD_SPECS)]


def build_categories() -> list[dict[str, Any]]:
    return [dict(item) for item in CATEGORIES]
