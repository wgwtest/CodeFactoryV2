from __future__ import annotations

from app.db.models.requirements import RequirementAnalysisSession
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService


class RequirementAnalysisTurnOutputService:
    def __init__(self, spec_tree_service: RequirementSpecTreeService | None = None) -> None:
        self.spec_tree_service = spec_tree_service

    @staticmethod
    def ensure_patch_target_section(*, model_output: dict, current_spec_node: dict, session: RequirementAnalysisSession) -> dict:
        current_section = str(current_spec_node.get("target_section") or "未绑定模板章节")
        patches = []
        for patch in model_output.get("document_patch", []):
            section = str(patch.get("section") or "").strip() or current_section
            patches.append(
                {
                    **patch,
                    "section": section,
                    "write_policy": patch.get("write_policy") or session.write_policy,
                }
            )
        if not patches and model_output.get("confirmed_facts_delta"):
            patches.append(
                {
                    "section": current_section,
                    "operation": "append_or_update",
                    "content": str(model_output["confirmed_facts_delta"][0]),
                    "write_policy": session.write_policy,
                }
            )
        return {**model_output, "document_patch": patches}

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
            "confirmed_facts_delta": list(model_output.get("confirmed_facts_delta", [])),
            "open_questions_delta": list(model_output.get("open_questions_delta", [])),
            "document_patch": list(model_output.get("document_patch", [])),
            "annotations": list(model_output.get("annotations", [])),
            "risks": list(model_output.get("risks", [])),
            "confidence": str(model_output.get("confidence") or "medium"),
            "raw_model_response": dict(model_output.get("raw_model_response") or {"provider_id": session.provider_id, "mock": True}),
        }

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
