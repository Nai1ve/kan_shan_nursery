from __future__ import annotations

from typing import Any


CREATED_AT = "2026-05-09T09:00:00+08:00"


CATEGORIES: list[dict[str, Any]] = [
    {"id": "shuma", "name": "数码科技", "meta": "2 张卡 · 1 条发芽", "kind": "interest", "active": True},
    {"id": "zhichang", "name": "职场教育", "meta": "2 张卡 · 2 条观点", "kind": "interest"},
    {"id": "chuangzuo", "name": "创作表达", "meta": "2 张卡 · 1 条缺资料", "kind": "interest"},
    {"id": "shenghuo", "name": "生活方式", "meta": "2 张卡", "kind": "interest"},
    {"id": "shehui", "name": "社会人文", "meta": "2 张卡", "kind": "interest"},
    {"id": "bendi", "name": "本地城市", "meta": "2 张卡", "kind": "interest"},
    {"id": "following", "name": "关注流精选", "meta": "3 条社交输入", "kind": "following"},
    {"id": "serendipity", "name": "偶遇输入", "meta": "2 条远端关联", "kind": "serendipity"},
]


_CARD_SPECS: list[dict[str, Any]] = [
    # 数码科技 (shuma)
    {
        "id": "ai-coding-growth",
        "categoryId": "shuma",
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
        "categoryId": "shuma",
        "title": "AI Coding 产品的壁垒到底在哪里？",
        "recommendationReason": "高赞回答都在讨论代码生成是否会同质化，与你已有种子相关。",
        "contentSummary": "模型能力、IDE 入口、私有上下文、企业研发流程接入。",
        "controversies": ["模型能力是否足以形成壁垒？", "上下文积累是否真的难迁移？"],
        "writingAngles": ["AI 编程工具的护城河可能不在会写代码。", "企业需要的是代码生成还是可控交付？"],
        "tagLabel": "知乎搜索",
        "featured": False,
    },
    # 职场教育 (zhichang)
    {
        "id": "tech-to-management",
        "categoryId": "zhichang",
        "title": "技术人转型管理，最难的不是带团队而是放手",
        "recommendationReason": "技术管理者转型是职场教育中的高频话题，适合用个人经验切入。",
        "contentSummary": "技术深度和管理广度之间的取舍，放手是否等于放弃技术。",
        "controversies": ["技术深度 vs 管理广度？", "放手是否等于放弃技术？"],
        "writingAngles": ["从写代码到带团队的思维转变。"],
        "tagLabel": "职场教育",
        "featured": False,
    },
    {
        "id": "online-degree",
        "categoryId": "zhichang",
        "title": "在线课程真的能替代传统学位吗？",
        "recommendationReason": "在线教育和传统学位的争论持续存在，适合用个人学习经历回应。",
        "contentSummary": "学习效率和认证价值的权衡，不同场景下结论不同。",
        "controversies": ["学习效率 vs 认证价值？"],
        "writingAngles": ["个人学习经历的判断。"],
        "tagLabel": "职场教育",
        "featured": False,
    },
    # 创作表达 (chuangzuo)
    {
        "id": "writing-method",
        "categoryId": "chuangzuo",
        "title": "好的技术长文，通常不是资料多，而是问题问得准",
        "recommendationReason": "关注作者的方法论总结，与看山小苗圃的产品定位直接相关。",
        "contentSummary": "资料充分不等于有价值，技术文章需要强观点和好问题。",
        "controversies": ["资料充分=有价值？", "技术文章必须有强观点？"],
        "writingAngles": ["关键不是堆概念而是建立问题。"],
        "tagLabel": "关注作者",
        "featured": False,
    },
    {
        "id": "content-strategy",
        "categoryId": "chuangzuo",
        "title": "知乎回答的开头为什么这么重要？",
        "recommendationReason": "开头策略是创作表达中的实用技巧，适合用案例说明。",
        "contentSummary": "开头决定阅读率，但不能沦为标题党。",
        "controversies": ["开头决定阅读率？"],
        "writingAngles": ["开头策略。"],
        "tagLabel": "创作表达",
        "featured": False,
    },
    # 生活方式 (shenghuo)
    {
        "id": "minimalism",
        "categoryId": "shenghuo",
        "title": "极简生活一年后，我真正丢掉了什么？",
        "recommendationReason": "生活方式话题适合用个人经历切入，容易引发共鸣。",
        "contentSummary": "极简是消费升级还是降级，每个人答案不同。",
        "controversies": ["极简是消费升级还是降级？"],
        "writingAngles": ["个人经历。"],
        "tagLabel": "生活方式",
        "featured": False,
    },
    {
        "id": "cooking-efficiency",
        "categoryId": "shenghuo",
        "title": "做饭这件事，效率和幸福感真的矛盾吗？",
        "recommendationReason": "日常话题容易引发讨论，适合轻松但有观点的写法。",
        "contentSummary": "效率做饭和享受过程之间的取舍。",
        "controversies": ["效率做饭 vs 享受过程？"],
        "writingAngles": ["个人经验。"],
        "tagLabel": "生活方式",
        "featured": False,
    },
    # 社会人文 (shehui)
    {
        "id": "ai-education",
        "categoryId": "shehui",
        "title": "AI 会不会让教育更不公平？",
        "recommendationReason": "AI 与教育公平是社会人文中的热点议题，适合用社会观察视角写。",
        "contentSummary": "AI 缩小还是扩大教育差距，取决于基础设施和资源分配。",
        "controversies": ["AI 缩小还是扩大教育差距？"],
        "writingAngles": ["社会观察。"],
        "tagLabel": "社会人文",
        "featured": False,
    },
    {
        "id": "reading-habit",
        "categoryId": "shehui",
        "title": "为什么年轻人越来越不爱读书了？",
        "recommendationReason": "文化观察类话题适合用数据和个人体验结合写。",
        "contentSummary": "碎片化阅读算不算阅读，定义本身就在变化。",
        "controversies": ["碎片化阅读算不算阅读？"],
        "writingAngles": ["文化观察。"],
        "tagLabel": "社会人文",
        "featured": False,
    },
    # 本地城市 (bendi)
    {
        "id": "city-life",
        "categoryId": "bendi",
        "title": "在一线城市租房，最不值得花的钱是什么？",
        "recommendationReason": "本地生活经验是知乎高互动话题，适合用真实体验写。",
        "contentSummary": "花钱提升租房体验是否值得，每个人标准不同。",
        "controversies": ["花钱提升租房体验值不值？"],
        "writingAngles": ["本地生活经验。"],
        "tagLabel": "本地城市",
        "featured": False,
    },
    {
        "id": "hidden-spots",
        "categoryId": "bendi",
        "title": "你所在城市有哪些被低估的角落？",
        "recommendationReason": "城市观察类话题适合轻松分享，互动性强。",
        "contentSummary": "被低估的角落往往藏着城市的真实面貌。",
        "controversies": [],
        "writingAngles": ["城市观察。"],
        "tagLabel": "本地城市",
        "featured": False,
    },
    # 关注流精选 (following)
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
        "id": "following-method",
        "categoryId": "following",
        "title": "好的技术长文方法论",
        "recommendationReason": "关注作者的方法论分享，可以补充写作策略。",
        "contentSummary": "方法论层面的总结对写作有直接帮助。",
        "controversies": ["方法论是否可迁移？"],
        "writingAngles": ["方法论。"],
        "tagLabel": "关注作者",
        "featured": False,
    },
    # 偶遇输入 (serendipity)
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
