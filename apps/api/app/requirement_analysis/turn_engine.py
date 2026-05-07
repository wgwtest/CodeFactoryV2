from __future__ import annotations

from app.orchestrators.adapters.base import load_orchestrator_plugin_adapter
from app.orchestrators.plugin_contracts import OrchestratorRunRequest
from app.orchestrators.plugin_registry import get_orchestrator_plugin_registry
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.turn_context_builder import TurnContextBuilder
from app.requirement_analysis.turn_execution_result import TurnExecutionResult
from app.requirement_analysis.working_document_service import WorkingDocumentService


class RequirementAnalysisTurnEngine:
    def __init__(
        self,
        *,
        turn_context_builder: TurnContextBuilder,
        working_document_service: WorkingDocumentService,
        **_dependencies,
    ) -> None:
        self.turn_context_builder = turn_context_builder
        self.working_document_service = working_document_service

    def run_turn(self, session: SessionSnapshot, payload: RequirementAnalysisTurnCreate) -> TurnExecutionResult:
        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        turn_id = f"turn-{len(turns) + 1:04d}"
        user_input = payload.user_input.strip()
        context = self.turn_context_builder.build(session=session, turn_id=turn_id, user_input=user_input)
        working_document = dict(
            context.working_document
            or self.working_document_service.initialize(topic=session.topic, template_id=session.template_id)
        )
        plugin = get_orchestrator_plugin_registry().require(session.orchestrator_id)
        adapter = load_orchestrator_plugin_adapter(plugin)
        result = adapter.run(
            self._build_plugin_request(
                session=session,
                context=context,
                turn_id=turn_id,
                user_input=user_input,
                working_document=working_document,
            )
        )
        passthrough = (result.raw_output or {}).get("turn_execution_result")
        if isinstance(passthrough, TurnExecutionResult):
            return passthrough
        if isinstance(passthrough, dict):
            return TurnExecutionResult(
                turn=dict(passthrough.get("turn") or {}),
                state_patch=dict(passthrough.get("state_patch") or {}),
                provider_logs=list(passthrough.get("provider_logs") or []),
            )
        raise ValueError("orchestrator adapter did not return turn_execution_result")

    def _build_plugin_request(
        self,
        *,
        session: SessionSnapshot,
        context,
        turn_id: str,
        user_input: str,
        working_document: dict,
    ) -> OrchestratorRunRequest:
        return OrchestratorRunRequest(
            contract_version="xg-observable-orchestrator-contract@1",
            session={
                "session_id": session.session_id,
                "topic": session.topic,
                "template_id": session.template_id,
                "knowledge_package_id": session.knowledge_package_id,
                "orchestrator_id": session.orchestrator_id,
                "provider_id": session.provider_id,
                "model": session.model,
                "write_policy": session.write_policy,
            },
            turn={
                "turn_id": turn_id,
                "turn_index": context.turn_index,
                "user_input": user_input,
                "normalized_input": context.normalized_input,
                "previous_interaction": context.previous_interaction,
                "input_relation": context.input_relation,
            },
            template={
                "template_id": session.template_id,
                "format": "structured",
                "content": "",
                "parsed_structure": {"spec_tree": context.spec_tree},
            },
            document_context={
                "state": dict(session.payload or {}),
                "working_document": working_document,
                "active_spec_node": context.active_spec_node,
                "spec_tree": context.spec_tree,
                "confirmed_facts": context.facts,
                "open_questions": context.questions,
                "patches": context.patches,
                "history_summary": "",
            },
            execution_options={
                "expected_output": "both",
                "observability_required": "full",
                "streaming_enabled": False,
            },
        )
