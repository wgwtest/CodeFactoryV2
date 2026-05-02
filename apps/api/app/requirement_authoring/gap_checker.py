from __future__ import annotations


class RequirementGapChecker:
    def run(self, template_payload: dict, fields: dict[str, str]) -> dict:
        required_fields = template_payload.get("gap_rules", {}).get("required_fields", [])
        form_labels = self.form_labels(template_payload)
        blocking_items = [
            {
                "severity": "blocking",
                "field_key": field_key,
                "clause_id": self.field_clause_id(template_payload, field_key),
                "message": f"{form_labels.get(field_key, field_key)} 缺少确认内容。",
            }
            for field_key in required_fields
            if not fields.get(field_key)
        ]
        passed_count = max(len(required_fields) - len(blocking_items), 0)
        return {
            "blocking_count": len(blocking_items),
            "warning_count": 0,
            "passed_count": passed_count,
            "items": blocking_items,
        }

    @staticmethod
    def empty_check_result() -> dict:
        return {"blocking_count": 0, "warning_count": 0, "passed_count": 0, "items": []}

    @staticmethod
    def form_labels(template_payload: dict) -> dict[str, str]:
        labels = {}
        for group in template_payload.get("form_groups", []):
            for field in group.get("fields", []):
                labels[field["field_key"]] = field["label"]
        return labels

    @staticmethod
    def field_clause_id(template_payload: dict, field_key: str) -> str:
        for group in template_payload.get("form_groups", []):
            for field in group.get("fields", []):
                if field["field_key"] == field_key:
                    return field["clause_id"]
        return "REQ-1.1"
