from __future__ import annotations

from typing import Any

from app.orchestrators.package_loader import LoadedOrchestratorPackage


class StageSchemaResolver:
    def resolve(self, loaded: LoadedOrchestratorPackage, *, stage: dict, fallback_schema: dict[str, Any] | None = None) -> dict[str, Any]:
        schema_id = str(stage.get("schema_id") or stage.get("prompt_id") or self._schema_id_from_stage(stage))
        schema = loaded.stage_schemas.get(schema_id)
        if isinstance(schema, dict):
            return dict(schema)
        return dict(fallback_schema or {})

    @staticmethod
    def _schema_id_from_stage(stage: dict) -> str:
        stage_kind = str(stage.get("stage_kind") or "")
        stage_id = str(stage.get("stage_id") or "")
        if stage_kind == "intent" or "intent" in stage_id:
            return "intent_understanding"
        if stage_kind == "decision_state_delta" or "decision_state_delta" in stage_id:
            return "decision_state_delta"
        if stage_kind == "next_interaction" or "next_interaction" in stage_id or "planning" in stage_id:
            return "next_interaction_planning"
        if stage_kind == "review" or "review" in stage_id:
            return "review_after_apply"
        return "write"
