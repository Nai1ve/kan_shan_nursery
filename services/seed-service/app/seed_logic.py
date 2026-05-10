from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def build_material(material_type: str, title: str, content: str, source_label: str, adopted: bool) -> dict[str, Any]:
    return {
        "id": create_id("material"),
        "type": material_type,
        "title": title,
        "content": content,
        "sourceLabel": source_label,
        "adopted": adopted,
        "createdAt": now_iso(),
    }


def recalc_seed(seed: dict[str, Any]) -> dict[str, Any]:
    adopted_types = {item["type"] for item in seed.get("wateringMaterials", []) if item.get("adopted")}
    resolved_questions = [item for item in seed.get("questions", []) if item.get("status") == "resolved"]
    score = min(96, 32 + len(adopted_types) * 14 + len(seed.get("questions", [])) * 3 + len(resolved_questions) * 4)
    next_seed = {**seed, "maturityScore": score}
    if next_seed.get("status") not in {"writing", "published"}:
        next_seed["status"] = "sproutable" if score >= 70 else "water_needed"
    return next_seed


def build_seed_from_card(card: dict[str, Any], reaction: str, user_note: str | None = None, seed_id: str | None = None) -> dict[str, Any]:
    sources = card.get("originalSources", [])
    first_source = sources[0] if sources else {}
    controversies = card.get("controversies", [])
    writing_angles = card.get("writingAngles", [])
    created_at = now_iso()
    seed = {
        "id": seed_id or create_id("seed"),
        "interestId": card.get("categoryId", "unknown"),
        "title": (writing_angles[0] if writing_angles else card.get("title", "未命名观点种子")),
        "interestName": card.get("categoryId", "unknown"),
        "source": " / ".join([tag.get("label", "") for tag in card.get("tags", []) if tag.get("label")]) or first_source.get("sourceType", "content_card"),
        "sourceTitle": card.get("title", ""),
        "sourceSummary": card.get("contentSummary", ""),
        "sourceUrl": first_source.get("sourceUrl", ""),
        "sourceType": first_source.get("sourceType", "content_card"),
        "userReaction": reaction,
        "userNote": user_note or reaction,
        "coreClaim": writing_angles[0] if writing_angles else card.get("title", ""),
        "possibleAngles": writing_angles,
        "counterArguments": controversies,
        "requiredMaterials": ["补充个人经验", "补充反方回应", "补充可引用来源"],
        "wateringMaterials": [
            build_material(
                "evidence",
                "来源证据",
                first_source.get("rawExcerpt") or card.get("contentSummary", ""),
                first_source.get("sourceType", "内容卡片"),
                True,
            ),
            build_material(
                "counterargument",
                "主要争议",
                controversies[0] if controversies else "需要补充反方观点",
                "内容卡片",
                reaction == "disagree",
            ),
        ],
        "questions": [],
        "status": "water_needed",
        "maturityScore": 45,
        "createdFromCardId": card.get("id"),
        "createdAt": created_at,
        "updatedAt": created_at,
    }
    return recalc_seed(seed)


def build_manual_seed(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = now_iso()
    seed = {
        "id": payload.get("id") or create_id("seed"),
        "interestId": payload.get("interestId", "manual"),
        "title": payload.get("title", "手动观点种子"),
        "interestName": payload.get("interestName", payload.get("interestId", "manual")),
        "source": payload.get("source", "用户手动创建"),
        "sourceTitle": payload.get("sourceTitle", payload.get("title", "手动观点种子")),
        "sourceSummary": payload.get("sourceSummary", payload.get("userNote", "")),
        "sourceUrl": payload.get("sourceUrl", ""),
        "sourceType": payload.get("sourceType", "manual"),
        "userReaction": payload.get("userReaction", "manual"),
        "userNote": payload.get("userNote", ""),
        "coreClaim": payload.get("coreClaim", payload.get("title", "")),
        "possibleAngles": payload.get("possibleAngles") or [payload.get("coreClaim", payload.get("title", ""))],
        "counterArguments": payload.get("counterArguments") or ["这个判断是否有足够证据？"],
        "requiredMaterials": payload.get("requiredMaterials") or ["补充个人经验", "补充反方回应"],
        "wateringMaterials": payload.get("wateringMaterials") or [],
        "questions": payload.get("questions") or [],
        "status": payload.get("status", "water_needed"),
        "maturityScore": payload.get("maturityScore", 35),
        "createdFromCardId": payload.get("createdFromCardId"),
        "createdAt": payload.get("createdAt", created_at),
        "updatedAt": now_iso(),
    }
    return recalc_seed(seed)


def answer_question(seed: dict[str, Any], question: str, parent_question_id: str | None = None) -> dict[str, Any]:
    question_id = create_id("question")
    thread_id = parent_question_id or create_id("thread")
    answer = (
        f"针对“{question}”，Agent 的 mock 判断是：先拆成事实判断和价值判断。"
        f"事实层需要补来源证据，价值层需要连接你的个人经验和观点边界。"
    )
    material_type = "counterargument" if any(word in question for word in ["反方", "质疑", "漏洞", "风险", "不足", "边界"]) else "evidence"
    question_record = {
        "id": question_id,
        "threadId": thread_id,
        "parentQuestionId": parent_question_id,
        "question": question,
        "agentAnswer": answer,
        "citedSourceIds": [],
        "status": "answered",
        "createdAt": now_iso(),
    }
    next_seed = {
        **seed,
        "questions": [question_record, *seed.get("questions", [])],
        "wateringMaterials": [
            build_material("open_question", "用户疑问", question, "有疑问按钮", False),
            build_material(material_type, "Agent 回答", answer, "Agent 问答", True),
            *seed.get("wateringMaterials", []),
        ],
        "updatedAt": now_iso(),
    }
    return recalc_seed(next_seed)


def mark_question(seed: dict[str, Any], question_id: str, status: str) -> dict[str, Any]:
    target = next((item for item in seed.get("questions", []) if item.get("id") == question_id), None)
    if not target:
        raise ValueError(f"question not found: {question_id}")
    next_materials = seed.get("wateringMaterials", [])
    next_materials = [
        {**item, "adopted": status == "resolved"}
        if item.get("type") == "open_question" and item.get("content") == target.get("question")
        else item
        for item in next_materials
    ]
    next_seed = {
        **seed,
        "questions": [
            {**item, "status": status} if item.get("id") == question_id else item
            for item in seed.get("questions", [])
        ],
        "wateringMaterials": next_materials,
        "updatedAt": now_iso(),
    }
    return recalc_seed(next_seed)


def agent_supplement(seed: dict[str, Any], material_type: str) -> dict[str, Any]:
    if material_type == "counterargument":
        material = build_material(
            "counterargument",
            "Agent 找到反方质疑",
            f"针对“{seed.get('coreClaim', '')}”，反方可能会质疑当前证据是否足以支持这个判断。",
            "继续浇水 / Agent 找反方",
            True,
        )
    else:
        material = build_material(
            "evidence",
            "Agent 补充事实证据",
            f"围绕“{seed.get('sourceTitle', '')}”，建议补充可验证来源和具体场景来支撑观点。",
            "继续浇水 / Agent 补证据",
            True,
        )
    return recalc_seed({**seed, "wateringMaterials": [material, *seed.get("wateringMaterials", [])], "updatedAt": now_iso()})
