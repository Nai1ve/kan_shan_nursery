from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


VALID_TONES = {"balanced", "sharp", "steady"}
DRAFT_STATUSES = [
    "claim_confirming",
    "blueprint_ready",
    "blueprint_confirmed",
    "outline_ready",
    "outline_confirmed",
    "draft_ready",
    "reviewing",
    "finalized",
    "published",
]

VALID_TRANSITIONS: dict[str, dict[str, Any]] = {
    "confirm_claim":             {"from": {"claim_confirming"},             "to": "claim_confirming"},
    "generate_blueprint":        {"from": {"claim_confirming"},             "to": "blueprint_ready"},
    "patch_blueprint":           {"from": {"blueprint_ready"},             "to": "blueprint_ready"},
    "regenerate_blueprint":      {"from": {"blueprint_ready"},             "to": "blueprint_ready"},
    "confirm_blueprint":         {"from": {"blueprint_ready"},             "to": "blueprint_confirmed"},
    "generate_outline":          {"from": {"blueprint_confirmed"},         "to": "outline_ready"},
    "patch_outline":             {"from": {"outline_ready"},              "to": "outline_ready"},
    "regenerate_outline_section": {"from": {"outline_ready"},             "to": "outline_ready"},
    "confirm_outline":           {"from": {"outline_ready"},              "to": "outline_confirmed"},
    "generate_draft":            {"from": {"outline_confirmed"},           "to": "draft_ready"},
    "start_roundtable":          {"from": {"draft_ready"},                "to": "reviewing"},
    "roundtable_author_message": {"from": {"reviewing"},                  "to": "reviewing"},
    "continue_roundtable":       {"from": {"reviewing"},                  "to": "reviewing"},
    "adopt_suggestion":          {"from": {"reviewing"},                  "to": "reviewing"},
    "finalize":                  {"from": {"reviewing", "draft_ready"},   "to": "finalized"},
    "publish_mock":              {"from": {"finalized"},                  "to": "published"},
}


class SessionNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


def check_transition(current_status: str, action: str) -> str:
    spec = VALID_TRANSITIONS.get(action)
    if not spec:
        raise InvalidTransition(f"unknown action: {action}")
    if current_status not in spec["from"]:
        raise InvalidTransition(
            f"cannot {action} from status {current_status}; "
            f"expected one of {sorted(spec['from'])}"
        )
    return spec["to"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _default_memory_for_interest(interest_id: str) -> dict[str, Any]:
    return {
        "interestId": interest_id,
        "interestName": interest_id,
        "knowledgeLevel": "中级",
        "preferredPerspective": ["工程视角", "案例驱动"],
        "evidencePreference": "案例 + 反方平衡",
        "writingReminder": "避免空泛结论，补充个人项目经验和反方边界。",
    }


# ---------------------------------------------------------------------------
# Blueprint builder
# ---------------------------------------------------------------------------

def _build_blueprint(claim: str, llm_client=None, session: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {
                "coreClaim": claim,
                "interestId": session.get("interestId", ""),
                "regenerateInstruction": session.get("regenerateInstruction", ""),
            }
            result = llm_client.argument_blueprint(
                seed=seed,
                materials=[],
                memory=memory,
                article_type=session.get("articleType", "deep_analysis"),
            )
            return _map_llm_blueprint(result, claim)
        except Exception:
            pass  # Fallback to mock below

    return {
        "centralClaim": claim,
        "mainThread": f'围绕"{claim}"，从工程视角拆开三层判断。',
        "argumentSteps": [
            {
                "id": _create_id("arg"),
                "title": "正方支撑：现实趋势",
                "purpose": "用趋势和案例建立论据基础",
                "keyPoints": [
                    "近期社区讨论已经出现明显倾向",
                    "可以引用一个真实项目复盘作为例证",
                ],
            },
            {
                "id": _create_id("arg"),
                "title": "工程视角：可控交付",
                "purpose": "把判断落到工程基本功上",
                "keyPoints": [
                    "用边界、状态、责任三个维度组织论证",
                ],
            },
            {
                "id": _create_id("arg"),
                "title": "反方边界：哪些场景不成立",
                "purpose": "承认部分场景下结论需要弱化",
                "keyPoints": [
                    "提出可衡量的反方判断条件",
                ],
            },
        ],
        "counterArguments": ["反方认为这个判断对小团队或非企业场景过度概括。"],
        "responseStrategy": "在文章中明确写出适用边界，并补充一个反例避免过度推广。",
        "personalExperienceNeeded": [
            "一次复杂系统交付中的真实判断",
            "AI 编程工具在你工作流里的实际使用感受",
        ],
        "riskNotes": ["结论可能过度概括", "需要避免模板化表达"],
    }


def _map_llm_blueprint(result: dict[str, Any], fallback_claim: str) -> dict[str, Any]:
    core_claim = result.get("coreClaim", fallback_claim)
    outline_items = result.get("outline", [])
    argument_steps = []
    for item in outline_items:
        if isinstance(item, str):
            argument_steps.append({
                "id": _create_id("arg"),
                "title": item,
                "purpose": "展开论证",
                "keyPoints": [],
            })
        elif isinstance(item, dict):
            argument_steps.append({
                "id": _create_id("arg"),
                "title": item.get("section", item.get("title", "论证")),
                "purpose": item.get("purpose", "展开论证"),
                "keyPoints": item.get("points", item.get("keyPoints", [])),
            })
    if not argument_steps:
        argument_steps = [
            {"id": _create_id("arg"), "title": "主体论证", "purpose": "展开核心观点", "keyPoints": []},
        ]
    counter_responses = result.get("counterResponses", [])
    personal_prompts = result.get("personalExperiencePrompts", result.get("personalExperienceNeeded", []))
    return {
        "centralClaim": core_claim,
        "mainThread": result.get("mainThread", f'围绕"{core_claim}"展开论证。'),
        "argumentSteps": argument_steps,
        "counterArguments": counter_responses if isinstance(counter_responses, list) else [str(counter_responses)],
        "responseStrategy": result.get("responseStrategy", "明确适用边界，回应反方质疑。"),
        "personalExperienceNeeded": personal_prompts if isinstance(personal_prompts, list) else [],
        "riskNotes": result.get("riskNotes", ["需要避免模板化表达"]),
    }


# ---------------------------------------------------------------------------
# Outline builder
# ---------------------------------------------------------------------------

def _build_outline(
    blueprint: dict[str, Any],
    materials: list[dict[str, Any]],
    llm_client=None,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            result = llm_client.generate_outline(
                blueprint=blueprint,
                materials=materials,
                memory=memory,
            )
            sections = result.get("sections", [])
            if sections:
                return {"sections": sections}
        except Exception:
            pass  # Fallback to mock

    # Mock: derive sections from blueprint argumentSteps
    sections = []
    for step in blueprint.get("argumentSteps", []):
        sections.append({
            "id": step.get("id", _create_id("sec")),
            "title": step.get("title", "章节"),
            "purpose": step.get("purpose", "展开论证"),
            "keyPoints": step.get("keyPoints", []),
            "referencedMaterialIds": [],
            "referencedSourceIds": [],
            "missingMaterialHints": ["建议补充相关来源材料"],
        })
    if not sections:
        claim = blueprint.get("centralClaim", "核心观点")
        sections = [
            {
                "id": _create_id("sec"),
                "title": "引言",
                "purpose": "提出问题",
                "keyPoints": [f"引入核心争议：{claim}"],
                "referencedMaterialIds": [],
                "referencedSourceIds": [],
                "missingMaterialHints": [],
            },
            {
                "id": _create_id("sec"),
                "title": "主体论证",
                "purpose": "展开核心观点",
                "keyPoints": ["提供论据支撑", "回应反方质疑"],
                "referencedMaterialIds": [],
                "referencedSourceIds": [],
                "missingMaterialHints": ["需要可引用的证据材料"],
            },
            {
                "id": _create_id("sec"),
                "title": "结论",
                "purpose": "总结判断边界",
                "keyPoints": ["给出可被检验的结论"],
                "referencedMaterialIds": [],
                "referencedSourceIds": [],
                "missingMaterialHints": [],
            },
        ]
    return {"sections": sections}


# ---------------------------------------------------------------------------
# Draft builder
# ---------------------------------------------------------------------------

def _build_draft(claim: str, tone: str, llm_client=None, session: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {"coreClaim": claim, "interestId": session.get("interestId", "")}
            blueprint = session.get("blueprint", {})
            result = llm_client.draft(
                seed=seed,
                materials=[],
                blueprint=blueprint,
                memory=memory,
                tone=tone,
            )
            return {
                "title": result.get("title", f"关于 {claim} 的工程视角"),
                "tone": tone,
                "outline": session.get("outline", {}).get("sections", []),
                "body": result.get("body", f'以"{claim}"为核心，本文从工程视角拆开三层判断，并回应当前讨论中常见的反方质疑。'),
                "aiDisclosureSuggestion": result.get("aiDisclosureSuggestion", "建议在发布时标注 AI 辅助整理。"),
                "schemaVersion": "writing.draft.v1",
            }
        except Exception:
            pass  # Fallback to mock below

    outline_sections = session.get("outline", {}).get("sections", []) if session else []
    section_titles = [s.get("title", "") for s in outline_sections] if outline_sections else [
        "热点引入：当前讨论与个人立场",
        "工程视角：边界、状态、责任三层判断",
        "反方回应：哪些场景下结论需要弱化",
        "落地结论：一个可被检验的判断",
    ]
    return {
        "title": f"关于 {claim} 的工程视角",
        "tone": tone,
        "outline": section_titles,
        "body": (
            f'以"{claim}"为核心，本文从工程视角拆开三层判断，并回应当前讨论中常见的反方质疑。'
        ),
        "schemaVersion": "writing.draft.v1",
    }


# ---------------------------------------------------------------------------
# Roundtable state management
# ---------------------------------------------------------------------------

def _init_roundtable_state(claim: str, llm_client=None, session: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {"coreClaim": claim, "interestId": session.get("interestId", "")}
            draft = session.get("draft", {})
            result = llm_client.roundtable_review(seed=seed, draft=draft, memory=memory)
            return _reviews_to_roundtable_state(result.get("reviews", []), claim)
        except Exception:
            pass  # Fallback to mock

    return _mock_roundtable_state(claim)


def _reviews_to_roundtable_state(reviews: list[dict[str, Any]], claim: str) -> dict[str, Any]:
    turns: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    for review in reviews:
        role = review.get("role", "reviewer")
        summary = review.get("summary", "")
        problems = review.get("problems", [])
        suggs = review.get("suggestions", [])
        severity = review.get("severity", "medium")
        content_parts = [summary] if summary else []
        if problems:
            content_parts.append("问题：" + "；".join(problems))
        if suggs:
            content_parts.append("建议：" + "；".join(suggs))
        turns.append({
            "id": _create_id("turn"),
            "role": role,
            "content": "\n".join(content_parts) if content_parts else f"针对\"{claim}\"的审稿意见。",
            "createdAt": _now_iso(),
        })
        for s in suggs:
            suggestions.append({
                "id": _create_id("sug"),
                "fromRole": role,
                "content": s,
                "severity": severity,
                "adopted": False,
            })
    if not turns:
        return _mock_roundtable_state(claim)
    return {"status": "active", "turns": turns, "suggestions": suggestions}


def _mock_roundtable_state(claim: str) -> dict[str, Any]:
    roles = [
        ("logic_reviewer", "工程视角评审", "medium",
         [f'主张"{claim}"是否落到具体工程动作？', "是否补充了真实项目案例？"],
         ["建议在第二段加入一次真实项目交付经历。"]),
        ("human_editor", "人文编辑", "medium",
         ["整体可读，但缺少真实细节，读起来略像 AI 模板。", "排比偏多。"],
         ["选一段加入项目踩坑细节。", "把排比改成两到三句具体陈述。"]),
        ("opponent_reader", "反方读者", "high",
         ["反方角度看，结论可能过度外推。", "样本是否充分没有说明。"],
         ["补一段 '反方可能这样反驳'。", "明确写出适用边界。"]),
        ("community_editor", "社区编辑", "low",
         ["标题和开头可以更贴合知乎语境。", "开头缺少代入感。"],
         ["标题改成提问式。", "开头加一句 '我最近遇到的事'。"]),
    ]
    turns: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    for role_id, role_name, severity, problems, suggs in roles:
        content = f"【{role_name}】\n问题：{'；'.join(problems)}\n建议：{'；'.join(suggs)}"
        turns.append({
            "id": _create_id("turn"),
            "role": role_id,
            "content": content,
            "createdAt": _now_iso(),
        })
        for s in suggs:
            suggestions.append({
                "id": _create_id("sug"),
                "fromRole": role_id,
                "content": s,
                "severity": severity,
                "adopted": False,
            })
    return {"status": "active", "turns": turns, "suggestions": suggestions}


def _build_roundtable_author_message(roundtable_state: dict[str, Any], content: str) -> dict[str, Any]:
    state = {**roundtable_state}
    turns = list(state.get("turns", []))
    turns.append({
        "id": _create_id("turn"),
        "role": "author",
        "content": content,
        "createdAt": _now_iso(),
    })
    state["turns"] = turns
    return state


def _continue_roundtable(
    roundtable_state: dict[str, Any],
    claim: str,
    llm_client=None,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = {**roundtable_state}
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {"coreClaim": claim, "interestId": session.get("interestId", "")}
            draft = session.get("draft", {})
            result = llm_client.roundtable_review(seed=seed, draft=draft, memory=memory)
            new_reviews = result.get("reviews", [])
            turns = list(state.get("turns", []))
            suggestions = list(state.get("suggestions", []))
            for review in new_reviews:
                role = review.get("role", "reviewer")
                suggs = review.get("suggestions", [])
                content_parts = []
                if review.get("summary"):
                    content_parts.append(review["summary"])
                if review.get("problems"):
                    content_parts.append("问题：" + "；".join(review["problems"]))
                if suggs:
                    content_parts.append("建议：" + "；".join(suggs))
                turns.append({
                    "id": _create_id("turn"),
                    "role": role,
                    "content": "\n".join(content_parts) if content_parts else f"针对\"{claim}\"的后续讨论。",
                    "createdAt": _now_iso(),
                })
                for s in suggs:
                    suggestions.append({
                        "id": _create_id("sug"),
                        "fromRole": role,
                        "content": s,
                        "severity": review.get("severity", "medium"),
                        "adopted": False,
                    })
            state["turns"] = turns
            state["suggestions"] = suggestions
            return state
        except Exception:
            pass

    # Mock: add a follow-up turn acknowledging the discussion
    turns = list(state.get("turns", []))
    turns.append({
        "id": _create_id("turn"),
        "role": "logic_reviewer",
        "content": f"收到作者的回应。针对\"{claim}\"，建议进一步明确判断的适用条件，并补充一个可验证的案例。",
        "createdAt": _now_iso(),
    })
    state["turns"] = turns
    return state


def _adopt_suggestion(roundtable_state: dict[str, Any], suggestion_id: str) -> dict[str, Any]:
    state = {**roundtable_state}
    suggestions = list(state.get("suggestions", []))
    found = False
    for i, sug in enumerate(suggestions):
        if sug.get("id") == suggestion_id:
            suggestions[i] = {**sug, "adopted": True}
            found = True
            break
    if not found:
        raise ValueError(f"suggestion {suggestion_id} not found")
    state["suggestions"] = suggestions
    return state


# ---------------------------------------------------------------------------
# Finalized builder
# ---------------------------------------------------------------------------

def _build_finalized(claim: str) -> dict[str, Any]:
    return {
        "title": f"定稿：{claim}",
        "summary": f'围绕"{claim}"的工程视角文章定稿，未自动发布，等待用户确认。',
        "publishingNotice": "请在知乎手动确认发布；本系统不会自动调用真实发布接口。",
    }
