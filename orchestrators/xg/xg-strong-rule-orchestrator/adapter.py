from __future__ import annotations

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest, OrchestratorRunResult
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.session_snapshot import SessionSnapshot


class LocalXGOrchestratorPluginAdapter:
    def __init__(self, *, manifest: OrchestratorPluginManifest, package=None, runtime_host=None) -> None:
        self.manifest = manifest
        self.runtime_host = runtime_host

    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        runtime = self._runtime()
        turn_result = runtime.run_turn(
            self._session_snapshot(request),
            RequirementAnalysisTurnCreate(user_input=str(request.turn.get("user_input") or "")),
        )
        return OrchestratorRunResult(
            contract_version=request.contract_version,
            plugin={
                "plugin_id": self.manifest.plugin_id,
                "plugin_type": self.manifest.plugin_type,
                "observability_level": self.manifest.observability_level,
            },
            final_output={
                "filled_document_text": "",
                "document_patch": list(turn_result.turn.get("spec_execution", {}).get("document_patch") or []),
                "changed_sections": [
                    str(node.get("target_section") or node.get("node_id") or "")
                    for node in list(turn_result.turn.get("spec_execution", {}).get("affected_spec_nodes") or [])
                    if str(node.get("target_section") or node.get("node_id") or "").strip()
                ],
                "completion_status": "partial",
                "confidence": str(turn_result.turn.get("confidence") or "medium"),
            },
            interaction_output={
                "assistant_message": str(turn_result.turn.get("spec_execution", {}).get("assistant_message") or ""),
                "next_question": str(turn_result.turn.get("next_interaction", {}).get("prompt") or ""),
                "quick_options": list(turn_result.turn.get("next_interaction", {}).get("options") or []),
                "suggested_focus": dict(turn_result.turn.get("next_interaction") or {}),
            },
            process_output={
                "stage_results": [],
                "stage_audits": list(turn_result.turn.get("stage_audits") or []),
                "decision_trace": list(turn_result.turn.get("decision_trace") or []),
                "provider_logs": list(turn_result.provider_logs),
                "review_after_apply_result": dict(turn_result.turn.get("review_after_apply_result") or {}),
                "annotations": list(turn_result.state_patch.get("annotations") or []),
                "risks": list(turn_result.state_patch.get("risks") or []),
            },
            state_output={
                "confirmed_facts_delta": list(turn_result.turn.get("spec_execution", {}).get("confirmed_facts") or []),
                "open_questions_delta": list(turn_result.turn.get("next_interaction_plan", {}).get("quick_options") or []),
                "spec_tree_update": {},
                "working_document_update": dict(turn_result.turn.get("spec_execution", {}).get("working_document_update") or {}),
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": {"turn": turn_result.turn},
                "raw_model_response": dict(turn_result.turn.get("raw_model_response") or {}),
                "raw_workflow_trace": {},
                "turn_execution_result": turn_result,
            },
        )

    def _runtime(self):
        from .local_xg_turn_runtime import LocalXGTurnRuntime
        from .turn_stage_executor import TurnStageExecutor
        from .turn_stage_planner import TurnStagePlanner
        from .turn_stage_reducer import TurnStageReducer
        from .turn_strategy_service import TurnStrategyService

        if self.runtime_host is None:
            raise RuntimeError("runtime_host_missing")
        return self.runtime_host.build_local_xg_turn_runtime(
            runtime_cls=LocalXGTurnRuntime,
            turn_strategy_service_cls=TurnStrategyService,
            turn_stage_planner_cls=TurnStagePlanner,
            turn_stage_executor_cls=TurnStageExecutor,
            turn_stage_reducer_cls=TurnStageReducer,
        )

    def _session_snapshot(self, request: OrchestratorRunRequest) -> SessionSnapshot:
        session = dict(request.session or {})
        context = dict(request.document_context or {})
        payload = dict(context.get("state") or {})
        payload.setdefault("turns", [])
        payload.setdefault("messages", [])
        payload.setdefault("confirmed_facts", list(context.get("confirmed_facts") or []))
        payload.setdefault("open_questions", [])
        payload.setdefault("document_patch", [])
        payload.setdefault("working_document", dict(context.get("working_document") or {}))
        payload.setdefault("questions", list(context.get("open_questions") or []))
        payload.setdefault("facts", [])
        payload.setdefault("patches", list(context.get("patches") or []))
        payload.setdefault("spec_tree", list(context.get("spec_tree") or []))
        payload.setdefault("active_spec_node_id", str((context.get("active_spec_node") or {}).get("node_id") or ""))
        payload.setdefault("turn_path", [])
        payload.setdefault("next_interaction", dict(request.turn.get("previous_interaction") or {}))
        payload.setdefault("last_quick_options", [])
        payload.setdefault("annotations", [])
        payload.setdefault("risks", [])
        payload.setdefault("provider_logs", [])
        return SessionSnapshot(
            session_id=str(session.get("session_id") or ""),
            topic=str(session.get("topic") or ""),
            orchestrator_id=self.manifest.plugin_id,
            provider_id=str(session.get("provider_id") or "mock"),
            model=str(session.get("model") or "mock-requirement-analysis-v1"),
            template_id=str(session.get("template_id") or "81433号"),
            knowledge_package_id=str(session.get("knowledge_package_id") or ""),
            write_policy=str(session.get("write_policy") or "patch_suggestion_only"),
            status="created",
            payload=payload,
        )
