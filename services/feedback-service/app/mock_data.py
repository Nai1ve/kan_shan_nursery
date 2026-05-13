from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FEEDBACK_ARTICLES: list[dict[str, Any]] = [
    {
        "id": "article-moat",
        "title": "AI 编程工具的护城河，可能不在会写代码",
        "interestId": "ai-coding",
        "linkedSeedId": "seed-ai-coding-moat",
        "status": "tracking",
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
        "publishMode": "mock",
        "publishedAt": "2026-05-10T08:00:00Z",
        "coreClaim": "AI编程工具的真正护城河不在代码生成能力，而在企业研发流程的深度整合",
        "latestMetrics": {
            "readCount": 1200,
            "likeCount": 86,
            "commentCount": 23,
            "favoriteCount": 45,
            "shareCount": 12,
            "metricSource": "mock",
            "capturedAt": "2026-05-12T10:00:00Z",
        },
    },
    {
        "id": "article-quality",
        "title": "Agent Quality 到底评估什么？",
        "interestId": "agent",
        "linkedSeedId": "seed-agent-quality",
        "status": "tracking",
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
        "publishMode": "mock",
        "publishedAt": "2026-05-11T09:00:00Z",
        "coreClaim": "Agent质量评估应该关注失败模式和可观测性，而不仅仅是成功率",
        "latestMetrics": {
            "readCount": 890,
            "likeCount": 52,
            "commentCount": 31,
            "favoriteCount": 28,
            "shareCount": 8,
            "metricSource": "mock",
            "capturedAt": "2026-05-12T10:00:00Z",
        },
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


# Mock comments in FeedbackComment[] format
MOCK_COMMENTS: dict[str, list[dict[str, Any]]] = {
    "article-moat": [
        {"commentId": "c1", "author": "张工", "content": "企业研发流程确实比单次生成更重要，我们团队就是这样做的。", "likeCount": 15, "createdAt": "2026-05-10T10:30:00Z"},
        {"commentId": "c2", "author": "李明", "content": "如果模型上下文窗口足够大，上下文积累可能不再形成长期壁垒。", "likeCount": 12, "createdAt": "2026-05-10T11:00:00Z"},
        {"commentId": "c3", "author": "王芳", "content": "权限、审计和团队知识库才是企业级 AI 工具的关键。", "likeCount": 8, "createdAt": "2026-05-10T12:00:00Z"},
        {"commentId": "c4", "author": "赵强", "content": "工作流入口可能被平台型公司直接整合掉，这个风险很大。", "likeCount": 6, "createdAt": "2026-05-10T14:00:00Z"},
        {"commentId": "c5", "author": "陈工", "content": "我们公司引入了审计流程，确实有效果，但成本不低。", "likeCount": 5, "createdAt": "2026-05-11T09:00:00Z"},
    ],
    "article-quality": [
        {"commentId": "c6", "author": "周工", "content": "Agent 失败需要可观测性才能复盘，这点说得太对了。", "likeCount": 18, "createdAt": "2026-05-11T10:00:00Z"},
        {"commentId": "c7", "author": "吴明", "content": "完整质量体系对小团队成本过高，这个要考虑。", "likeCount": 14, "createdAt": "2026-05-11T11:30:00Z"},
        {"commentId": "c8", "author": "郑芳", "content": "工具调用链路应该有明确的日志和回放，方便排查问题。", "likeCount": 10, "createdAt": "2026-05-11T13:00:00Z"},
        {"commentId": "c9", "author": "孙工", "content": "把软件测试范式直接套用到 Agent 不一定合适，需要新的方法论。", "likeCount": 9, "createdAt": "2026-05-11T15:00:00Z"},
        {"commentId": "c10", "author": "刘强", "content": "能分享一次工具调用失败导致 Agent 持续给出错误结论的真实案例吗？", "likeCount": 7, "createdAt": "2026-05-12T08:00:00Z"},
    ],
}


# Mock FeedbackAnalysis data
MOCK_ANALYSES: dict[str, dict[str, Any]] = {
    "article-moat": {
        "articleId": "article-moat",
        "generatedAt": "2026-05-12T10:30:00Z",
        "performanceSummary": "文章获得较好互动，读者认同企业研发流程的重要性，但有读者提出上下文窗口可能弱化壁垒的质疑。",
        "readerSignals": [
            {"type": "agree", "summary": "企业研发流程比单次生成更重要", "commentIds": ["c1", "c3"], "severity": "high"},
            {"type": "disagree", "summary": "大上下文窗口可能弱化壁垒", "commentIds": ["c2"], "severity": "medium"},
            {"type": "evidence", "summary": "企业引入审计流程的实际案例", "commentIds": ["c5"], "severity": "medium"},
        ],
        "positiveFeedback": ["观点明确，切中要害", "企业视角独特"],
        "negativeFeedback": ["缺少具体数据支撑", "未讨论中小企业情况"],
        "openQuestions": ["上下文窗口增长会如何影响这个壁垒？", "中小企业如何落地？"],
        "counterArguments": ["大上下文窗口可能弱化壁垒", "平台型公司可能直接整合"],
        "missingMaterials": ["企业审计流程的具体数据", "中小企业案例"],
        "articlePortrait": {
            "strongestPoint": "企业研发流程视角独特",
            "weakestPoint": "缺少数据和案例支撑",
            "readerProfile": "关注AI工具落地的技术管理者",
            "controversyMap": ["上下文壁垒的持久性", "平台整合风险"],
            "styleFeedback": "逻辑清晰但偏理论化",
            "nextImprovement": "补充企业调研数据和真实案例",
        },
        "secondArticleIdeas": [
            {
                "ideaId": "idea-1",
                "title": "AI Coding 的企业壁垒：权限、安全和组织知识库",
                "angle": "从企业安全和知识管理角度探讨AI工具的真正壁垒",
                "reason": "多位读者提到权限和安全审计的重要性",
                "sourceCommentIds": ["c3", "c5"],
                "suggestedArticleType": "article",
            },
            {
                "ideaId": "idea-2",
                "title": "工作流入口竞争如何影响开发者工具生态？",
                "angle": "从平台竞争角度分析AI工具的未来格局",
                "reason": "有读者指出平台整合风险",
                "sourceCommentIds": ["c4"],
                "suggestedArticleType": "commentary",
            },
        ],
        "seedCandidates": [
            {
                "candidateId": "sc-1",
                "title": "企业AI工具的真正护城河在安全审计",
                "coreClaim": "企业级AI工具的核心竞争力在于安全审计和权限管理，而非代码生成能力",
                "sourceCommentIds": ["c3", "c5"],
                "reason": "多位读者提到权限和安全审计的重要性",
                "suggestedMaterials": {
                    "evidence": ["企业引入审计流程的案例"],
                    "counterargument": ["小团队可能不需要复杂审计"],
                    "openQuestion": ["审计成本如何控制？"],
                },
            },
        ],
        "memoryUpdateCandidates": [
            {
                "candidateId": "mc-1",
                "interestId": "ai-coding",
                "targetField": "writingReminder",
                "suggestedValue": "写AI工具相关文章时，注意补充企业安全和权限管理的视角",
                "reason": "读者对企业安全视角反馈积极",
                "sourceArticleId": "article-moat",
            },
        ],
    },
    "article-quality": {
        "articleId": "article-quality",
        "generatedAt": "2026-05-12T10:30:00Z",
        "performanceSummary": "文章框架清晰但偏理论化，读者强烈要求补充真实失败案例和可观测性实践。",
        "readerSignals": [
            {"type": "agree", "summary": "Agent失败需要可观测性", "commentIds": ["c6", "c8"], "severity": "high"},
            {"type": "disagree", "summary": "质量体系对小团队成本过高", "commentIds": ["c7"], "severity": "medium"},
            {"type": "question", "summary": "请求分享真实失败案例", "commentIds": ["c10"], "severity": "high"},
        ],
        "positiveFeedback": ["框架清晰", "问题定义准确"],
        "negativeFeedback": ["缺少真实案例", "未讨论成本问题"],
        "openQuestions": ["真实失败案例是什么样的？", "小团队如何低成本实现？"],
        "counterArguments": ["完整质量体系对小团队成本过高", "软件测试范式不适合Agent"],
        "missingMaterials": ["工具调用失败的真实案例", "小团队实践方案"],
        "articlePortrait": {
            "strongestPoint": "问题定义清晰，框架完整",
            "weakestPoint": "缺少真实案例和数据",
            "readerProfile": "关注Agent工程化的技术负责人",
            "controversyMap": ["质量体系的成本效益", "测试范式的适用性"],
            "styleFeedback": "偏理论化，需要更多实践内容",
            "nextImprovement": "补充1-2个真实失败案例和复盘过程",
        },
        "secondArticleIdeas": [
            {
                "ideaId": "idea-3",
                "title": "Agent 工程化的最小可观测性清单",
                "angle": "从最小可行角度介绍Agent可观测性实践",
                "reason": "多位读者关注可观测性实现",
                "sourceCommentIds": ["c6", "c8"],
                "suggestedArticleType": "answer",
            },
            {
                "ideaId": "idea-4",
                "title": "为什么 Agent 失败模式比成功率更值得讨论？",
                "angle": "从失败学习角度探讨Agent质量",
                "reason": "有读者请求真实失败案例",
                "sourceCommentIds": ["c10"],
                "suggestedArticleType": "commentary",
            },
        ],
        "seedCandidates": [
            {
                "candidateId": "sc-2",
                "title": "Agent可观测性的最小可行方案",
                "coreClaim": "Agent工程化应该从最小可观测性清单开始，而不是追求完整的质量体系",
                "sourceCommentIds": ["c6", "c7", "c8"],
                "reason": "读者对可观测性和成本问题都有强烈反馈",
                "suggestedMaterials": {
                    "evidence": ["工具调用链路日志实践"],
                    "counterargument": ["小团队可能连最小方案都难以落地"],
                    "openQuestion": ["最小清单具体包含哪些内容？"],
                },
            },
        ],
        "memoryUpdateCandidates": [
            {
                "candidateId": "mc-2",
                "interestId": "agent",
                "targetField": "feedbackSummary",
                "suggestedValue": "读者反馈：需要更多真实案例，关注成本效益，对可观测性实践感兴趣",
                "reason": "读者普遍反馈缺少真实案例",
                "sourceArticleId": "article-quality",
            },
            {
                "candidateId": "mc-3",
                "interestId": "agent",
                "targetField": "writingReminder",
                "suggestedValue": "写Agent相关文章时，注意补充真实失败案例，避免纯理论框架",
                "reason": "读者对真实案例的需求强烈",
                "sourceArticleId": "article-quality",
            },
        ],
    },
}
