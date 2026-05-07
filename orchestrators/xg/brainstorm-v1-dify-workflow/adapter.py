from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.orchestrators.adapters.plugin_turn_result_materializer import PluginTurnResultMaterializer
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest, OrchestratorRunResult
from app.requirement_analysis.turn_execution_result import TurnExecutionResult


DECISION_STATE_SECTIONS = (
    ("confirmed_facts", "一、已确认事实"),
    ("confirmed_decisions", "二、已确认决策"),
    ("tentative_assumptions", "三、暂定假设"),
    ("open_questions", "四、未闭合问题"),
    ("rejected_directions", "五、被否定方向"),
    ("next_focus", "六、下一步交互焦点"),
    ("chapter_projections", "七、章节投影"),
)


class BrainstormV1DifyWorkflowAdapter:
    def __init__(self, *, manifest: OrchestratorPluginManifest, package: Any | None = None) -> None:
        self.manifest = manifest
        self.materializer = PluginTurnResultMaterializer()
        self.workflow = self._load_workflow()

    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        context = self._workflow_context(request)
        node_outputs: dict[str, dict] = {}
        trace_nodes: list[dict] = []
        for node in list(self.workflow.get("nodes") or []):
            node_id = str(node.get("node_id") or "")
            output = self._run_node(node_id=node_id, context=context, node_outputs=node_outputs)
            node_outputs[node_id] = output
            trace_nodes.append(
                {
                    "node_id": node_id,
                    "type": str(node.get("type") or ""),
                    "status": "completed",
                    "summary": str(output.get("summary") or node.get("description") or ""),
                }
            )

        normalized = node_outputs["normalize_output"]
        result = OrchestratorRunResult(
            contract_version=request.contract_version,
            plugin={
                "plugin_id": self.manifest.plugin_id,
                "plugin_type": self.manifest.plugin_type,
                "observability_level": self.manifest.observability_level,
            },
            final_output={
                "filled_document_text": normalized["filled_document_text"],
                "document_patch": normalized["document_patch"],
                "changed_sections": [context["active_section"]] if context["active_section"] else [],
                "completion_status": "partial",
                "confidence": "medium",
            },
            interaction_output={
                "assistant_message": normalized["assistant_message"],
                "next_question": normalized["next_question"],
                "quick_options": normalized["quick_options"],
                "suggested_focus": {
                    "planning_strategy": "decision_state_loop",
                    "target_spec_node_ids": [context["active_spec_node_id"]] if context["active_spec_node_id"] else [],
                },
            },
            process_output={
                "stage_results": [],
                "stage_audits": [],
                "decision_trace": normalized["decision_trace"],
                "provider_logs": [],
                "review_after_apply_result": {},
                "annotations": normalized["annotations"],
                "risks": normalized["risks"],
            },
            state_output={
                "confirmed_facts_delta": [item["content"] for item in normalized["decision_state_delta"]["confirmed_facts"]],
                "open_questions_delta": [item["content"] for item in normalized["decision_state_delta"]["open_questions"]],
                "decision_state_delta": normalized["decision_state_delta"],
                "decision_state_change_summary": normalized["decision_state_change_summary"],
                "decision_state_document": normalized["decision_state_document"],
                "spec_tree_update": {},
                "working_document_update": {},
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": {"workflow_outputs": node_outputs},
                "raw_model_response": {},
                "raw_workflow_trace": {
                    "fake": False,
                    "local": True,
                    "workflow_id": str(self.workflow.get("workflow_id") or "brainstorm-v1-dify-shaped-workflow"),
                    "run_id": f"local-{context['turn_id']}",
                    "nodes": trace_nodes,
                },
            },
        )
        materialized_turn = self._materialized_turn(request=request, result=result, normalized=normalized)
        return result.model_copy(
            update={
                "raw_output": {
                    **dict(result.raw_output or {}),
                    "turn_execution_result": materialized_turn,
                }
            }
        )

    def _run_node(self, *, node_id: str, context: dict, node_outputs: dict[str, dict]) -> dict:
        if node_id == "normalize_input":
            return {
                "summary": "已规范化用户输入和活动章节。",
                "semantic": context["semantic"],
                "active_section": context["active_section"],
            }
        if node_id == "intent_understanding":
            return self._intent_understanding(context)
        if node_id == "decision_state_delta":
            return self._decision_state_delta(context)
        if node_id == "document_projection":
            return self._document_projection(context, node_outputs["decision_state_delta"])
        if node_id == "next_interaction_planning":
            return self._next_interaction_planning(context, node_outputs["decision_state_delta"])
        if node_id == "normalize_output":
            return self._normalize_output(context=context, node_outputs=node_outputs)
        raise ValueError(f"unsupported workflow node: {node_id}")

    def _intent_understanding(self, context: dict) -> dict:
        semantic = context["semantic"]
        active_section = context["active_section"]
        return {
            "summary": f"识别到本轮输入可沉淀为“{active_section}”的需求规格信息。",
            "intent_understanding_result": {
                "user_goal_summary": semantic,
                "input_type": "first_round_product_concept" if context["turn_index"] == 1 else "free_supplement",
                "relation_to_previous_interaction": str(context["input_relation"].get("relation") or "none"),
                "document_strategy": "decision_state_then_section_projection",
                "target_section_candidates": [active_section],
                "ambiguities": [],
            },
            "stage_task_definition": {
                "task_summary": f"围绕“{active_section}”维护决策状态并形成章节投影。",
                "target_sections": [active_section],
                "must_output": ["decision_state_delta", "document_patch", "next_interaction_plan"],
            },
        }

    def _decision_state_delta(self, context: dict) -> dict:
        semantic = context["semantic"]
        active_section = context["active_section"]
        question = context["active_question"]
        delta = {
            "confirmed_facts": [
                self._state_item(
                    item_id="DS-F-001",
                    content=semantic,
                    source_turn_id=context["turn_id"],
                    target_section=active_section,
                )
            ]
            if semantic
            else [],
            "confirmed_decisions": [
                self._state_item(
                    item_id="DS-D-001",
                    content=f"本轮优先围绕“{active_section}”补齐需求规格信息。",
                    source_turn_id=context["turn_id"],
                    target_section=active_section,
                )
            ],
            "tentative_assumptions": [],
            "open_questions": [
                self._state_item(
                    item_id="DS-Q-001",
                    content=question,
                    source_turn_id=context["turn_id"],
                    target_section=active_section,
                    status="open",
                )
            ],
            "rejected_directions": [],
            "chapter_projections": [
                self._state_item(
                    item_id="DS-P-001",
                    content=active_section,
                    source_turn_id=context["turn_id"],
                    target_section=active_section,
                    status="projected",
                )
            ],
            "next_focus": question,
        }
        return {
            "summary": "已生成 Brainstorm v1 决策状态增量。",
            "decision_state_delta": delta,
        }

    def _document_projection(self, context: dict, decision_output: dict) -> dict:
        semantic = context["semantic"]
        active_section = context["active_section"]
        anchor_path = context["anchor_path"]
        content = (
            f"围绕“{active_section}”，本轮已确认：{semantic}"
            if semantic
            else f"围绕“{active_section}”，本轮已建立需求分析决策状态。"
        )
        document_patch = [
            {
                "plan_ref": "BRAINSTORM-DIFY-AP-001",
                "operation": "append_or_update",
                "content": content,
                "write_policy": context["write_policy"],
            }
        ]
        target_anchor_plan = [
            {
                "plan_id": "BRAINSTORM-DIFY-AP-001",
                "decision_type": "append_existing_clause",
                "template_clause_id": anchor_path,
                "canonical_clause_heading": active_section,
                "display_heading": active_section,
                "anchor_path": anchor_path,
                "reason": "Dify-shaped workflow 使用 Brainstorm 决策状态章节投影作为正文锚点。",
                "confidence": "medium",
            }
        ]
        return {
            "summary": "已把决策状态投影为章节正文补丁。",
            "document_patch": document_patch,
            "target_anchor_plan": target_anchor_plan,
            "filled_document_text": content,
            "decision_state_delta": dict(decision_output["decision_state_delta"]),
        }

    def _next_interaction_planning(self, context: dict, decision_output: dict) -> dict:
        question = str(dict(decision_output["decision_state_delta"]).get("next_focus") or context["active_question"])
        return {
            "summary": "已基于决策状态规划下一轮问题。",
            "next_interaction_plan": {
                "planning_strategy": "decision_state_loop",
                "user_message": f"本轮已沉淀为决策状态并投影到临时正文。建议下一步确认：{question}",
                "next_question": question,
                "quick_options": [],
                "plan_reason": "继续沿 Brainstorm v1 的决策状态闭环补齐需求规格说明。",
                "target_spec_nodes": [context["active_spec_node_id"]] if context["active_spec_node_id"] else [],
            },
            "planning_trace": ["Dify-shaped workflow 读取决策状态增量和当前活动章节生成下一轮问题。"],
        }

    def _normalize_output(self, *, context: dict, node_outputs: dict[str, dict]) -> dict:
        decision_delta = dict(node_outputs["decision_state_delta"]["decision_state_delta"])
        projection = dict(node_outputs["document_projection"])
        planning = dict(node_outputs["next_interaction_planning"]["next_interaction_plan"])
        decision_state, summary = self._apply_decision_delta(
            current_state=context["decision_state"],
            delta=decision_delta,
            next_focus=str(decision_delta.get("next_focus") or planning.get("next_question") or ""),
        )
        decision_state_document = self._render_decision_state_document(decision_state)
        return {
            "summary": "已归一化为组织器插件输出合同。",
            "assistant_message": f"我已把本轮讨论沉淀为结构化决策状态，并投影到：{context['active_section']}。",
            "next_question": str(planning.get("next_question") or context["active_question"]),
            "quick_options": list(planning.get("quick_options") or []),
            "filled_document_text": str(projection.get("filled_document_text") or ""),
            "document_patch": list(projection.get("document_patch") or []),
            "target_anchor_plan": list(projection.get("target_anchor_plan") or []),
            "decision_state_delta": decision_delta,
            "decision_state": decision_state,
            "decision_state_change_summary": summary,
            "decision_state_document": decision_state_document,
            "decision_trace": [
                {"step": "intent_understanding", "decision": node_outputs["intent_understanding"]["summary"]},
                {"step": "decision_state_delta", "decision": "将用户输入沉淀为 confirmed_facts 与 chapter_projections。"},
                {"step": "document_projection", "decision": "使用章节投影生成 document_patch。"},
                {"step": "next_interaction_planning", "decision": str(planning.get("plan_reason") or "")},
            ],
            "annotations": ["该插件为本地 Dify-shaped workflow，不要求安装 Dify；可在后续替换为真实 Dify Workflow API。"],
            "risks": [],
        }

    def _materialized_turn(
        self,
        *,
        request: OrchestratorRunRequest,
        result: OrchestratorRunResult,
        normalized: dict,
    ) -> TurnExecutionResult:
        materialized = self.materializer.materialize(request=request, result=result)
        turn = {
            **dict(materialized.turn),
            "decision_state_delta": normalized["decision_state_delta"],
            "decision_state_change_summary": normalized["decision_state_change_summary"],
            "decision_state_document": normalized["decision_state_document"],
        }
        state_patch = {
            **dict(materialized.state_patch),
            "decision_state": normalized["decision_state"],
            "decision_state_document": normalized["decision_state_document"],
        }
        return TurnExecutionResult(
            turn=turn,
            state_patch=state_patch,
            provider_logs=list(materialized.provider_logs),
        )

    def _workflow_context(self, request: OrchestratorRunRequest) -> dict:
        session = dict(request.session or {})
        turn = dict(request.turn or {})
        document_context = dict(request.document_context or {})
        state = dict(document_context.get("state") or {})
        normalized_input = dict(turn.get("normalized_input") or {})
        semantic = str(normalized_input.get("semantic") or turn.get("user_input") or "").strip()
        active_spec_node = dict(document_context.get("active_spec_node") or {})
        active_spec_node_id = str(active_spec_node.get("node_id") or state.get("active_spec_node_id") or "")
        active_section = str(active_spec_node.get("target_section") or "需求规格说明")
        return {
            "session": session,
            "turn_id": str(turn.get("turn_id") or "turn-0001"),
            "turn_index": int(turn.get("turn_index") or 1),
            "semantic": semantic,
            "input_relation": dict(turn.get("input_relation") or {}),
            "write_policy": str(session.get("write_policy") or "patch_suggestion_only"),
            "decision_state": self._normalize_decision_state(state.get("decision_state")),
            "active_spec_node": active_spec_node,
            "active_spec_node_id": active_spec_node_id,
            "active_section": active_section,
            "active_question": str(active_spec_node.get("question") or "请继续补充需求规格说明。"),
            "anchor_path": active_spec_node_id.removeprefix("SPEC-") or "REQ-1.1",
        }

    @staticmethod
    def _state_item(
        *,
        item_id: str,
        content: str,
        source_turn_id: str,
        target_section: str,
        status: str = "active",
    ) -> dict:
        return {
            "item_id": item_id,
            "content": content,
            "source_turn_id": source_turn_id,
            "target_section": target_section,
            "status": status,
        }

    def _apply_decision_delta(self, *, current_state: dict, delta: dict, next_focus: str) -> tuple[dict, dict]:
        state = self._normalize_decision_state(current_state)
        before_counts = self._counts(state)
        for key in [
            "confirmed_facts",
            "confirmed_decisions",
            "tentative_assumptions",
            "open_questions",
            "rejected_directions",
            "chapter_projections",
        ]:
            state[key] = self._append_unique_items(list(state.get(key, [])), list(delta.get(key, [])))
        state["next_focus"] = next_focus
        after_counts = self._counts(state)
        return state, {
            "turn_id": str(delta.get("turn_id") or ""),
            "added_counts": {
                key: max(0, after_counts.get(key, 0) - before_counts.get(key, 0))
                for key in after_counts
            },
            "next_focus": next_focus,
        }

    @staticmethod
    def _normalize_decision_state(value: object) -> dict:
        state = dict(value) if isinstance(value, dict) else {}
        return {
            "topic": str(state.get("topic") or ""),
            "confirmed_facts": list(state.get("confirmed_facts") or []),
            "confirmed_decisions": list(state.get("confirmed_decisions") or []),
            "tentative_assumptions": list(state.get("tentative_assumptions") or []),
            "open_questions": list(state.get("open_questions") or []),
            "rejected_directions": list(state.get("rejected_directions") or []),
            "next_focus": str(state.get("next_focus") or ""),
            "chapter_projections": list(state.get("chapter_projections") or []),
        }

    @staticmethod
    def _append_unique_items(current: list[dict], additions: list[dict]) -> list[dict]:
        result = list(current)
        seen = {str(item.get("content") or "") for item in result if isinstance(item, dict)}
        for item in additions:
            content = str(item.get("content") or "")
            if not content or content in seen:
                continue
            result.append(item)
            seen.add(content)
        return result

    @staticmethod
    def _counts(state: dict) -> dict[str, int]:
        return {
            key: len(list(state.get(key, [])))
            for key in [
                "confirmed_facts",
                "confirmed_decisions",
                "tentative_assumptions",
                "open_questions",
                "rejected_directions",
                "chapter_projections",
            ]
        }

    @staticmethod
    def _render_decision_state_document(decision_state: dict) -> dict:
        sections: list[dict] = []
        for section_id, heading in DECISION_STATE_SECTIONS:
            if section_id == "next_focus":
                focus = str(decision_state.get("next_focus") or "").strip()
                items = [
                    {
                        "item_id": "DS-FOCUS",
                        "content": focus,
                        "source_turn_id": None,
                        "target_section": "",
                        "status": "active",
                    }
                ] if focus else []
            else:
                items = list(decision_state.get(section_id, []))
            sections.append({"section_id": section_id, "heading": heading, "items": items})
        return {
            "document_id": "decision-state-document",
            "title": "需求分析结构化状态",
            "phase": "waiting_user",
            "sections": sections,
        }

    @staticmethod
    def _load_workflow() -> dict:
        return json.loads((Path(__file__).with_name("workflow.json")).read_text(encoding="utf-8"))
