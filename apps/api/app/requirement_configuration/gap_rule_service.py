from __future__ import annotations


class GapRuleService:
    def validate(self, gap_rules: dict | None, *, field_keys: set[str]) -> list[dict]:
        if gap_rules is None:
            return []
        errors: list[dict] = []
        for field_key in gap_rules.get("required_fields", []):
            if field_key not in field_keys:
                errors.append({"field": "gap_rules.required_fields", "message": f"unknown field_key: {field_key}"})
        return errors

    def summarize_for_authoring(self, template_payload: dict) -> dict:
        return dict(template_payload.get("gap_rules", {}))

