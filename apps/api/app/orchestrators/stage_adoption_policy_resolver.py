from __future__ import annotations

from typing import Any

from app.orchestrators.package_loader import LoadedOrchestratorPackage


class StageAdoptionPolicyResolver:
    def resolve(self, loaded: LoadedOrchestratorPackage, *, stage: dict) -> dict[str, Any]:
        policy_id = str(stage.get("adoption_id") or stage.get("prompt_id") or self._policy_id_from_stage(stage))
        policy = loaded.stage_adoption_policies.get(policy_id)
        if isinstance(policy, dict):
            return dict(policy)
        return {
            "adopt_fields": list(stage.get("adopt_fields") or []),
            "ignore_fields": [],
            "failure_policy": str(stage.get("failure_policy") or "block_turn"),
        }

    @staticmethod
    def _policy_id_from_stage(stage: dict) -> str:
        stage_kind = str(stage.get("stage_kind") or "")
        stage_id = str(stage.get("stage_id") or "")
        if stage_kind == "intent" or "intent" in stage_id:
            return "intent_understanding"
        if stage_kind == "next_interaction" or "next_interaction" in stage_id or "planning" in stage_id:
            return "next_interaction_planning"
        if stage_kind == "review" or "review" in stage_id:
            return "review_after_apply"
        return "write"
