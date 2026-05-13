from __future__ import annotations

from typing import Any

from .base import Provider, ProviderResult


def _pick_title(input_data: dict[str, Any]) -> str:
    seed = input_data.get("seed") or {}
    card = input_data.get("card") or {}
    return seed.get("title") or card.get("title") or input_data.get("title") or "未命名主题"


def _pick_claim(input_data: dict[str, Any]) -> str:
    seed = input_data.get("seed") or {}
    return seed.get("coreClaim") or input_data.get("coreClaim") or _pick_title(input_data)


def _sources(input_data: dict[str, Any]) -> list[dict[str, Any]]:
    card = input_data.get("card") or {}
    explicit_sources = input_data.get("sources") or []
    return explicit_sources or card.get("originalSources") or []


def run_mock_task(task_type: str, input_data: dict[str, Any], persona: str | None = None) -> dict[str, Any]:
    if task_type == "roundtable-review" and persona:
        return _roundtable_persona(persona, input_data)
    handlers = {
        "summarize-content": _summarize_content,
        "extract-controversies": _extract_controversies,
        "generate-writing-angles": _generate_writing_angles,
        "answer-seed-question": _answer_seed_question,
        "supplement-material": _supplement_material,
        "sprout-opportunities": _sprout_opportunities,
        "argument-blueprint": _argument_blueprint,
        "draft": _draft,
        "roundtable-review": _roundtable_review,
        "feedback-summary": _feedback_summary,
        "profile-memory-synthesis": _profile_memory_synthesis,
    }
    try:
        return handlers[task_type](input_data)
    except KeyError as exc:
        raise ValueError(f"Unsupported taskType: {task_type}") from exc


class MockProvider:
    name = "mock"

    def run(
        self,
        task_type: str,
        input_data: dict[str, Any],
        prompt: str,
        persona: str | None = None,
    ) -> ProviderResult:
        output = run_mock_task(task_type, input_data, persona)
        return ProviderResult(output=output, provider_meta={"provider": self.name, "persona": persona})


def _summarize_content(input_data: dict[str, Any]) -> dict[str, Any]:
    title = _pick_title(input_data)
    source_ids = [item.get("sourceId") for item in _sources(input_data) if item.get("sourceId")]
    return {
        "summary": f"这组材料围绕“{title}”展开，核心价值是把信息输入转化为可讨论的观点。",
        "keyPoints": [
            "先区分事实判断、经验判断和价值判断。",
            "保留来源线索，避免脱离材料凭空生成。",
            "如果要成文，需要补充个人经验和反方回应。",
        ],
        "sourceIds": source_ids,
        "nextAction": "save_seed",
    }


def _extract_controversies(input_data: dict[str, Any]) -> dict[str, Any]:
    title = _pick_title(input_data)
    return {
        "controversies": [
            {
                "claim": f"支持方认为“{title}”已经具备写作价值。",
                "opposition": "反方会质疑证据是否充分，以及结论是否过度外推。",
                "whyItMatters": "争议越明确，越容易形成知乎式讨论。",
            },
            {
                "claim": "个人经验可以增强表达可信度。",
                "opposition": "但个人经验不能替代公共证据。",
                "whyItMatters": "这决定文章应偏经验复盘还是观点论证。",
            },
        ]
    }


def _generate_writing_angles(input_data: dict[str, Any]) -> dict[str, Any]:
    claim = _pick_claim(input_data)
    return {
        "angles": [
            {
                "title": claim,
                "angle": "从用户自己的阅读反应出发，解释为什么这个判断值得讨论。",
                "fitScore": 86,
            },
            {
                "title": f"反过来看：{claim}",
                "angle": "先承认反方担忧，再给出边界和条件。",
                "fitScore": 79,
            },
            {
                "title": "把抽象判断落到一个具体场景",
                "angle": "用个人项目经历或观察作为开头，降低模板感。",
                "fitScore": 74,
            },
        ]
    }


def _answer_seed_question(input_data: dict[str, Any]) -> dict[str, Any]:
    question = input_data.get("question") or input_data.get("userQuestion") or "这个观点是否成立？"
    claim = _pick_claim(input_data)
    needs_material = any(word in question for word in ["证据", "数据", "来源", "可靠", "证明"])
    return {
        "answer": (
            f"围绕“{claim}”，这个问题可以先拆成两层：材料是否能证明事实，"
            f"以及这些事实能不能支持你的判断。对“{question}”的当前回答是：可以作为写作方向，"
            "但需要补一条可引用证据和一个反方边界。"
        ),
        "statusRecommendation": "needs_material" if needs_material else "answered",
        "materials": [
            {
                "type": "evidence" if needs_material else "counterargument",
                "title": "Agent 问答补充",
                "content": "建议把来源摘要、精选评论和自己的项目观察放在同一段里交叉验证。",
                "adopted": True,
            }
        ],
        "followUpQuestions": ["这个判断在哪些场景下不成立？", "有没有一个你的个人经历能支撑它？"],
    }


def _supplement_material(input_data: dict[str, Any]) -> dict[str, Any]:
    material_type = input_data.get("materialType") or input_data.get("type") or "evidence"
    claim = _pick_claim(input_data)
    title = "Agent 补证据" if material_type == "evidence" else "Agent 找反方"
    content = (
        f"围绕“{claim}”，补一条事实证据：需要可追溯来源、时间和作者。"
        if material_type == "evidence"
        else f"围绕“{claim}”，反方可能认为当前论证忽略了样本偏差和适用边界。"
    )
    return {"material": {"type": material_type, "title": title, "content": content, "adopted": True}}


def _sprout_opportunities(input_data: dict[str, Any]) -> dict[str, Any]:
    seed = input_data.get("seed") or {}
    title = _pick_title(input_data)
    score = min(96, max(60, int(seed.get("maturityScore", 60)) + 8))
    return {
        "opportunities": [
            {
                "seedId": seed.get("id", "seed-mock"),
                "triggerTopic": title,
                "whyWorthWriting": "材料已有观点、争议和写作角度，适合转入写作苗圃。",
                "suggestedTitle": f"{title}，真正值得讨论的是什么？",
                "suggestedAngle": "先承认复杂性，再给出自己的判断边界。",
                "score": score,
            }
        ]
    }


def _argument_blueprint(input_data: dict[str, Any]) -> dict[str, Any]:
    claim = _pick_claim(input_data)
    return {
        "coreClaim": claim,
        "outline": [
            "问题为什么值得讨论",
            "现有材料分别支持什么",
            "我的判断边界是什么",
            "反方可能怎么质疑",
            "结论和行动建议",
        ],
        "counterResponses": ["承认反例存在，但限定讨论场景。", "用来源证据和个人经验分层回应。"],
        "memoryInjected": input_data.get("memory", {}),
    }


def _draft(input_data: dict[str, Any]) -> dict[str, Any]:
    claim = _pick_claim(input_data)
    return {
        "title": claim,
        "body": (
            f"我想讨论的不是一个简单的结论，而是“{claim}”背后的判断方式。\n\n"
            "先看材料：它提供了一个公共讨论入口，但还不足以直接推出最终结论。"
            "真正需要补上的，是个人经验、反方边界和可验证证据。\n\n"
            "所以这篇文章更适合写成观点澄清，而不是情绪表达。"
        ),
        "aiDisclosureSuggestion": "本文使用 AI 辅助梳理论证结构，核心观点和最终表达由作者确认。",
    }


def _roundtable_review(input_data: dict[str, Any]) -> dict[str, Any]:
    claim = _pick_claim(input_data)
    return {
        "reviews": [
            _roundtable_persona("logic_reviewer", input_data)["reviews"][0] | {"_synthesized": True},
            _roundtable_persona("opponent_reader", input_data)["reviews"][0] | {"_synthesized": True},
        ],
        "summary": f"针对“{claim}”，逻辑清晰但反方回应不足，建议补一段适用边界。",
    }


def _roundtable_persona(persona: str, input_data: dict[str, Any]) -> dict[str, Any]:
    claim = _pick_claim(input_data)
    catalog = {
        "logic_reviewer": {
            "summary": f"主张“{claim}”清楚，但论据层次还可以更分明。",
            "problems": ["事实证据和个人经验混在一起。", "结论的适用条件没有显式声明。"],
            "suggestions": ["把公共材料放前，个人经验放后。", "在结尾加一段 '在什么情况下我不这么认为'。"],
            "severity": "medium",
        },
        "human_editor": {
            "summary": "整体可读，但缺少真实细节，读起来略像 AI 模板。",
            "problems": ["没有具体场景或时间地点。", "排比偏多。"],
            "suggestions": ["选一段加入项目踩坑细节。", "把排比改成两到三句具体陈述。"],
            "severity": "medium",
        },
        "opponent_reader": {
            "summary": "反方角度看，结论可能过度外推。",
            "problems": ["样本是否充分没有说明。", "没有承认反例。"],
            "suggestions": ["补一段 '反方可能这样反驳'。", "明确写出适用边界。"],
            "severity": "high",
        },
        "community_editor": {
            "summary": "标题和开头可以更贴合知乎语境。",
            "problems": ["标题偏抽象，不够吸引点击。", "开头缺少代入感。"],
            "suggestions": ["标题改成提问式。", "开头加一句 '我最近遇到的事'。"],
            "severity": "low",
        },
    }
    review = catalog.get(persona) or catalog["logic_reviewer"]
    return {"reviews": [{"role": persona, **review}]}


def _feedback_summary(input_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": "反馈集中在观点有启发，但希望看到更多具体案例。",
        "signals": ["点赞来自认同观点", "评论集中追问证据", "收藏说明主题有长期价值"],
        "secondArticleIdeas": ["把本文的一个反方质疑展开成后续文章", "补一篇个人项目复盘作为案例"],
    }


def _profile_memory_synthesis(input_data: dict[str, Any]) -> dict[str, Any]:
    user = input_data.get("user") or {}
    nickname = user.get("nickname") or "用户"
    interests = user.get("interests") or []
    interactions = input_data.get("interactions") or {}
    reactions = interactions.get("seedReactions") or []

    # Build interest memories from user interests
    interest_memories = []
    for interest in interests:
        interest_memories.append({
            "interestId": interest,
            "interestName": interest,
            "knowledgeLevel": "中级",
            "preferredPerspective": [f"{interest}相关视角"],
            "evidencePreference": "个人经验 + 案例",
            "writingReminder": f"关于{interest}的内容，需要补充实际使用场景和案例分析",
            "feedbackSummary": "",
        })

    return {
        "globalMemory": {
            "longTermBackground": f"用户{nickname}，刚完成注册和兴趣选择。",
            "contentPreference": "偏好真实经历、问题拆解、反方质疑。更重视'为什么这样想'而不是单纯罗列信息。",
            "writingStyle": "清晰、克制；允许有观点锋芒，但避免标题党和情绪煽动。",
            "recommendationStrategy": "按兴趣小类展开；关注流和偶遇输入作为平级入口。每次推荐都要说明为什么值得看。",
            "riskReminder": "容易写成逻辑完整但缺少个人经历的文章；需要在写作阶段主动补充真实案例。",
        },
        "interestMemories": interest_memories,
        "confidence": "medium",
        "reasoning": "基于用户的兴趣选择和注册信息推断",
    }


__all__ = ["MockProvider", "run_mock_task"]
