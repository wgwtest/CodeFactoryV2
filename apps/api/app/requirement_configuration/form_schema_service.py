from __future__ import annotations


class FormSchemaService:
    def validate(self, form_groups: list[dict]) -> list[dict]:
        errors: list[dict] = []
        seen_field_keys: set[str] = set()
        for group in form_groups:
            for field in group.get("fields", []):
                field_key = str(field.get("field_key") or "").strip()
                if not field_key:
                    errors.append({"field": "form_groups.fields.field_key", "message": "field_key is required"})
                elif field_key in seen_field_keys:
                    errors.append({"field": "form_groups.fields.field_key", "message": f"duplicate field_key: {field_key}"})
                seen_field_keys.add(field_key)
        return errors

