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
                raise ValueError(f"document_patch.plan_ref is not in target_anchor_plan: {plan_ref}")
        return model_output

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
