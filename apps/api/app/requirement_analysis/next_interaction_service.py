from __future__ import annotations

from app.db.models.requirements import RequirementAnalysisSession
from app.orchestrators.plugin_registry import get_orchestrator_plugin_registry
from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.process_artifact_service import ProcessArtifactService


class NextInteractionService:
    def __init__(
        self,
        *,
        input_normalizer: InputNormalizer,
        process_artifact_service: ProcessArtifactService,
    ) -> None:
        self.input_normalizer = input_normalizer
        self.process_artifact_service = process_artifact_service

    def align_model_output_to_next_node(
        self,
        *,
        model_output: dict,
        next_spec_node: dict,
        current_spec_node: dict,
        session: RequirementAnalysisSession,
        continue_same_topic: bool = False,
        target_review: dict | None = None,
        global_review: dict | None = None,
    ) -> dict:
        review = target_review or {}
        global_state = global_review or {}
        focus_node = current_spec_node if continue_same_topic else next_spec_node

        if not focus_node.get("node_id"):
            next_question = "当前完成度树已无待确认节点。需要整体复核哪些章节仍显薄弱？"
            quick_options: list[dict] = []
        else:
            next_question = str(focus_node.get("question") or focus_node.get("title"))
            if model_output.get("raw_model_response", {}).get("mock") or not model_output.get("quick_options"):
                quick_options = self.process_artifact_service.quick_options_for_node(
                    get_orchestrator_plugin_registry().local_package_id_for_plugin(session.orchestrator_id),
                    focus_node,
                )
            else:
                quick_options = model_output["quick_options"]
        updated_sections = current_spec_node.get("target_section") or "需求规格说明"
        if continue_same_topic:
            next_content = f"当前章节仍需补齐：{next_question}"
        elif focus_node.get("node_id"):
            next_content = f"建议下一步确认：{next_question}"
        else:
            next_content = "当前完成度树暂无待确认节点，可以进入整体复核。"
        if continue_same_topic:
            assistant_message = f"基于你的输入，本轮先写入了：{updated_sections}。当前章节仍需继续补齐。"
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
                or review.get("reason")
                or f"{updated_sections} 已有可写入材料，完成度树建议继续补齐 {focus_node.get('target_section')}。"
                if focus_node.get("node_id")
                else "需求规格完成度树暂无 open 叶子节点。"
            ),
            "related_spec_node_ids": existing_related or ([focus_node["node_id"]] if focus_node.get("node_id") else []),
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
            "open_questions_delta": [next_question] if focus_node.get("node_id") else [],
            "document_patch": [
                {
                    **patch,
                    "write_policy": patch.get("write_policy") or session.write_policy,
                }
                for patch in model_output["document_patch"]
            ],
        }

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

    def build(self, *, next_spec_node: dict, model_output: dict, turn_index: int) -> dict:
        if not next_spec_node.get("node_id"):
            return {
                "interaction_id": f"interaction-{turn_index:04d}",
                "type": "free_continue",
                "prompt": "当前完成度树暂无待确认节点，可以进入整体复核。",
                "options": [],
                "target_spec_node_ids": [],
                "reason": "需求规格完成度树暂无 open 叶子节点。",
            }
        options = self.input_normalizer.normalize_quick_options(model_output.get("quick_options"))
        interaction_type = "choice_question" if options else "open_question"
        next_suggestion = model_output.get("next_suggestion")
        suggestion_prompt = (
            str(next_suggestion.get("content") or "").strip() if isinstance(next_suggestion, dict) else ""
        )
        return {
            "interaction_id": f"interaction-{turn_index:04d}",
            "type": interaction_type,
            "prompt": suggestion_prompt
            or str(model_output.get("next_question") or next_spec_node.get("question") or next_spec_node.get("title")),
            "options": options,
            "target_spec_node_ids": [str(next_spec_node["node_id"])],
            "reason": str(
                next_suggestion.get("reason")
                if isinstance(next_suggestion, dict)
                else ""
            )
            or f"补充后回看发现 {next_spec_node.get('target_section')} 仍缺少可写入材料。",
        }
