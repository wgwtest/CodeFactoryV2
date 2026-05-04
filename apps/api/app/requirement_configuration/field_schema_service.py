from __future__ import annotations


class FieldSchemaService:
    def field_keys(self, form_groups: list[dict]) -> set[str]:
        return {
            str(field.get("field_key"))
            for group in form_groups
            for field in group.get("fields", [])
            if field.get("field_key")
        }

