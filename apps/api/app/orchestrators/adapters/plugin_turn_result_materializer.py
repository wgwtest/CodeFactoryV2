from __future__ import annotations

from datetime import UTC, datetime

from app.orchestrators.plugin_contracts import OrchestratorRunRequest, OrchestratorRunResult
from app.orchestrators.plugin_result_normalizer import OrchestratorPluginResultNormalizer
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.requirement_analysis.working_document_service import WorkingDocumentService


class PluginTurnResultMaterializer:
    def __init__(self, *, working_document_service: WorkingDocumentService | None = None) -> None:
        self.working_document_service = working_document_service or WorkingDocumentService()

    def materialize(
        self,
        *,
        request: OrchestratorRunRequest,
        result: OrchestratorRunResult,
    ) -> TurnExecutionResult:
        normalized_result = OrchestratorPluginResultNormalizer().normalize(result)
        plugin_model_output = normalized_result["model_output"]
        plugin_process_output = normalized_result["process_output"]
        plugin_state_output = normalized_result["state_output"]

        session = dict(request.session or {})
        request_turn = dict(request.turn or {})
        document_context = dict(request.document_context or {})
        state = dict(document_context.get("state") or {})
        turns = list(state.get("turns", []))
        turn_id = str(request_turn.get("turn_id") or f"turn-{len(turns) + 1:04d}")
        user_input = str(request_turn.get("user_input") or "")
        normalized_input = dict(request_turn.get("normalized_input") or {})
        active_spec_node = dict(document_context.get("active_spec_node") or {})
        active_spec_node_id = str(active_spec_node.get("node_id") or state.get("active_spec_node_id") or "")
        working_document = dict(
            document_context.get("working_document")
            or state.get("working_document")
            or self.working_document_service.initialize(
                topic=str(session.get("topic") or ""),
                template_id=str(session.get("template_id") or ""),
            )
        )

        anchor_path = str(active_spec_node.get("node_id") or "SPEC-REQ-1.1").removeprefix("SPEC-")
        display_heading = str(active_spec_node.get("target_section") or "需求规格说明")
        document_patch = [
            {
                "plan_ref": "AP-PLUGIN-001",
                "operation": "append_or_update",
                "content": str(plugin_model_output.get("filled_document_text") or ""),
                "write_policy": str(session.get("write_policy") or "patch_suggestion_only"),
            }
        ]
        target_anchor_plan = [
            {
                "plan_id": "AP-PLUGIN-001",
                "template_clause_id": anchor_path,
                "display_heading": display_heading,
                "canonical_clause_heading": display_heading,
                "anchor_path": anchor_path,
            }
        ]
        projection_spec_node = {
            **active_spec_node,
            "target_section": display_heading,
        }
        working_document_update_result = self.working_document_service.apply_patches(
            working_document=working_document,
            document_patch=document_patch,
            patch_proposals=[],
            projection_spec_node=projection_spec_node,
            turn_id=turn_id,
            user_input_summary=str(normalized_input.get("semantic") or user_input),
            target_anchor_plan=target_anchor_plan,
        )
        working_document_update = working_document_update_result.to_dict()
        next_question = str(plugin_model_output.get("next_question") or "请继续补充下一项需求规格信息。")
        assistant_message = str(plugin_model_output.get("assistant_message") or "组织器插件已返回需求规格正文草稿。")
        now = datetime.now(UTC).isoformat()
        turn_index = int(request_turn.get("turn_index") or len(turns) + 1)
        next_options = list(plugin_model_output.get("quick_options") or [])
        turn = {
            "turn_id": turn_id,
            "session_id": str(session.get("session_id") or ""),
            "user_input": user_input,
            "orchestrator_plugin": dict(result.plugin or {}),
            "previous_interaction": dict(request_turn.get("previous_interaction") or {}),
            "normalized_input": normalized_input,
            "input_relation": dict(request_turn.get("input_relation") or {}),
            "intent_understanding_result": {},
            "target_document_structure": {},
            "stage_task_definition": {},
            "stage_quality_constraints": {},
            "spec_execution": {
                "assistant_message": assistant_message,
                "affected_spec_nodes": [projection_spec_node],
                "confirmed_facts": list(plugin_state_output.get("confirmed_facts_delta") or []),
                "document_patch": document_patch,
                "target_anchor_plan": target_anchor_plan,
                "working_document_update": working_document_update,
                "interpretation": {"intent": "supplement_requirement"},
            },
            "post_update_review": {
                "target_review": {"status": "acceptable"},
                "global_review": {"status": "continue"},
            },
            "review_after_apply_result": {},
            "next_interaction_plan": {},
            "closure_decision": {"status": "open"},
            "next_interaction": {
                "interaction_id": f"interaction-{turn_index:04d}",
                "type": "open_question",
                "prompt": next_question,
                "options": next_options,
                "target_spec_node_ids": [active_spec_node_id] if active_spec_node_id else [],
                "reason": "",
            },
            "stage_audits": list(plugin_process_output.get("stage_audits") or []),
            "decision_trace": list(plugin_process_output.get("decision_trace") or []),
            "confidence": str(plugin_model_output.get("confidence") or "medium"),
            "service_steps": self._service_steps(),
            "raw_model_response": {},
            "raw_plugin_response": normalized_result["raw_plugin_response"],
            "created_at": now,
        }
        updated_turns = [*turns, turn]
        messages = [
            *list(state.get("messages", [])),
            {"id": f"msg-{len(updated_turns) * 2:04d}", "role": "user", "content": user_input, "turn_id": turn_id, "created_at": now},
            {"id": f"msg-{len(updated_turns) * 2 + 1:04d}", "role": "assistant", "content": assistant_message, "turn_id": turn_id, "created_at": now},
        ]
        return TurnExecutionResult(
            turn=turn,
            state_patch={
                "turns": updated_turns,
                "messages": messages,
                "confirmed_facts": list(plugin_state_output.get("confirmed_facts_delta") or []),
                "open_questions": list(plugin_state_output.get("open_questions_delta") or []),
                "document_patch": document_patch,
                "working_document": working_document,
                "questions": list(state.get("questions", [])),
                "facts": list(state.get("facts", [])),
                "patches": list(state.get("patches", [])),
                "spec_tree": list(document_context.get("spec_tree") or state.get("spec_tree") or []),
                "active_spec_node_id": active_spec_node_id,
                "turn_path": list(state.get("turn_path", [])),
                "next_interaction": turn["next_interaction"],
                "last_quick_options": next_options,
                "annotations": list(plugin_process_output.get("annotations") or []),
                "risks": list(plugin_process_output.get("risks") or []),
            },
            provider_logs=list(plugin_process_output.get("provider_logs") or []),
        )

    @staticmethod
    def _service_steps() -> list[dict]:
        return [
            {"step": 1, "title": "接收用户输入", "status": "completed"},
            {"step": 2, "title": "读取会话状态", "status": "completed"},
            {"step": 3, "title": "读取模板与知识包", "status": "completed"},
            {"step": 4, "title": "组装组织器上下文", "status": "completed"},
            {"step": 5, "title": "调用组织器插件", "status": "completed"},
            {"step": 6, "title": "解析结构化输出", "status": "completed"},
            {"step": 7, "title": "校验并落状态", "status": "completed"},
        ]
