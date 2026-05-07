from __future__ import annotations

from typing import Any

from app.orchestrators.package_loader import LoadedOrchestratorPackage


class StageAdoptionPolicyResolver:
    def resolve(self, loaded: LoadedOrchestratorPackage, *, stage: dict) -> dict[str, Any]:
        policy_id = str(stage.get("adoption_id") or stage.get("prompt_id") or stage.get("stage_id") or "write")
        policy = loaded.stage_adoption_policies.get(policy_id)
        if isinstance(policy, dict):
            return dict(policy)
        return {
            "adopt_fields": list(stage.get("adopt_fields") or []),
            "ignore_fields": [],
            "failure_policy": str(stage.get("failure_policy") or "block_turn"),
        }
