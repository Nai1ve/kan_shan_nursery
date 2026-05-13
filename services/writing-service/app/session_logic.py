from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


VALID_TONES = {"balanced", "sharp", "steady"}
DRAFT_STATUSES = ["claim_confirming", "blueprint_ready", "draft_ready", "reviewing", "finalized", "published"]


class SessionNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


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


def _build_blueprint(claim: str, llm_client=None, session: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {"coreClaim": claim, "interestId": session.get("interestId", "")}
            result = llm_client.argument_blueprint(
                seed=seed,
                materials=[],
                memory=memory,
                article_type=session.get("articleType", "deep_analysis"),
            )
            return {
                "centralClaim": result.get("coreClaim", claim),
                "background": result.get("outline", [{}])[0].get("section", "背景") if result.get("outline") else f'围绕"{claim}"近期出现的新讨论和案例。',
                "arguments": [
                    {
                        "title": point.get("section", "论证"),
                        "explanationPoints": point.get("points", []),
                    }
                    for point in result.get("outline", [])
                ] or [
                    {
                        "title": "正方支撑：现实趋势",
                        "explanationPoints": ["近期社区讨论已经出现明显倾向", "可以引用一个真实项目复盘作为例证"],
                    },
                ],
                "counterArgument": result.get("counterResponses", [""])[0] if result.get("counterResponses") else "反方认为这个判断对小团队或非企业场景过度概括。",
                "responseStrategy": "在文章中明确写出适用边界，并补充一个反例避免过度推广。",
                "suggestedPersonalExperience": [
                    "一次复杂系统交付中的真实判断",
                    "AI 编程工具在你工作流里的实际使用感受",
                ],
            }
        except Exception:
            pass  # Fallback to mock below

    return {
        "centralClaim": claim,
        "background": f'围绕"{claim}"近期出现的新讨论和案例。',
        "arguments": [
            {
                "title": "正方支撑：现实趋势",
                "explanationPoints": [
                    "近期社区讨论已经出现明显倾向",
                    "可以引用一个真实项目复盘作为例证",
                ],
            },
            {
                "title": "工程视角：可控交付",
                "explanationPoints": [
                    "把判断落到工程基本功上",
                    "用边界、状态、责任三个维度组织论证",
                ],
            },
            {
                "title": "反方边界：哪些场景不成立",
                "explanationPoints": [
                    "承认部分场景下结论需要弱化",
                    "提出可衡量的反方判断条件",
                ],
            },
        ],
        "counterArgument": "反方认为这个判断对小团队或非企业场景过度概括。",
        "responseStrategy": "在文章中明确写出适用边界，并补充一个反例避免过度推广。",
        "suggestedPersonalExperience": [
            "一次复杂系统交付中的真实判断",
            "AI 编程工具在你工作流里的实际使用感受",
        ],
    }


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
                "outline": blueprint.get("arguments", []),
                "body": result.get("body", f'以"{claim}"为核心，本文从工程视角拆开三层判断，并回应当前讨论中常见的反方质疑。'),
                "aiDisclosureSuggestion": result.get("aiDisclosureSuggestion", "建议在发布时标注 AI 辅助整理。"),
                "schemaVersion": "writing.draft.v1",
            }
        except Exception:
            pass  # Fallback to mock below

    return {
        "title": f"关于 {claim} 的工程视角",
        "tone": tone,
        "outline": [
            "热点引入：当前讨论与个人立场",
            "工程视角：边界、状态、责任三层判断",
            "反方回应：哪些场景下结论需要弱化",
            "落地结论：一个可被检验的判断",
        ],
        "body": (
            f'以"{claim}"为核心，本文从工程视角拆开三层判断，并回应当前讨论中常见的反方质疑。'
        ),
        "schemaVersion": "writing.draft.v1",
    }


def _build_roundtable(claim: str, llm_client=None, session: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_client and session:
        try:
            memory = session.get("memoryOverride") or _default_memory_for_interest(session.get("interestId", ""))
            seed = {"coreClaim": claim, "interestId": session.get("interestId", "")}
            draft = session.get("draft", {})
            result = llm_client.roundtable_review(
                seed=seed,
                draft=draft,
                memory=memory,
            )
            reviews = result.get("reviews", [])
            return {
                "reviewers": [
                    {
                        "role": review.get("role", "评审"),
                        "comments": review.get("problems", []) + review.get("suggestions", []),
                        "suggestion": review.get("suggestions", [""])[0] if review.get("suggestions") else "",
                    }
                    for review in reviews
                ] or [
                    {
                        "role": "工程视角评审",
                        "comments": [f'主张"{claim}"是否落到具体工程动作？', "是否补充了真实项目案例？"],
                        "suggestion": "建议在第二段加入一次真实项目交付经历。",
                    },
                ],
                "schemaVersion": "writing.roundtable.v1",
            }
        except Exception:
            pass  # Fallback to mock below

    return {
        "reviewers": [
            {
                "role": "工程视角评审",
                "comments": [
                    f'主张"{claim}"是否落到具体工程动作？',
                    "是否补充了真实项目案例？",
                ],
                "suggestion": "建议在第二段加入一次真实项目交付经历。",
            },
            {
                "role": "反方质疑",
                "comments": [
                    "结论是否过度概括？",
                    "是否回应了小团队 / 非企业场景？",
                ],
                "suggestion": "建议明确写出适用边界。",
            },
            {
                "role": "读者代表",
                "comments": [
                    "读完是否能记住一个有判断力的结论？",
                    "是否有 AI 套话或排比？",
                ],
                "suggestion": "建议精简排比，强化一个可被反驳的具体判断。",
            },
        ],
        "schemaVersion": "writing.roundtable.v1",
    }


def _build_finalized(claim: str) -> dict[str, Any]:
    return {
        "title": f"定稿：{claim}",
        "summary": f'围绕"{claim}"的工程视角文章定稿，未自动发布，等待用户确认。',
        "publishingNotice": "请在知乎手动确认发布；本系统不会自动调用真实发布接口。",
    }
