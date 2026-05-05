from __future__ import annotations


class RequirementFreezeService:
    def build_frozen_package(
        self,
        *,
        standard_document: dict,
        annotations: list[dict],
        fields: dict[str, str],
        archive_ids: list[str],
        frozen_at: str,
    ) -> dict:
        return {
            "p3_consumable": True,
            "frozen_at": frozen_at,
            "standard_document": standard_document,
            "annotations": annotations,
            "structured_spec": self.build_structured_spec(fields, archive_ids),
        }

    @staticmethod
    def build_structured_spec(fields: dict[str, str], archive_ids: list[str]) -> dict:
        return {
            "application": {
                "name": fields.get("application_name", ""),
                "domain": fields.get("domain_scope", ""),
                "summary": fields.get("normal_flow", ""),
                "target_users": [
                    item.strip()
                    for item in fields.get("target_users", "").replace("、", ",").split(",")
                    if item.strip()
                ],
            },
            "objects": [],
            "processes": [
                {
                    "id": "process-main",
                    "name": fields.get("main_process", ""),
                    "process_kind": "collaboration",
                    "source_kind": "temporary",
                    "description": fields.get("normal_flow", ""),
                    "participant_object_ids": [],
                    "source_archive_id": archive_ids[0] if archive_ids else None,
                    "source_item_type": None,
                    "source_item_id": None,
                }
            ],
            "rules": [{"id": "rule-exception-flow", "name": "异常流程", "description": fields.get("exception_flow", "")}],
            "metrics": [{"id": "metric-acceptance", "name": "验收准则", "description": fields.get("acceptance_criteria", "")}],
            "non_functional_constraints": [
                {
                    "id": "constraint-performance",
                    "name": "性能与可靠性",
                    "category": "quality",
                    "description": fields.get("non_functional", ""),
                }
            ],
        }
