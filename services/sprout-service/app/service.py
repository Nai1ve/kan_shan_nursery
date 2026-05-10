from __future__ import annotations

from typing import Any

from . import mock_data


class RunNotFound(Exception):
    pass


class OpportunityNotFound(Exception):
    pass


class SproutService:
    def __init__(self) -> None:
        self._opportunities: dict[str, dict[str, Any]] = {
            item["id"]: item for item in mock_data.initial_opportunities()
        }
        self._runs: dict[str, dict[str, Any]] = {}
        self._cache_by_interest: dict[str, str] = {}

    def list_opportunities(self, interest_id: str | None = None) -> dict[str, Any]:
        items = list(self._opportunities.values())
        if interest_id:
            items = [item for item in items if item["interestId"] == interest_id]
        items = sorted(items, key=lambda item: -item["score"])
        return {"items": items}

    def start_run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        interest_id = payload.get("interestId")
        cached_run_id = self._cache_by_interest.get(interest_id or "__all__")
        cache_hit = bool(cached_run_id and cached_run_id in self._runs)
        if cache_hit:
            run = self._runs[cached_run_id]
            return {**run, "cacheHit": True}
        run_id = mock_data.create_id("run")
        opportunities = list(self._opportunities.values())
        if interest_id:
            opportunities = [item for item in opportunities if item["interestId"] == interest_id]
        run = {
            "id": run_id,
            "userId": payload.get("userId", "demo-user"),
            "interestId": interest_id,
            "status": "completed",
            "createdAt": mock_data.now_iso(),
            "completedAt": mock_data.now_iso(),
            "opportunities": opportunities,
        }
        self._runs[run_id] = run
        self._cache_by_interest[interest_id or "__all__"] = run_id
        return {**run, "cacheHit": False}

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise RunNotFound(run_id)
        return run

    def supplement(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        payload = payload or {}
        material = (
            payload.get("material")
            or f"Agent 补充材料：围绕“{opportunity['activatedSeed']}”，建议补充一次真实项目复盘。"
        )
        next_opportunity = {
            **opportunity,
            "status": "supplemented",
            "suggestedMaterials": material,
        }
        self._opportunities[opportunity_id] = next_opportunity
        return {
            "opportunity": next_opportunity,
            "seedMaterial": {
                "type": "evidence",
                "title": "今日发芽补充材料",
                "content": material,
                "sourceLabel": "今日发芽",
                "adopted": True,
            },
        }

    def switch_angle(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        payload = payload or {}
        new_angle = payload.get("angle") or f"换角度：从反方视角重新讲“{opportunity['activatedSeed']}”。"
        next_opportunity = {
            **opportunity,
            "status": "angle_changed",
            "suggestedAngle": new_angle,
            "suggestedTitle": payload.get("title", opportunity["suggestedTitle"]),
        }
        self._opportunities[opportunity_id] = next_opportunity
        return next_opportunity

    def dismiss(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {**opportunity, "status": "dismissed"}
        self._opportunities[opportunity_id] = next_opportunity
        return next_opportunity

    def start_writing(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {**opportunity, "status": "writing"}
        self._opportunities[opportunity_id] = next_opportunity
        return {
            "opportunity": next_opportunity,
            "writingHandoff": {
                "seedId": opportunity["seedId"],
                "interestId": opportunity["interestId"],
                "coreClaim": opportunity["activatedSeed"],
                "suggestedTitle": opportunity["suggestedTitle"],
                "suggestedAngle": opportunity["suggestedAngle"],
                "suggestedMaterials": opportunity["suggestedMaterials"],
            },
        }

    def _require(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self._opportunities.get(opportunity_id)
        if not opportunity:
            raise OpportunityNotFound(opportunity_id)
        return opportunity
