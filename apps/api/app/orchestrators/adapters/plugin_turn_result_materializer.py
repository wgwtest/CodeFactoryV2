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

        fallback_anchor_path = str(active_spec_node.get("node_id") or "SPEC-REQ-1.1").removeprefix("SPEC-")
        fallback_display_heading = str(active_spec_node.get("target_section") or "需求规格说明")
        document_patch, target_anchor_plan = self._materialize_document_patch(
            plugin_model_output=plugin_model_output,
            session=session,
            fallback_anchor_path=fallback_anchor_path,
            fallback_display_heading=fallback_display_heading,
        )
        projection_spec_node = {
            **active_spec_node,
            "target_section": fallback_display_heading,
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
        assistant_message = str(plugin_model_output.get("assistant_message") or "组织器插件已返回需求规格正文草稿。")
        now = datetime.now(UTC).isoformat()
        turn_index = int(request_turn.get("turn_index") or len(turns) + 1)
        next_suggestion = dict(plugin_model_output.get("next_suggestion") or {})
        should_ask_user = self._bool_value(plugin_model_output.get("should_ask_user"), default=True)
        if plugin_model_output.get("should_ask_user") is None and "should_ask_user" in next_suggestion:
            should_ask_user = self._bool_value(next_suggestion.get("should_ask_user"), default=True)
        interaction_mode = str(plugin_model_output.get("interaction_mode") or next_suggestion.get("interaction_mode") or "").strip()
        next_question = str(plugin_model_output.get("next_question") or "")
        if should_ask_user and not next_question:
            next_question = "请继续补充下一项需求规格信息。"
        next_options = [] if not should_ask_user else list(plugin_model_output.get("quick_options") or [])
        next_interaction_type = interaction_mode if not should_ask_user and interaction_mode else "open_question"
        next_interaction_prompt = next_question if should_ask_user else assistant_message
        next_interaction_target_ids = [active_spec_node_id] if should_ask_user and active_spec_node_id else []
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
                "type": next_interaction_type,
                "prompt": next_interaction_prompt,
                "options": next_options,
                "target_spec_node_ids": next_interaction_target_ids,
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
    def _materialize_document_patch(
        *,
        plugin_model_output: dict,
        session: dict,
        fallback_anchor_path: str,
        fallback_display_heading: str,
    ) -> tuple[list[dict], list[dict]]:
        write_policy = str(session.get("write_policy") or "patch_suggestion_only")
        document_patch: list[dict] = []
        target_anchor_plan: list[dict] = []
        seen_plan_ids: set[str] = set()

        for item in list(plugin_model_output.get("document_patch") or []):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            plan_ref = str(item.get("plan_ref") or "").strip()
            if not plan_ref or plan_ref in seen_plan_ids:
                plan_ref = PluginTurnResultMaterializer._next_plan_ref(seen_plan_ids)
            seen_plan_ids.add(plan_ref)
            anchor_path = str(item.get("anchor_path") or item.get("target_section") or fallback_anchor_path).strip()
            display_heading = str(
                item.get("target_section")
                or item.get("display_heading")
                or item.get("canonical_clause_heading")
                or fallback_display_heading
                or anchor_path
            ).strip()
            template_clause_id = str(item.get("template_clause_id") or anchor_path or fallback_anchor_path).strip()
            normalized_patch = {
                **item,
                "plan_ref": plan_ref,
                "operation": str(item.get("operation") or "append_or_update"),
                "content": content,
                "write_policy": str(item.get("write_policy") or write_policy),
                "anchor_path": anchor_path,
            }
            if display_heading:
                normalized_patch["target_section"] = display_heading
            document_patch.append(normalized_patch)
            target_anchor_plan.append(
                {
                    "plan_id": plan_ref,
                    "decision_type": str(item.get("decision_type") or "append_existing_clause"),
                    "template_clause_id": template_clause_id,
                    "display_heading": display_heading or anchor_path,
                    "canonical_clause_heading": str(item.get("canonical_clause_heading") or display_heading or anchor_path),
                    "anchor_path": anchor_path,
                    "reason": str(item.get("reason") or "由组织器插件 document_patch 自动物化。"),
                    "confidence": str(item.get("confidence") or plugin_model_output.get("confidence") or "medium"),
                }
            )

        if document_patch:
            return document_patch, target_anchor_plan

        content = str(plugin_model_output.get("filled_document_text") or "").strip()
        if not content:
            return [], []
        return [
            {
                "plan_ref": "AP-PLUGIN-001",
                "operation": "append_or_update",
                "content": content,
                "write_policy": write_policy,
            }
        ], [
            {
                "plan_id": "AP-PLUGIN-001",
                "template_clause_id": fallback_anchor_path,
                "display_heading": fallback_display_heading,
                "canonical_clause_heading": fallback_display_heading,
                "anchor_path": fallback_anchor_path,
            }
        ]

    @staticmethod
    def _next_plan_ref(seen_plan_ids: set[str]) -> str:
        index = len(seen_plan_ids) + 1
        while True:
            plan_ref = f"AP-PLUGIN-{index:03d}"
            if plan_ref not in seen_plan_ids:
                return plan_ref
            index += 1

    @staticmethod
    def _bool_value(value: object, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        if value is None:
            return default
        return bool(value)

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
