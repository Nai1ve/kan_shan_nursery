from __future__ import annotations

from typing import Any


FEEDBACK_ARTICLES: list[dict[str, Any]] = [
    {
        "id": "article-moat",
        "title": "AI 编程工具的护城河，可能不在会写代码",
        "interestId": "ai-coding",
        "linkedSeedId": "seed-ai-coding-moat",
        "status": "表现良好",
        "statusTone": "green",
        "performanceSummary": "阅读完成率较高，收藏率高于平均值。评论区围绕上下文是否真的构成壁垒展开。",
        "commentInsights": [
            "支持观点：企业研发流程确实比单次生成更重要。",
            "反方观点：未来长上下文模型可能会弱化这个壁垒。",
            "补充材料：多人提到权限、安全审计和团队知识库。",
        ],
        "memoryAction": "生成新种子：AI Coding 的企业壁垒可能在权限、安全和组织知识库。",
        "metrics": [
            {"label": "阅读完成率", "value": 78},
            {"label": "收藏率", "value": 42},
            {"label": "评论争议度", "value": 69},
        ],
    },
    {
        "id": "article-quality",
        "title": "Agent Quality 到底评估什么？",
        "interestId": "agent",
        "linkedSeedId": "seed-agent-quality",
        "status": "需要复盘",
        "statusTone": "orange",
        "performanceSummary": "点赞不错，但评论指出文章偏框架化，缺少真实失败案例。",
        "commentInsights": [
            "读者希望看到更多真实工具调用失败案例。",
            "有人质疑质量体系是否会增加开发负担。",
            "高赞评论建议补充可观测性和回放机制。",
        ],
        "memoryAction": "将真实案例不足写入写作风险 Memory，下次自动提醒补案例。",
        "metrics": [
            {"label": "阅读完成率", "value": 61},
            {"label": "收藏率", "value": 35},
            {"label": "案例需求", "value": 82},
        ],
    },
]


COMMENT_SUMMARIES: dict[str, dict[str, list[str]]] = {
    "article-moat": {
        "supportingViews": [
            "企业研发流程确实比单次生成更重要。",
            "权限、审计和团队知识库是企业级 AI 工具的关键。",
        ],
        "counterArguments": [
            "如果模型上下文窗口足够大，上下文积累可能不再形成长期壁垒。",
            "工作流入口可能被平台型公司直接整合掉。",
        ],
        "supplementaryMaterials": [
            "某企业落地 AI 编程工具后引入审计流程的案例。",
            "知乎上一份关于工程团队接入 AI 工具的复盘。",
        ],
        "secondArticleAngles": [
            "AI Coding 的企业壁垒可能在权限、安全和组织知识库。",
            "工作流入口竞争如何影响开发者工具生态？",
        ],
    },
    "article-quality": {
        "supportingViews": [
            "Agent 失败需要可观测性才能复盘。",
            "工具调用链路应该有明确的日志和回放。",
        ],
        "counterArguments": [
            "完整质量体系对小团队成本过高。",
            "把软件测试范式直接套用到 Agent 不一定合适。",
        ],
        "supplementaryMaterials": [
            "一次工具调用失败导致 Agent 持续给出错误结论的真实案例。",
            "Agent 上下文污染后无法复盘的复盘讨论。",
        ],
        "secondArticleAngles": [
            "Agent 工程化的最小可观测性清单。",
            "为什么 Agent 失败模式比成功率更值得讨论？",
        ],
    },
}
