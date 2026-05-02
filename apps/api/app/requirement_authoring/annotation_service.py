from __future__ import annotations


class RequirementAnnotationService:
    def build_annotations(
        self,
        template_payload: dict,
        fields: dict[str, str],
        blocking_items: list[dict] | None = None,
    ) -> list[dict]:
        blocking_by_clause = {item["clause_id"]: item for item in blocking_items or []}
        field_mappings = template_payload.get("field_mappings", [])
        annotations = []
        for section in template_payload.get("sections", []):
            for clause in section.get("clauses", []):
                clause_id = clause["clause_id"]
                mappings = [item for item in field_mappings if item.get("clause_id") == clause_id]
                annotations.append(
                    {
                        "clause_id": clause_id,
                        "title": clause["title"],
                        "interpretation": f"{clause['title']}用于约束标准规格正文与后台语义字段的一致性。",
                        "source_refs": [
                            binding["label"]
                            for binding in template_payload.get("knowledge_bindings", [])
                            if binding.get("enabled", True)
                        ],
                        "semantic_mapping": mappings,
                        "p3_mapping": [item.get("structured_path") for item in mappings],
                        "gaps": [blocking_by_clause[clause_id]["message"]] if clause_id in blocking_by_clause else [],
                        "pending_confirmations": []
                        if any(fields.get(field_key) for field_key in clause.get("field_keys", []))
                        else ["该条款仍需专家确认。"],
                    }
                )
        return annotations

    def mark_clause_pending_mapping(self, annotations: list[dict], clause_id: str) -> list[dict]:
        return [
            {
                **annotation,
                "pending_confirmations": ["正文已轻量编辑，结构化映射待确认。"],
            }
            if annotation["clause_id"] == clause_id
            else annotation
            for annotation in annotations
        ]
