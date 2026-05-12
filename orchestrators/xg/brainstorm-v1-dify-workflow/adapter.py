from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

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
        self._require_remote_configuration()
        return self._run_remote_dify(request)

    def _run_remote_dify(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        context = self._workflow_context(request)
        remote_trace = self._call_remote_dify(request)
        normalized = self._normalize_remote_result(context=context, trace=remote_trace)
        provider_logs = [self._provider_log(request=request, trace=remote_trace, normalized=normalized)]
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
                "changed_sections": list(normalized["changed_sections"] or []),
                "completion_status": str(normalized["completion_status"] or "partial"),
                "confidence": str(normalized["confidence"] or "medium"),
            },
            interaction_output={
                "assistant_message": normalized["assistant_message"],
                "next_question": normalized["next_question"],
                "quick_options": normalized["quick_options"],
                "suggested_focus": {
                    "planning_strategy": "decision_state_loop",
                    "interaction_mode": normalized["interaction_mode"],
                    "should_ask_user": normalized["should_ask_user"],
                    "target_spec_node_ids": [context["active_spec_node_id"]] if context["active_spec_node_id"] else [],
                },
            },
            process_output={
                "stage_results": [],
                "stage_audits": [],
                "decision_trace": normalized["decision_trace"],
                "provider_logs": provider_logs,
                "review_after_apply_result": {},
                "annotations": normalized["annotations"],
                "risks": normalized["risks"],
            },
            state_output={
                "confirmed_facts_delta": list(normalized["confirmed_facts_delta"] or []),
                "open_questions_delta": list(normalized["open_questions_delta"] or []),
                "decision_state_delta": dict(normalized["decision_state_delta"] or {}),
                "decision_state_change_summary": dict(normalized["decision_state_change_summary"] or {}),
                "decision_state_document": dict(normalized["decision_state_document"] or {}),
                "spec_tree_update": {},
                "working_document_update": {},
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": {"remote_payload": dict(remote_trace["payload"] or {})},
                "raw_model_response": {},
                "raw_workflow_trace": dict(normalized["raw_workflow_trace"] or {}),
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

    @staticmethod
    def _require_remote_configuration() -> None:
        if not os.environ.get("DIFY_API_KEY", "").strip():
            raise ValueError("DIFY_API_KEY is not configured for brainstorm-v1-dify-workflow")

    def _call_remote_dify(self, request: OrchestratorRunRequest) -> dict:
        base_url = os.environ.get("DIFY_BASE_URL", "http://localhost").rstrip("/")
        api_key = os.environ.get("DIFY_API_KEY", "").strip()
        response_mode = os.environ.get("DIFY_RESPONSE_MODE", "blocking").strip() or "blocking"
        timeout_seconds = float(os.environ.get("DIFY_TIMEOUT_SECONDS", "120").strip() or "120")

        payload = {
            "inputs": self._remote_inputs(request),
            "response_mode": response_mode,
            "user": "codefactoryv2",
        }
        url = f"{base_url}/v1/workflows/run"
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
                trust_env=False,
            )
            response.raise_for_status()
            remote_payload = response.json()
        except httpx.HTTPError as exc:
            raise ValueError(f"remote dify workflow request failed: {exc}") from exc
        except ValueError as exc:
            raise ValueError("remote dify workflow returned non-JSON response") from exc
        outputs = dict(dict(remote_payload.get("data") or {}).get("outputs") or {})
        data = dict(remote_payload.get("data") or {})
        workflow_status = str(data.get("status") or "").strip()
        workflow_error = str(data.get("error") or "").strip()
        workflow_run_id = str(remote_payload.get("workflow_run_id") or data.get("id") or "").strip()
        if workflow_status == "failed" or workflow_error:
            detail = workflow_error or "workflow status failed"
            raise ValueError(f"remote dify workflow failed ({workflow_run_id}): {detail}")
        result_json = outputs.get("result_json")
        if not isinstance(result_json, str) or not result_json.strip():
            raise ValueError("remote dify workflow did not return data.outputs.result_json")
        return {
            "request": {
                "url": url,
                "response_mode": response_mode,
                "user": "codefactoryv2",
                "inputs": payload["inputs"],
            },
            "payload": remote_payload,
            "result_json": result_json,
            "workflow_trace": {
                "remote": True,
                "local": False,
                "workflow_id": str(
                    os.environ.get("DIFY_PUBLISHED_WORKFLOW_ID")
                    or os.environ.get("DIFY_WORKFLOW_ID")
                    or self.workflow.get("workflow_id")
                    or ""
                ),
                "workflow_run_id": str(
                    remote_payload.get("workflow_run_id")
                    or dict(remote_payload.get("data") or {}).get("id")
                    or ""
                ),
                "status": str(dict(remote_payload.get("data") or {}).get("status") or ""),
                "response_mode": response_mode,
            },
        }

    def _provider_log(self, *, request: OrchestratorRunRequest, trace: dict, normalized: dict) -> dict:
        turn = dict(request.turn or {})
        session = dict(request.session or {})
        workflow_trace = dict(normalized.get("raw_workflow_trace") or {})
        payload = dict(trace.get("payload") or {})
        data = dict(payload.get("data") or {})
        return {
            "call_id": f"{turn.get('turn_id') or 'turn-0001'}-dify-workflow",
            "turn_id": str(turn.get("turn_id") or ""),
            "stage_id": "dify_workflow",
            "stage_type": "external_workflow",
            "provider_id": "dify",
            "orchestrator_id": self.manifest.plugin_id,
            "orchestrator_mode": "dify_workflow",
            "model": str(session.get("model") or ""),
            "status": str(data.get("status") or workflow_trace.get("status") or "completed"),
            "created_at": "",
            "audit": {
                "user_input": str(turn.get("user_input") or ""),
                "normalized_input": dict(turn.get("normalized_input") or {}),
                "provider_request": dict(trace.get("request") or {}),
                "provider_response": {
                    "workflow_run_id": str(payload.get("workflow_run_id") or data.get("id") or ""),
                    "status": str(data.get("status") or ""),
                    "outputs": dict(data.get("outputs") or {}),
                    "raw_workflow_trace": workflow_trace,
                },
                "provider_normalized_output": {
                    "assistant_message": str(normalized.get("assistant_message") or ""),
                    "next_question": str(normalized.get("next_question") or ""),
                    "quick_options": list(normalized.get("quick_options") or []),
                    "interaction_mode": str(normalized.get("interaction_mode") or ""),
                    "should_ask_user": normalized.get("should_ask_user"),
                    "document_patch": list(normalized.get("document_patch") or []),
                    "decision_state_delta": dict(normalized.get("decision_state_delta") or {}),
                    "raw_workflow_trace": workflow_trace,
                },
                "service_output": {
                    "completion_status": str(normalized.get("completion_status") or ""),
                    "confidence": str(normalized.get("confidence") or ""),
                    "changed_sections": list(normalized.get("changed_sections") or []),
                    "annotations": list(normalized.get("annotations") or []),
                    "risks": list(normalized.get("risks") or []),
                },
            },
        }

    def _normalize_remote_result(self, *, context: dict, trace: dict) -> dict:
        try:
            parsed = json.loads(str(trace["result_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError("remote dify result_json is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("remote dify result_json is not a JSON object")

        decision_state_delta = self._normalize_delta_for_current_turn(
            dict(parsed.get("decision_state_delta") or {}),
            turn_id=str(context.get("turn_id") or "turn-0001"),
        )
        raw_workflow_trace = dict(parsed.get("raw_workflow_trace") or {})
        completion_status = str(parsed.get("completion_status") or "partial")
        is_draft_delivery = (
            raw_workflow_trace.get("branch_taken") == "draft_compose"
            or completion_status == "completed"
            or str(decision_state_delta.get("next_focus") or "").strip() == "等待用户审阅草案后主动提出修改意见。"
        )
        next_question = str(parsed.get("next_question") or "")
        if not next_question and not is_draft_delivery:
            next_question = context["active_question"]
        decision_state, change_summary = self._apply_decision_delta(
            current_state=context["decision_state"],
            delta=decision_state_delta,
            next_focus=str(decision_state_delta.get("next_focus") or next_question or ""),
            replace_open_questions=raw_workflow_trace.get("branch_taken") == "draft_compose",
        )
        document_patch = self._normalize_remote_document_patch(list(parsed.get("document_patch") or []))
        filled_document_text = self._clean_remote_text(str(parsed.get("filled_document_text") or ""))
        return {
            "assistant_message": str(parsed.get("assistant_message") or ""),
            "next_question": next_question,
            "quick_options": [] if is_draft_delivery else list(parsed.get("quick_options") or []),
            "interaction_mode": "draft_delivery" if is_draft_delivery else str(parsed.get("interaction_mode") or "ask_user"),
            "should_ask_user": False if is_draft_delivery else bool(parsed.get("should_ask_user", True)),
            "filled_document_text": filled_document_text,
            "document_patch": document_patch,
            "changed_sections": list(parsed.get("changed_sections") or ([context["active_section"]] if context["active_section"] else [])),
            "completion_status": completion_status,
            "confidence": str(parsed.get("confidence") or "medium"),
            "confirmed_facts_delta": list(parsed.get("confirmed_facts_delta") or []),
            "open_questions_delta": [] if is_draft_delivery else list(parsed.get("open_questions_delta") or []),
            "decision_state_delta": decision_state_delta,
            "decision_state": decision_state,
            "decision_state_change_summary": change_summary,
            "decision_state_document": dict(parsed.get("decision_state_document") or {}) or self._render_decision_state_document(decision_state),
            "decision_trace": list(parsed.get("decision_trace") or []),
            "annotations": list(parsed.get("annotations") or []),
            "risks": list(parsed.get("risks") or []),
            "raw_workflow_trace": {
                **raw_workflow_trace,
                **dict(trace.get("workflow_trace") or {}),
            },
        }

    @classmethod
    def _normalize_remote_document_patch(cls, patches: list[Any]) -> list[dict]:
        normalized: list[dict] = []
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            next_patch = dict(patch)
            next_patch["content"] = cls._clean_remote_text(str(next_patch.get("content") or ""))
            normalized.append(next_patch)
        return normalized

    @staticmethod
    def _clean_remote_text(text: str) -> str:
        value = str(text or "")
        replacements = [
            (r"这个我还没完全想清楚[，,但目前倾向于]*", ""),
            (r"我还没完全想清楚[，,但目前倾向于]*", ""),
            (r"但目前倾向于", ""),
            (r"目前倾向于", ""),
        ]
        for pattern, replacement in replacements:
            value = re.sub(pattern, replacement, value)
        return value.strip("，,、:： \n")

    def _remote_inputs(self, request: OrchestratorRunRequest) -> dict:
        session = dict(request.session or {})
        turn = dict(request.turn or {})
        template = dict(request.template or {})
        document_context = dict(request.document_context or {})
        state = dict(document_context.get("state") or {})
        return {
            "user_input": str(turn.get("user_input") or ""),
            "normalized_input_json": json.dumps(dict(turn.get("normalized_input") or {}), ensure_ascii=False),
            "topic": str(session.get("topic") or ""),
            "template_id": str(session.get("template_id") or template.get("template_id") or ""),
            "template_content": str(template.get("content") or ""),
            "template_structure_json": json.dumps(dict(template.get("parsed_structure") or {}), ensure_ascii=False),
            "active_spec_node_json": json.dumps(dict(document_context.get("active_spec_node") or {}), ensure_ascii=False),
            "spec_tree_json": json.dumps(list(document_context.get("spec_tree") or []), ensure_ascii=False),
            "working_document_json": json.dumps(dict(document_context.get("working_document") or {}), ensure_ascii=False),
            "decision_state_json": json.dumps(dict(state.get("decision_state") or {}), ensure_ascii=False),
            "previous_interaction_json": json.dumps(dict(turn.get("previous_interaction") or {}), ensure_ascii=False),
            "input_relation_json": json.dumps(dict(turn.get("input_relation") or {}), ensure_ascii=False),
            "confirmed_facts_json": json.dumps(list(document_context.get("confirmed_facts") or []), ensure_ascii=False),
            "open_questions_json": json.dumps(list(document_context.get("open_questions") or []), ensure_ascii=False),
            "history_summary": str(document_context.get("history_summary") or ""),
            "write_policy": str(session.get("write_policy") or "patch_suggestion_only"),
            "expected_output": str(dict(request.execution_options or {}).get("expected_output") or "both"),
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

    def _apply_decision_delta(
        self,
        *,
        current_state: dict,
        delta: dict,
        next_focus: str,
        replace_open_questions: bool = False,
    ) -> tuple[dict, dict]:
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
            if key == "open_questions" and replace_open_questions:
                state[key] = self._uniquify_item_ids(
                    list(delta.get(key, [])),
                    prefix=self._prefix_for_section(key),
                )
                continue
            state[key] = self._append_unique_items(
                list(state.get(key, [])),
                list(delta.get(key, [])),
                prefix=self._prefix_for_section(key),
            )
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
            "confirmed_facts": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("confirmed_facts") or []),
                prefix="DS-F",
            ),
            "confirmed_decisions": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("confirmed_decisions") or []),
                prefix="DS-D",
            ),
            "tentative_assumptions": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("tentative_assumptions") or []),
                prefix="DS-A",
            ),
            "open_questions": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("open_questions") or []),
                prefix="DS-Q",
            ),
            "rejected_directions": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("rejected_directions") or []),
                prefix="DS-R",
            ),
            "next_focus": str(state.get("next_focus") or ""),
            "chapter_projections": BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(
                list(state.get("chapter_projections") or []),
                prefix="DS-P",
            ),
        }

    @staticmethod
    def _append_unique_items(current: list[dict], additions: list[dict], *, prefix: str = "DS-I") -> list[dict]:
        result = list(current)
        seen = {str(item.get("content") or "") for item in result if isinstance(item, dict)}
        for item in additions:
            content = str(item.get("content") or "")
            if not content or content in seen:
                continue
            result.append(dict(item))
            seen.add(content)
        return BrainstormV1DifyWorkflowAdapter._uniquify_item_ids(result, prefix=prefix)

    @staticmethod
    def _uniquify_item_ids(items: list[dict], *, prefix: str) -> list[dict]:
        result: list[dict] = []
        used: set[str] = set()
        next_index = 1
        for item in items:
            normalized = dict(item) if isinstance(item, dict) else {}
            item_id = str(normalized.get("item_id") or "").strip()
            if not item_id or item_id in used:
                item_id = BrainstormV1DifyWorkflowAdapter._next_item_id(
                    prefix=prefix,
                    used=used,
                    start_index=next_index,
                )
            used.add(item_id)
            normalized["item_id"] = item_id
            result.append(normalized)
            next_index = BrainstormV1DifyWorkflowAdapter._next_index_from_id(item_id, default=next_index) + 1
        return result

    @staticmethod
    def _next_item_id(*, prefix: str, used: set[str], start_index: int = 1) -> str:
        index = max(1, start_index)
        while True:
            candidate = f"{prefix}-{index:03d}"
            if candidate not in used:
                return candidate
            index += 1

    @staticmethod
    def _next_index_from_id(item_id: str, *, default: int) -> int:
        try:
            return int(str(item_id).rsplit("-", 1)[-1])
        except ValueError:
            return default

    @staticmethod
    def _prefix_for_section(section_id: str) -> str:
        return {
            "confirmed_facts": "DS-F",
            "confirmed_decisions": "DS-D",
            "tentative_assumptions": "DS-A",
            "open_questions": "DS-Q",
            "rejected_directions": "DS-R",
            "chapter_projections": "DS-P",
        }.get(section_id, "DS-I")

    @classmethod
    def _normalize_delta_for_current_turn(cls, delta: dict, *, turn_id: str) -> dict:
        normalized = dict(delta)
        for key in [
            "confirmed_facts",
            "confirmed_decisions",
            "tentative_assumptions",
            "open_questions",
            "rejected_directions",
            "chapter_projections",
        ]:
            items = []
            for item in list(normalized.get(key) or []):
                if not isinstance(item, dict):
                    continue
                next_item = dict(item)
                if not str(next_item.get("source_turn_id") or "").strip() or str(next_item.get("source_turn_id")) == "turn-0001":
                    next_item["source_turn_id"] = turn_id
                items.append(next_item)
            normalized[key] = cls._uniquify_item_ids(items, prefix=cls._prefix_for_section(key))
        normalized["confirmed_decisions"] = cls._append_promoted_decisions(
            current=list(normalized.get("confirmed_decisions") or []),
            facts=list(normalized.get("confirmed_facts") or []),
            turn_id=turn_id,
        )
        return normalized

    @classmethod
    def _append_promoted_decisions(cls, *, current: list[dict], facts: list[dict], turn_id: str) -> list[dict]:
        result = [dict(item) for item in current if isinstance(item, dict)]
        seen = {str(item.get("content") or "") for item in result}
        for fact in facts:
            if not isinstance(fact, dict) or not cls._is_decision_like_item(fact):
                continue
            content = str(fact.get("content") or "").strip()
            if not content or content in seen:
                continue
            result.append(
                {
                    "content": content,
                    "source_turn_id": turn_id,
                    "target_section": str(fact.get("target_section") or ""),
                    "status": str(fact.get("status") or "active"),
                }
            )
            seen.add(content)
        return cls._uniquify_item_ids(result, prefix=cls._prefix_for_section("confirmed_decisions"))

    @staticmethod
    def _is_decision_like_item(item: dict) -> bool:
        section = str(item.get("target_section") or "")
        content = str(item.get("content") or "")
        if section in {
            "2 项目概述 / 软件定位",
            "2 项目概述 / 使用场景",
            "2 项目概述 / 范围边界",
            "3 工程需求 / 接口需求",
            "3 工程需求 / 功能需求",
            "3 工程需求 / 性能需求",
            "3 工程需求 / 安装和操作要求",
            "3 工程需求 / 业务规则与异常补偿",
            "4 运行环境要求 / 硬件需求",
            "4 运行环境要求 / 软件需求",
            "4 运行环境要求 / 网络与部署环境",
            "5 数据与信息要求 / 输入数据",
            "5 数据与信息要求 / 输出数据与成果",
            "5 数据与信息要求 / 数据质量与追溯",
            "6 质量、安全与约束要求 / 安全与权限",
            "6 质量、安全与约束要求 / 可靠性与可用性",
            "6 质量、安全与约束要求 / 精度与质量约束",
            "7 验收准则 / 验收场景",
            "7 验收准则 / 验收准则",
            "7 验收准则 / 待确认事项",
        }:
            return True
        return any(
            marker in content
            for marker in [
                "第一阶段",
                "主要用户",
                "核心流程",
                "不做",
                "不承诺",
                "辅助判断",
                "数据接入",
                "验收",
                "权限",
                "审计",
                "部署",
                "精度",
                "性能",
            ]
        )

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
