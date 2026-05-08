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
                "scope": fields.get("application_scope", ""),
                "goals": fields.get("business_goals", ""),
                "expected_value": fields.get("expected_value", ""),
                "main_scenarios": fields.get("main_scenarios", ""),
                "usage_modes": fields.get("usage_modes", ""),
                "scope_in": fields.get("in_scope", ""),
                "scope_out": fields.get("out_of_scope", ""),
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
            "capabilities": {
                "situational_display": fields.get("situational_display", ""),
                "gis_analysis_tools": fields.get("gis_analysis_tools", ""),
                "deployment_analysis": fields.get("deployment_analysis", ""),
                "result_outputs": fields.get("result_outputs", ""),
                "collaboration_mode": fields.get("collaboration_mode", ""),
            },
            "data": {
                "input_sources": fields.get("input_data_sources", ""),
                "input_mode": fields.get("input_data_mode", ""),
                "output_products": fields.get("output_data_products", ""),
            },
            "interfaces": {"external": fields.get("external_interfaces", "")},
            "security": {
                "requirements": fields.get("security_requirements", ""),
                "permission_model": fields.get("permission_model", ""),
            },
            "deployment": {"environment": fields.get("deployment_environment", "")},
            "quality": {
                "accuracy": fields.get("accuracy_constraints", ""),
                "constraints": fields.get("quality_constraints", ""),
            },
            "acceptance": {
                "scenarios": fields.get("acceptance_scenarios", ""),
                "criteria": fields.get("acceptance_criteria", ""),
                "open_items": fields.get("open_decision_items", ""),
            },
            "rules": [
                {
                    "id": "rule-exception-flow",
                    "name": "异常流程",
                    "description": fields.get("exception_flow", ""),
                },
                {
                    "id": "rule-fallback",
                    "name": "补偿策略",
                    "description": fields.get("fallback_rules", ""),
                },
            ],
            "metrics": [{"id": "metric-acceptance", "name": "验收准则", "description": fields.get("acceptance_criteria", "")}],
            "non_functional_constraints": [
                {
                    "id": "constraint-performance",
                    "name": "性能与可靠性",
                    "category": "quality",
                    "description": fields.get("performance_requirements", "") or fields.get("non_functional", ""),
                },
                {
                    "id": "constraint-reliability",
                    "name": "可靠性",
                    "category": "quality",
                    "description": fields.get("reliability_requirements", ""),
                }
            ],
        }
