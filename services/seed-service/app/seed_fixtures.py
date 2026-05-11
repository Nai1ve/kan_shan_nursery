"""Seed fixtures preloaded into the in-memory repository.

These seeds match the two demo seeds that the frontend mock-data.ts has
historically shown so the gateway-backed view shows the same starting
state as the legacy /api/mock/seeds route. They use stable ids so a
demo-mode reset still finds them.
"""

from __future__ import annotations

from typing import Any


CREATED_AT = "2026-05-09T09:00:00+08:00"


SEED_FIXTURES: list[dict[str, Any]] = [
    {
        "id": "seed-ai-coding-moat",
        "interestId": "ai-coding",
        "title": "AI 编程工具的护城河可能不在代码生成",
        "interestName": "AI Coding",
        "source": "知乎热榜 / 搜索结果 / 用户手动记录",
        "sourceTitle": "AI Coding 产品的壁垒到底在哪里？",
        "sourceSummary": "近期讨论集中在 AI 编程工具是否会替代程序员，以及代码生成能力是否会快速同质化。",
        "sourceUrl": "https://mock.zhihu.local/ai-coding/4/answer",
        "sourceType": "zhihu_search",
        "userReaction": "agree",
        "userNote": "我认同代码生成会越来越普遍，但不认为这就是最终壁垒。",
        "coreClaim": "单纯代码生成工具的护城河很浅，真正的壁垒可能在上下文积累、工作流入口、团队协作和企业数据闭环。",
        "possibleAngles": [
            "AI 编程工具为什么会快速同质化？",
            "企业真正需要的是代码，还是可控的工程交付？",
            "Agent 产品的护城河到底在哪里？",
        ],
        "counterArguments": [
            "如果模型足够强，是否也能理解上下文？",
            "工作流入口是否会被平台垄断？",
        ],
        "requiredMaterials": ["AI 编程产品案例", "企业研发流程", "自己做复杂工程项目的经历"],
        "wateringMaterials": [
            {
                "id": "material-evidence-ai-coding-moat-001",
                "type": "evidence",
                "title": "代码生成能力正在同质化",
                "content": "多个 AI Coding 产品都把补全、生成测试、解释代码作为基础能力，差异正在从单点生成转向工作流。",
                "sourceLabel": "知乎搜索 / 高赞回答",
                "adopted": True,
                "createdAt": CREATED_AT,
            },
            {
                "id": "material-counterargument-ai-coding-moat-001",
                "type": "counterargument",
                "title": "长上下文模型可能削弱上下文壁垒",
                "content": "反方认为模型窗口和企业知识库能力提升后，上下文积累不一定形成长期壁垒。",
                "sourceLabel": "圈子评论",
                "adopted": True,
                "createdAt": CREATED_AT,
            },
            {
                "id": "material-personal-ai-coding-moat-001",
                "type": "personal_experience",
                "title": "复杂后端系统的真实难点",
                "content": "过去做金融软件和数据同步时，真正麻烦的是需求边界、状态变化、回滚追责，而不是写出某段代码。",
                "sourceLabel": "用户经验",
                "adopted": False,
                "createdAt": CREATED_AT,
            },
        ],
        "questions": [
            {
                "id": "q-ai-context",
                "question": "如果长上下文模型能读完整代码库，上下文还会是壁垒吗？",
                "agentAnswer": "长上下文能降低读取门槛，但企业上下文还包括权限、历史决策、流程责任和团队协作数据，这些不是一次性塞进窗口就能稳定使用的资产。",
                "citedSourceIds": ["source-ai-coding-4-hot", "source-ai-coding-4-answer"],
                "status": "answered",
                "createdAt": CREATED_AT,
            }
        ],
        "status": "sproutable",
        "maturityScore": 76,
        "activationScore": 87,
        "createdFromCardId": "ai-coding-moat",
        "createdAt": CREATED_AT,
        "updatedAt": CREATED_AT,
    },
    {
        "id": "seed-agent-quality",
        "interestId": "agent",
        "title": "Agent Quality 不能只看任务完成率",
        "interestName": "Agent 工程化",
        "source": "知乎搜索 / 关注作者 / 用户手动记录",
        "sourceTitle": "Agent Quality 到底评估什么？",
        "sourceSummary": "任务完成率被频繁讨论，但工具调用、上下文污染和失败恢复仍缺系统性框架。",
        "sourceUrl": "https://mock.zhihu.local/agent/0/answer",
        "sourceType": "zhihu_search",
        "userReaction": "agree",
        "userNote": "我认为 Agent 质量体系应该更接近工程可靠性评估，而不是单次问答评测。",
        "coreClaim": "Agent 不是一次回答，而是持续执行的工作流，质量评估应覆盖失败模式和可恢复性。",
        "possibleAngles": ["Agent Quality 的失败模式清单", "为什么任务完成率不是唯一指标"],
        "counterArguments": ["质量体系是否会增加开发负担？", "小团队是否需要完整测试框架？"],
        "requiredMaterials": ["真实工具调用失败案例", "可观测性和回放机制"],
        "wateringMaterials": [
            {
                "id": "material-evidence-agent-quality-001",
                "type": "evidence",
                "title": "任务完成率不能解释失败链路",
                "content": "只看最终成功与否无法定位工具调用、上下文污染、外部 API 异常等问题。",
                "sourceLabel": "关注流复盘",
                "adopted": True,
                "createdAt": CREATED_AT,
            },
            {
                "id": "material-open-question-agent-quality-001",
                "type": "open_question",
                "title": "Agent 质量体系会不会太重？",
                "content": "需要找到轻量化的 P0 质量清单，避免把原型做成大而全平台。",
                "sourceLabel": "用户疑问",
                "adopted": False,
                "createdAt": CREATED_AT,
            },
        ],
        "questions": [],
        "status": "water_needed",
        "maturityScore": 58,
        "createdFromCardId": "agent-quality",
        "createdAt": CREATED_AT,
        "updatedAt": CREATED_AT,
    },
]


def initial_seeds() -> list[dict[str, Any]]:
    """Return deep-copied fixtures so the in-memory repo can mutate freely."""
    import copy
    return copy.deepcopy(SEED_FIXTURES)
