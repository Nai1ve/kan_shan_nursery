from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone
from typing import Any

from . import mock_data
from .data_fetcher import SproutDataFetcher
from .filter import build_dismissed_pairs_from_opportunities, filter_candidates
from .scorer import compute_activation_score

logger = logging.getLogger("kanshan.sprout.service")


class RunNotFound(Exception):
    pass


class OpportunityNotFound(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    from uuid import uuid4
    return f"{prefix}-{uuid4().hex[:12]}"


class SproutService:
    def __init__(
        self,
        storage: Any = None,
        llm_client: Any = None,
        data_fetcher: SproutDataFetcher | None = None,
    ) -> None:
        self._storage = storage
        self._llm_client = llm_client
        self._data_fetcher = data_fetcher
        if self._storage:
            self._storage.load_initial_opportunities(mock_data.initial_opportunities())
        self._opportunities: dict[str, dict[str, Any]] = {
            item["id"]: item for item in mock_data.initial_opportunities()
        }
        self._runs: dict[str, dict[str, Any]] = {}
        self._cache_by_interest: dict[str, str] = {}
        self._dismissed_records: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _get_opp(self, opp_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get_opportunity(opp_id)
        return self._opportunities.get(opp_id)

    def _save_opp(self, opp_id: str, data: dict[str, Any]) -> None:
        if self._storage:
            self._storage.save_opportunity(opp_id, data)
        self._opportunities[opp_id] = data

    def _list_opps(self) -> list[dict[str, Any]]:
        if self._storage:
            return self._storage.list_opportunities()
        return list(self._opportunities.values())

    def _get_run(self, run_id: str) -> dict[str, Any] | None:
        if self._storage:
            return self._storage.get_run(run_id)
        return self._runs.get(run_id)

    def _save_run(self, run_id: str, data: dict[str, Any]) -> None:
        if self._storage:
            self._storage.save_run(run_id, data)
        self._runs[run_id] = data

    def _get_cache(self, key: str) -> str | None:
        if self._storage:
            return self._storage.get_cache(key)
        return self._cache_by_interest.get(key)

    def _set_cache(self, key: str, run_id: str) -> None:
        if self._storage:
            self._storage.set_cache(key, run_id)
        self._cache_by_interest[key] = run_id

    def _cache_key(
        self,
        user_id: str,
        interest_id: str | None,
        dismissed_pairs: set[tuple[str, str]],
    ) -> str:
        dismissed_fingerprint = hashlib.sha256(
            repr(sorted(dismissed_pairs)).encode("utf-8")
        ).hexdigest()[:10]
        return f"{user_id}:{interest_id or '__all__'}:{dismissed_fingerprint}"

    # ------------------------------------------------------------------
    # Dismissed pair tracking
    # ------------------------------------------------------------------

    def _get_dismissed_pairs(self, user_id: str) -> set[tuple[str, str]]:
        """Get (seedId, triggerCardId) pairs dismissed within 7 days."""
        if self._storage and hasattr(self._storage, "get_dismissed_pairs"):
            return self._storage.get_dismissed_pairs(user_id)
        # In-memory fallback: scan all opportunities
        all_opps = [
            opp for opp in self._list_opps()
            if not opp.get("userId") or opp.get("userId") == user_id
        ]
        return build_dismissed_pairs_from_opportunities(all_opps)

    def _record_dismissed(self, seed_id: str, trigger_card_ids: list[str]) -> None:
        """Record a dismissed seed+trigger pair."""
        self._dismissed_records.append({
            "seedId": seed_id,
            "triggerCardIds": trigger_card_ids,
            "dismissedAt": _now_iso(),
        })

    # ------------------------------------------------------------------
    # Data gathering
    # ------------------------------------------------------------------

    def _gather_input(
        self,
        payload: dict[str, Any],
        user_id: str,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Collect sprout input from payload and/or cross-service fetch."""
        result: dict[str, Any] = {
            "seeds": payload.get("seeds") or [],
            "hotCards": payload.get("hotCards") or [],
            "todayCards": payload.get("todayCards") or [],
            "userRecentActions": payload.get("userRecentActions") or [],
            "memory": payload.get("memory") or {},
        }

        if not self._data_fetcher:
            return result

        # Fetch missing data from services
        if not result["seeds"]:
            result["seeds"] = self._data_fetcher.fetch_seeds(user_id)
        if not result["hotCards"]:
            result["hotCards"] = self._data_fetcher.fetch_hot_cards()
        if not result["todayCards"]:
            result["todayCards"] = self._data_fetcher.fetch_today_cards(user_id)
        if not result["memory"] and session_id:
            result["memory"] = self._data_fetcher.fetch_memory(session_id)

        # Filter by interest if specified
        interest_id = payload.get("interestId")
        if interest_id and result["seeds"]:
            result["seeds"] = [
                s for s in result["seeds"] if s.get("interestId") == interest_id
            ]

        return result

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        top_candidates: list[tuple[dict, dict]],
        sprout_input: dict[str, Any],
        run_id: str,
        user_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Call LLM for top candidates and normalize output."""
        candidates_payload = []
        for seed, score_result in top_candidates:
            # Find the actual trigger card objects
            trigger_card_ids = score_result.get("bestTriggerCards", [])
            all_cards = (sprout_input.get("hotCards") or []) + (sprout_input.get("todayCards") or [])
            trigger_cards = [c for c in all_cards if c.get("id") in trigger_card_ids]
            candidates_payload.append({
                "seed": seed,
                "triggerCards": trigger_cards,
                "scoreSignals": {
                    **score_result.get("factors", {}),
                    "total": score_result.get("total", 0),
                    "penaltyReasons": score_result.get("penaltyReasons", []),
                },
            })

        try:
            raw_opps = self._llm_client.sprout_opportunities(
                candidates_payload,
                memory=sprout_input.get("memory"),
                limit=limit,
            )
        except Exception as e:
            logger.warning("llm_call_failed", extra={"error": str(e)})
            return self._build_fallback_opportunities(top_candidates, run_id, user_id, limit)

        if not raw_opps:
            return self._build_fallback_opportunities(top_candidates, run_id, user_id, limit)

        # Normalize LLM output
        opportunities = []
        for i, opp in enumerate(raw_opps[:limit]):
            # Match back to scored candidate for deterministic score
            matched_score = 70.0
            matched_seed_id = opp.get("seedId", "")
            for seed, score_result in top_candidates:
                if seed.get("id") == matched_seed_id:
                    matched_score = score_result.get("total", 70.0)
                    break

            opportunities.append({
                "id": _create_id("sprout"),
                "runId": run_id,
                "userId": user_id,
                "seedId": opp.get("seedId", ""),
                "interestId": opp.get("interestId", ""),
                "triggerType": opp.get("triggerType", "hot"),
                "triggerCardIds": opp.get("triggerCardIds", []),
                "triggerTopic": opp.get("triggerTopic", ""),
                "activatedSeed": opp.get("activatedSeed", opp.get("seedTitle", "")),
                "whyWorthWriting": opp.get("whyWorthWriting", ""),
                "suggestedTitle": opp.get("suggestedTitle", ""),
                "suggestedAngle": opp.get("suggestedAngle", ""),
                "suggestedMaterials": opp.get("suggestedMaterials", ""),
                "missingMaterials": opp.get("missingMaterials", []),
                "score": round(matched_score, 1),
                "tags": [
                    {"label": f"发芽指数 {round(matched_score)}", "tone": "blue"},
                ],
                "status": "active",
                "createdAt": _now_iso(),
            })
        return opportunities

    def _build_fallback_opportunities(
        self,
        top_candidates: list[tuple[dict, dict]],
        run_id: str,
        user_id: str,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """Build opportunities from scored candidates without LLM."""
        opportunities = []
        for seed, score_result in top_candidates[:limit]:
            title = seed.get("title", "")
            core_claim = seed.get("coreClaim", "")
            angles = seed.get("possibleAngles") or []
            opp = {
                "id": _create_id("sprout"),
                "runId": run_id,
                "userId": user_id,
                "seedId": seed.get("id", ""),
                "interestId": seed.get("interestId", ""),
                "triggerType": score_result.get("triggerType", "hot"),
                "triggerCardIds": score_result.get("bestTriggerCards", []),
                "triggerTopic": seed.get("sourceTitle", title),
                "activatedSeed": core_claim or title,
                "whyWorthWriting": f"种子《{title}》成熟度足够，可以开始写作。",
                "suggestedTitle": title,
                "suggestedAngle": angles[0] if angles else "",
                "suggestedMaterials": "",
                "missingMaterials": seed.get("requiredMaterials") or [],
                "score": round(score_result.get("total", 0), 1),
                "tags": [
                    {"label": f"发芽指数 {round(score_result.get('total', 0))}", "tone": "blue"},
                ],
                "status": "active",
                "createdAt": _now_iso(),
            }
            opportunities.append(opp)
        return opportunities

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_opportunities(self, interest_id: str | None = None) -> dict[str, Any]:
        items = self._list_opps()
        if interest_id:
            items = [item for item in items if item.get("interestId") == interest_id]
        items = sorted(items, key=lambda item: -float(item.get("score", 0)))
        return {"items": items}

    def start_run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        user_id = payload.get("userId", "demo-user")
        interest_id = payload.get("interestId")
        session_id = payload.get("sessionId")
        limit = int(payload.get("limit", 4))
        dismissed_pairs = self._get_dismissed_pairs(user_id)

        # Check cache
        cache_allowed = not payload.get("forceRefresh") and not any(
            payload.get(key)
            for key in ("seeds", "hotCards", "todayCards", "memory", "userRecentActions")
        )
        cache_key = self._cache_key(user_id, interest_id, dismissed_pairs)
        if cache_allowed:
            cached_run_id = self._get_cache(cache_key)
            cache_hit = bool(cached_run_id and self._get_run(cached_run_id))
            if cache_hit:
                run = self._get_run(cached_run_id)
                return {**run, "cacheHit": True}

        # Step 1: Gather input data
        sprout_input = self._gather_input(payload, user_id, session_id)
        seeds = sprout_input.get("seeds", [])

        # Step 2: Filter candidates
        candidates = filter_candidates(seeds, dismissed_pairs)

        # Step 3: Score candidates
        scored: list[tuple[dict, dict]] = []
        for seed in candidates:
            score_result = compute_activation_score(
                seed,
                sprout_input.get("hotCards", []),
                sprout_input.get("todayCards", []),
                sprout_input.get("memory", {}),
                dismissed_pairs,
            )
            scored.append((seed, score_result))

        # Step 4: Sort by score descending, take top N+2 (buffer for LLM)
        scored.sort(key=lambda x: x[1]["total"], reverse=True)
        top_candidates = scored[: min(limit + 2, len(scored))]

        # Step 5: Call LLM or build fallback
        run_id = _create_id("run")
        if top_candidates and self._llm_client:
            opportunities = self._call_llm(
                top_candidates, sprout_input, run_id, user_id, limit
            )
        elif top_candidates:
            opportunities = self._build_fallback_opportunities(
                top_candidates, run_id, user_id, limit
            )
        else:
            # No candidates pass filter — fall back to mock data only if no seeds were provided
            if not seeds:
                logger.info("no_seeds_fallback_to_mock")
                opportunities = [
                    {**opp, "runId": run_id, "userId": user_id, "status": "active", "createdAt": _now_iso()}
                    for opp in mock_data.initial_opportunities()
                ]
            else:
                opportunities = []

        # Step 6: Persist and return
        run = {
            "id": run_id,
            "userId": user_id,
            "interestId": interest_id,
            "status": "completed",
            "createdAt": _now_iso(),
            "completedAt": _now_iso(),
            "opportunities": opportunities,
            "candidateCount": len(candidates),
            "scoredCount": len(scored),
        }
        self._save_run(run_id, run)
        for opp in opportunities:
            self._save_opp(opp["id"], opp)
        if cache_allowed:
            self._set_cache(cache_key, run_id)

        logger.info(
            "sprout_run_completed",
            extra={
                "runId": run_id,
                "candidateCount": len(candidates),
                "opportunityCount": len(opportunities),
            },
        )
        return {**run, "cacheHit": False}

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        if not run:
            raise RunNotFound(run_id)
        return run

    def supplement(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        payload = payload or {}

        # Determine material type based on score
        score = float(opportunity.get("score", 70))
        material_type = payload.get("materialType") or ("evidence" if score >= 70 else "counterargument")

        # Call LLM Agent for real material
        llm_material: dict[str, Any] = {}
        if self._llm_client:
            seed_payload = {
                "seedId": opportunity.get("seedId", ""),
                "title": opportunity.get("activatedSeed", ""),
                "coreClaim": opportunity.get("activatedSeed", ""),
                "controversies": [opportunity.get("triggerTopic", "")],
            }
            llm_material = self._llm_client.supplement_material(
                seed_payload,
                material_type=material_type,
            )

        # Fall back to template if LLM returns nothing
        if not llm_material:
            claim = opportunity.get("activatedSeed", "")
            llm_material = {
                "type": material_type,
                "title": "Agent 补证据" if material_type == "evidence" else "Agent 找反方",
                "content": (
                    f'围绕"{claim}"，补一条事实证据：需要可追溯来源、时间和作者。'
                    if material_type == "evidence"
                    else f'围绕"{claim}"，反方可能认为当前论证忽略了样本偏差和适用边界。'
                ),
            }

        material_content = llm_material.get("content", "")
        material_title = llm_material.get("title", "今日发芽补充材料")

        # Append to existing materials instead of overwriting
        existing_materials = opportunity.get("suggestedMaterials", "")
        if existing_materials:
            combined_materials = f"{existing_materials}\n\n---\n\n**{material_title}**\n{material_content}"
        else:
            combined_materials = f"**{material_title}**\n{material_content}"

        next_opportunity = {
            **opportunity,
            "status": "supplemented",
            "suggestedMaterials": combined_materials,
        }
        self._save_opp(opportunity_id, next_opportunity)
        return {
            "opportunity": next_opportunity,
            "seedMaterial": {
                "type": llm_material.get("type", material_type),
                "title": material_title,
                "content": material_content,
                "sourceLabel": "今日发芽",
                "adopted": True,
            },
        }

    def switch_angle(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        payload = payload or {}

        new_title = payload.get("title", "")
        new_angle = payload.get("angle", "")

        # Call dedicated switch-sprout-angle LLM Agent
        if self._llm_client and not new_angle:
            llm_result = self._llm_client.switch_angle(opportunity)
            if llm_result:
                new_title = llm_result.get("suggestedTitle") or new_title
                new_angle = llm_result.get("suggestedAngle") or new_angle

        # Fall back to template if LLM returns nothing
        if not new_title:
            new_title = opportunity.get("suggestedTitle", "")
        if not new_angle:
            claim = opportunity.get("activatedSeed", "")
            new_angle = f'换角度：从反方视角重新审视「{claim}」。先列出反方最强的三个质疑，再逐个回应。'

        # Preserve previous angles in history
        previous_angles = list(opportunity.get("previousAngles", []))
        old_title = opportunity.get("suggestedTitle", "")
        old_angle = opportunity.get("suggestedAngle", "")
        if old_title or old_angle:
            previous_angles.append({"title": old_title, "angle": old_angle})

        next_opportunity = {
            **opportunity,
            "status": "angle_changed",
            "suggestedAngle": new_angle,
            "suggestedTitle": new_title,
            "previousAngles": previous_angles,
        }
        self._save_opp(opportunity_id, next_opportunity)
        return next_opportunity

    def dismiss(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {
            **opportunity,
            "status": "dismissed",
            "dismissedAt": _now_iso(),
        }
        self._save_opp(opportunity_id, next_opportunity)
        # Record dismissed pair for future filtering
        self._record_dismissed(
            opportunity.get("seedId", ""),
            opportunity.get("triggerCardIds", []),
        )
        return next_opportunity

    def start_writing(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {**opportunity, "status": "writing"}
        self._save_opp(opportunity_id, next_opportunity)
        return {
            "opportunity": next_opportunity,
            "writingHandoff": {
                "seedId": opportunity.get("seedId", ""),
                "interestId": opportunity.get("interestId", ""),
                "coreClaim": opportunity.get("activatedSeed", ""),
                "suggestedTitle": opportunity.get("suggestedTitle", ""),
                "suggestedAngle": opportunity.get("suggestedAngle", ""),
                "suggestedMaterials": opportunity.get("suggestedMaterials", ""),
            },
        }

    def _require(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self._get_opp(opportunity_id)
        if not opportunity:
            raise OpportunityNotFound(opportunity_id)
        return opportunity
