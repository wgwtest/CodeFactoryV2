from __future__ import annotations

from typing import Any

from app.orchestrators.package_loader import LoadedOrchestratorPackage


class StageSchemaResolver:
    def resolve(self, loaded: LoadedOrchestratorPackage, *, stage: dict, fallback_schema: dict[str, Any] | None = None) -> dict[str, Any]:
        schema_id = str(stage.get("schema_id") or stage.get("prompt_id") or stage.get("stage_id") or "write")
        schema = loaded.stage_schemas.get(schema_id)
        if isinstance(schema, dict):
            return dict(schema)
        return dict(fallback_schema or {})
