from __future__ import annotations

from typing import Any

from . import mock_data


class RunNotFound(Exception):
    pass


class OpportunityNotFound(Exception):
    pass


class SproutService:
    def __init__(self, storage: Any = None, llm_client: Any = None) -> None:
        self._storage = storage  # If None, use in-memory dict
        self._llm_client = llm_client
        if self._storage:
            self._storage.load_initial_opportunities(mock_data.initial_opportunities())
        self._opportunities: dict[str, dict[str, Any]] = {
            item["id"]: item for item in mock_data.initial_opportunities()
        }
        self._runs: dict[str, dict[str, Any]] = {}
        self._cache_by_interest: dict[str, str] = {}

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

    def list_opportunities(self, interest_id: str | None = None) -> dict[str, Any]:
        items = self._list_opps()
        if interest_id:
            items = [item for item in items if item["interestId"] == interest_id]
        items = sorted(items, key=lambda item: -item["score"])
        return {"items": items}

    def start_run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        interest_id = payload.get("interestId")
        cached_run_id = self._get_cache(interest_id or "__all__")
        cache_hit = bool(cached_run_id and self._get_run(cached_run_id))
        if cache_hit:
            run = self._get_run(cached_run_id)
            return {**run, "cacheHit": True}
        run_id = mock_data.create_id("run")
        opportunities: list[dict[str, Any]] = []
        seeds = payload.get("seeds", [])
        if seeds and self._llm_client:
            try:
                memory = payload.get("memory", {})
                opportunities = self._llm_client.sprout_opportunities(seeds, memory=memory)
                for opp in opportunities:
                    self._save_opp(opp["id"], opp)
            except Exception as e:
                import logging
                logging.getLogger("kanshan.sprout").warning("sprout_llm_failed", extra={"error": str(e)})
        if not opportunities:
            opportunities = self._list_opps()
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
        self._save_run(run_id, run)
        self._set_cache(interest_id or "__all__", run_id)
        return {**run, "cacheHit": False}

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        if not run:
            raise RunNotFound(run_id)
        return run

    def supplement(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        payload = payload or {}
        material = (
            payload.get("material")
            or f'Agent 补充材料：围绕"{opportunity["activatedSeed"]}"，建议补充一次真实项目复盘。'
        )
        next_opportunity = {
            **opportunity,
            "status": "supplemented",
            "suggestedMaterials": material,
        }
        self._save_opp(opportunity_id, next_opportunity)
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
        new_angle = payload.get("angle") or f'换角度：从反方视角重新讲"{opportunity["activatedSeed"]}"。'
        next_opportunity = {
            **opportunity,
            "status": "angle_changed",
            "suggestedAngle": new_angle,
            "suggestedTitle": payload.get("title", opportunity["suggestedTitle"]),
        }
        self._save_opp(opportunity_id, next_opportunity)
        return next_opportunity

    def dismiss(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {**opportunity, "status": "dismissed"}
        self._save_opp(opportunity_id, next_opportunity)
        return next_opportunity

    def start_writing(self, opportunity_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        opportunity = self._require(opportunity_id)
        next_opportunity = {**opportunity, "status": "writing"}
        self._save_opp(opportunity_id, next_opportunity)
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
        opportunity = self._get_opp(opportunity_id)
        if not opportunity:
            raise OpportunityNotFound(opportunity_id)
        return opportunity
