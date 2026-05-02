from __future__ import annotations

from typing import Any

from app.db.models.requirements import RequirementAnalysisSession


class RequirementAnalysisTurnOutputService:
    def __init__(self, owner: Any) -> None:
        self.owner = owner

    def align_model_output_to_next_node(
        self,
        *,
        model_output: dict,
        next_spec_node: dict,
        current_spec_node: dict,
        session: RequirementAnalysisSession,
    ) -> dict:
        if not next_spec_node.get("node_id"):
            next_question = "当前完成度树已无待确认节点。需要整体复核哪些章节仍显薄弱？"
            quick_options: list[dict] = []
        else:
            next_question = str(next_spec_node.get("question") or next_spec_node.get("title"))
            if model_output.get("raw_model_response", {}).get("mock") or not model_output.get("quick_options"):
                quick_options = self.owner._quick_options_for_node(next_spec_node)
            else:
                quick_options = model_output["quick_options"]
        updated_sections = current_spec_node.get("target_section") or "需求规格说明"
        next_content = (
            f"建议下一步确认：{next_question}"
            if next_spec_node.get("node_id")
            else "当前完成度树暂无待确认节点，可以进入整体复核。"
        )
        orchestrator_id = str(model_output.get("raw_model_response", {}).get("orchestrator_id") or "")
        if orchestrator_id == "xg-strong-rule-orchestrator":
            assistant_message = f"强规则组织器已按固定闭环更新：{updated_sections}。{next_content}"
        else:
            assistant_message = f"基于你的输入，本轮更新了：{updated_sections}。{next_content}"
        existing_suggestion = model_output.get("next_suggestion")
        existing_suggestion_id = (
            existing_suggestion.get("suggestion_id") if isinstance(existing_suggestion, dict) else ""
        )
        existing_content = (
            str(existing_suggestion.get("content") or "").strip() if isinstance(existing_suggestion, dict) else ""
        )
        existing_reason = (
            str(existing_suggestion.get("reason") or "").strip() if isinstance(existing_suggestion, dict) else ""
        )
        existing_related = (
            list(existing_suggestion.get("related_spec_node_ids") or [])
            if isinstance(existing_suggestion, dict) and isinstance(existing_suggestion.get("related_spec_node_ids"), list)
            else []
        )
        next_suggestion = {
            "suggestion_id": "",
            "kind": "topic",
            "content": existing_content or next_content,
            "reason": (
                existing_reason
                or f"{updated_sections} 已有可写入材料，完成度树建议继续补齐 {next_spec_node.get('target_section')}。"
                if next_spec_node.get("node_id")
                else "需求规格完成度树暂无 open 叶子节点。"
            ),
            "related_spec_node_ids": existing_related or ([next_spec_node["node_id"]] if next_spec_node.get("node_id") else []),
        }
        return {
            **model_output,
            "assistant_message": assistant_message,
            "next_suggestion": {
                **next_suggestion,
                "suggestion_id": str(existing_suggestion_id or ""),
            },
            "next_question": next_question,
            "quick_options": quick_options,
            "open_questions_delta": [next_question] if next_spec_node.get("node_id") else [],
            "document_patch": [
                {
                    **patch,
                    "write_policy": patch.get("write_policy") or session.write_policy,
                }
                for patch in model_output["document_patch"]
            ],
        }

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

    def select_projection_spec_node_id(self, spec_tree: list[dict], model_output: dict, fallback_node_id: str) -> str:
        patch_sections = [
            str(patch.get("section") or "").strip()
            for patch in model_output.get("document_patch", [])
            if isinstance(patch, dict)
        ]
        for section in patch_sections:
            matched = self.owner._find_spec_node_by_target_section(spec_tree, section)
            if matched and matched.get("node_id"):
                return str(matched["node_id"])
        return fallback_node_id

    def ensure_next_open_question(
        self,
        *,
        questions: list[dict],
        next_question: str,
        next_spec_node: dict,
        turn_id: str,
    ) -> list[dict]:
        if not next_question or not next_spec_node.get("node_id"):
            return questions
        for question in questions:
            if question.get("status") == "open" and question.get("target_section") == next_spec_node.get("target_section"):
                return questions
        for question in questions:
            if question.get("content") == next_question and question.get("status") == "open":
                question["target_section"] = next_spec_node.get("target_section")
                return questions
        questions.append(
            {
                "question_id": f"Q-{len(questions) + 1:03d}",
                "content": next_question,
                "status": "open",
                "target_section": next_spec_node.get("target_section"),
                "source_turn_id": turn_id,
                "resolution_fact_ids": [],
            }
        )
        return questions

    def affected_spec_nodes(self, *, spec_tree: list[dict], node_ids: list[str]) -> list[dict]:
        affected: list[dict] = []
        for node_id in node_ids:
            node = self.owner._find_spec_node(spec_tree, node_id)
            affected.append(
                {
                    "node_id": node_id or None,
                    "title": node.get("title") if node else node_id,
                    "target_section": node.get("target_section") if node else "未绑定模板章节",
                    "effect": "update",
                    "reason": "用户本轮输入形成了该章节的可写入材料。",
                }
            )
        return affected
