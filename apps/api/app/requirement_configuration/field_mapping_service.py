from __future__ import annotations


class FieldMappingService:
    def validate(self, field_mappings: list[dict], *, field_keys: set[str], clause_ids: set[str]) -> list[dict]:
        errors: list[dict] = []
        for mapping in field_mappings:
            field_key = str(mapping.get("field_key") or "").strip()
            clause_id = str(mapping.get("clause_id") or "").strip()
            if field_key and field_key not in field_keys:
                errors.append({"field": "field_mappings.field_key", "message": f"unknown field_key: {field_key}"})
            if clause_id and clause_id not in clause_ids:
                errors.append({"field": "field_mappings.clause_id", "message": f"unknown clause_id: {clause_id}"})
        return errors

