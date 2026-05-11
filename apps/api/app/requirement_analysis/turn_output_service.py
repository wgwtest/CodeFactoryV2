from __future__ import annotations

from app.db.models.requirements import RequirementAnalysisSession
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService


class RequirementAnalysisTurnOutputService:
    def __init__(self, spec_tree_service: RequirementSpecTreeService | None = None) -> None:
        self.spec_tree_service = spec_tree_service

    def validate_anchor_plan_refs(
        self,
        *,
        model_output: dict,
        chapter_configuration_context: dict | None = None,
    ) -> dict:
        plans = list(model_output.get("target_anchor_plan") or [])
        plan_ids: set[str] = set()
        canonical_clause_map = dict((chapter_configuration_context or {}).get("canonical_clause_map") or {})
        for plan in plans:
            plan_id = str(plan.get("plan_id") or "").strip()
            if not plan_id or plan_id in plan_ids:
                raise ValueError(f"invalid target_anchor_plan.plan_id: {plan_id}")
            plan_ids.add(plan_id)
            template_clause_id = str(plan.get("template_clause_id") or "").strip()
            if canonical_clause_map and template_clause_id not in canonical_clause_map:
                raise ValueError(f"target_anchor_plan.template_clause_id is not in chapter configuration: {template_clause_id}")
        for patch in list(model_output.get("document_patch") or []):
            plan_ref = str(patch.get("plan_ref") or "").strip()
            if not plan_ref or plan_ref not in plan_ids:
                materialized_plan = RequirementAnalysisTurnOutputService.materialize_anchor_plan_for_patch(
                    patch=patch,
                    canonical_clause_map=canonical_clause_map,
                )
                if not plan_ref or materialized_plan is None:
                    raise ValueError(f"document_patch.plan_ref is not in target_anchor_plan: {plan_ref}")
                materialized_plan["plan_id"] = plan_ref
                plans.append(materialized_plan)
                plan_ids.add(plan_ref)
        return {**model_output, "target_anchor_plan": plans}

    @staticmethod
    def materialize_anchor_plan_for_patch(*, patch: dict, canonical_clause_map: dict) -> dict | None:
        template_clause_id = RequirementAnalysisTurnOutputService.resolve_template_clause_id_from_patch(
            patch=patch,
            canonical_clause_map=canonical_clause_map,
        )
        if not template_clause_id:
            return None
        clause = dict(canonical_clause_map.get(template_clause_id) or {})
        display_heading = str(
            patch.get("target_section")
            or patch.get("display_heading")
            or clause.get("display_heading")
            or clause.get("heading")
            or template_clause_id
        )
        return {
            "plan_id": "",
            "decision_type": "append_existing_clause",
            "template_clause_id": template_clause_id,
            "canonical_clause_heading": str(clause.get("display_heading") or clause.get("heading") or display_heading),
            "subtopic_action": "none",
            "subtopic_key": "",
            "subtopic_title": "",
            "display_heading": display_heading,
            "template_shape_ref": "",
            "reason": "由 document_patch 自带结构化锚点补齐 target_anchor_plan，未做业务语义匹配。",
            "confidence": "medium",
            "anchor_path": template_clause_id,
        }

    @staticmethod
    def resolve_template_clause_id_from_patch(*, patch: dict, canonical_clause_map: dict) -> str:
        candidates = [
            patch.get("template_clause_id"),
            patch.get("anchor_path"),
            patch.get("plan_ref"),
        ]
        normalized_candidates: list[str] = []
        for candidate in candidates:
            value = str(candidate or "").strip()
            if not value:
                continue
            normalized_candidates.append(value)
            if value.startswith("SPEC-"):
                normalized_candidates.append(value.removeprefix("SPEC-"))
            if value.startswith("plan-"):
                plan_value = value.removeprefix("plan-")
                normalized_candidates.append(plan_value)
                first_token = plan_value.split("-", 1)[0].strip()
                if first_token:
                    normalized_candidates.append(first_token)
                    normalized_candidates.append(f"REQ-{first_token}")
        for value in normalized_candidates:
            if not canonical_clause_map or value in canonical_clause_map:
                return value
        heading_clause_id = RequirementAnalysisTurnOutputService.resolve_template_clause_id_from_patch_heading(
            patch=patch,
            canonical_clause_map=canonical_clause_map,
        )
        if heading_clause_id:
            return heading_clause_id
        return ""

    @staticmethod
    def resolve_template_clause_id_from_patch_heading(*, patch: dict, canonical_clause_map: dict) -> str:
        if not canonical_clause_map:
            return ""
        patch_headings = RequirementAnalysisTurnOutputService.heading_match_candidates(
            patch.get("display_heading"),
            patch.get("target_section"),
        )
        patch_headings.discard("")
        if not patch_headings:
            return ""
        for clause_id, clause in canonical_clause_map.items():
            clause_data = dict(clause or {})
            clause_headings = RequirementAnalysisTurnOutputService.heading_match_candidates(
                clause_id,
                clause_data.get("display_heading"),
                clause_data.get("heading"),
            )
            if patch_headings & clause_headings:
                return str(clause_id)
        return ""

    @staticmethod
    def heading_match_candidates(*values: object) -> set[str]:
        candidates: set[str] = set()
        for value in values:
            normalized = RequirementAnalysisTurnOutputService.normalize_heading_for_exact_match(value)
            if not normalized:
                continue
            candidates.add(normalized)
            leaf = normalized.split("/")[-1].strip()
            if leaf:
                candidates.add(leaf)
                without_number = RequirementAnalysisTurnOutputService.strip_heading_number(leaf)
                if without_number:
                    candidates.add(without_number)
        return candidates

    @staticmethod
    def normalize_heading_for_exact_match(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def strip_heading_number(value: object) -> str:
        text = RequirementAnalysisTurnOutputService.normalize_heading_for_exact_match(value)
        parts = text.split(" ", 1)
        if len(parts) == 2 and parts[0].replace(".", "").isdigit():
            return parts[1].strip()
        return text

    @staticmethod
    def normalize_turn_model_output(model_output: dict, *, session: RequirementAnalysisSession) -> dict:
        next_suggestion = model_output.get("next_suggestion")
        if not isinstance(next_suggestion, dict):
            next_question = str(model_output.get("next_question") or "")
            next_suggestion = {
                "kind": "topic",
                "content": next_question or "下一轮可以继续补齐需求规格说明。",
                "reason": "Provider 未返回 next_suggestion，服务端按当前 Turn 协议生成下一轮引导。",
                "related_spec_node_ids": [],
            }
        return {
            **model_output,
            "organizer_interpretation": RequirementAnalysisTurnOutputService.normalize_organizer_interpretation(
                model_output.get("organizer_interpretation")
            ),
            "next_suggestion": {
                "suggestion_id": str(next_suggestion.get("suggestion_id") or ""),
                "kind": str(next_suggestion.get("kind") or "topic"),
                "content": str(next_suggestion.get("content") or ""),
                "reason": str(next_suggestion.get("reason") or ""),
                "related_spec_node_ids": [
                    str(item) for item in next_suggestion.get("related_spec_node_ids", []) if str(item).strip()
                ]
                if isinstance(next_suggestion.get("related_spec_node_ids"), list)
                else [],
            },
            "quick_options": list(model_output.get("quick_options", [])),
            "template_shape_assessment": RequirementAnalysisTurnOutputService.normalize_template_shape_assessment(
                model_output.get("template_shape_assessment")
            ),
            "target_anchor_plan": RequirementAnalysisTurnOutputService.normalize_target_anchor_plan(
                model_output.get("target_anchor_plan")
            ),
            "confirmed_facts_delta": list(model_output.get("confirmed_facts_delta", [])),
            "open_questions_delta": list(model_output.get("open_questions_delta", [])),
            "document_patch": RequirementAnalysisTurnOutputService.normalize_document_patch(
                model_output.get("document_patch"),
                write_policy=session.write_policy,
            ),
            "annotations": list(model_output.get("annotations", [])),
            "risks": list(model_output.get("risks", [])),
            "confidence": str(model_output.get("confidence") or "medium"),
            "raw_model_response": dict(model_output.get("raw_model_response") or {"provider_id": session.provider_id, "mock": True}),
        }

    @staticmethod
    def normalize_template_shape_assessment(value: object) -> dict:
        if isinstance(value, dict):
            return {
                "shape_type": str(value.get("shape_type") or "coarse_grained_extensible"),
                "reason": str(value.get("reason") or ""),
                "allowed_write_modes": list(value.get("allowed_write_modes", []))
                if isinstance(value.get("allowed_write_modes"), list)
                else [],
                "forbidden_write_modes": list(value.get("forbidden_write_modes", []))
                if isinstance(value.get("forbidden_write_modes"), list)
                else [],
                "template_revision_recommendations": list(value.get("template_revision_recommendations", []))
                if isinstance(value.get("template_revision_recommendations"), list)
                else [],
            }
        return {
            "shape_type": "coarse_grained_extensible",
            "reason": "",
            "allowed_write_modes": [],
            "forbidden_write_modes": [],
            "template_revision_recommendations": [],
        }

    @staticmethod
    def normalize_target_anchor_plan(value: object) -> list[dict]:
        if not isinstance(value, list):
            return []
        plans = []
        for item in value:
            if not isinstance(item, dict):
                continue
            plans.append(
                {
                    "plan_id": str(item.get("plan_id") or ""),
                    "decision_type": str(item.get("decision_type") or "append_existing_clause"),
                    "template_clause_id": str(item.get("template_clause_id") or ""),
                    "canonical_clause_heading": str(item.get("canonical_clause_heading") or ""),
                    "subtopic_action": str(item.get("subtopic_action") or "none"),
                    "subtopic_key": str(item.get("subtopic_key") or ""),
                    "subtopic_title": str(item.get("subtopic_title") or ""),
                    "display_heading": str(item.get("display_heading") or item.get("canonical_clause_heading") or ""),
                    "template_shape_ref": str(item.get("template_shape_ref") or ""),
                    "reason": str(item.get("reason") or ""),
                    "confidence": str(item.get("confidence") or "medium"),
                    "anchor_path": str(item.get("anchor_path") or ""),
                }
            )
        return plans

    @staticmethod
    def normalize_organizer_interpretation(value: object) -> dict:
        if isinstance(value, dict):
            return {
                "summary": str(value.get("summary") or "系统已理解本轮用户输入。"),
                "intent": str(value.get("intent") or "supplement_requirement"),
                "confidence": str(value.get("confidence") or "medium"),
            }
        return {
            "summary": "系统已理解本轮用户输入。",
            "intent": "supplement_requirement",
            "confidence": "medium",
        }

    @staticmethod
    def normalize_document_patch(value: object, *, write_policy: str) -> list[dict]:
        if not isinstance(value, list):
            return []
        patches = []
        for item in value:
            if not isinstance(item, dict):
                continue
            patches.append(
                {
                    **item,
                    "write_policy": str(item.get("write_policy") or write_policy),
                }
            )
        return patches
