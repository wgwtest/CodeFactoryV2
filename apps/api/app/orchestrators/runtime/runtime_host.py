from __future__ import annotations

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest
from app.orchestrators.runtime.request_mapper import OrchestratorRunRequestMapper


class OrchestratorRuntimeHost:
    def __init__(
        self,
        *,
        turn_context_builder=None,
        provider_call_service=None,
        provider_call_log_service=None,
        spec_tree_service=None,
        spec_projection_service=None,
        summary_artifact_service=None,
        turn_audit_service=None,
        turn_output_service=None,
        next_interaction_service=None,
        working_document_service=None,
        working_document_review_service=None,
        turn_decision_service=None,
    ) -> None:
        self.turn_context_builder = turn_context_builder
        self.provider_call_service = provider_call_service
        self.provider_call_log_service = provider_call_log_service
        self.spec_tree_service = spec_tree_service
        self.spec_projection_service = spec_projection_service
        self.summary_artifact_service = summary_artifact_service
        self.turn_audit_service = turn_audit_service
        self.turn_output_service = turn_output_service
        self.next_interaction_service = next_interaction_service
        self.working_document_service = working_document_service
        self.working_document_review_service = working_document_review_service
        self.turn_decision_service = turn_decision_service

    def build_policy_interpreted_runtime(self):
        self._require(
            "turn_context_builder",
            "provider_call_service",
            "provider_call_log_service",
            "spec_tree_service",
            "spec_projection_service",
            "summary_artifact_service",
            "turn_audit_service",
            "turn_output_service",
            "next_interaction_service",
            "working_document_service",
            "working_document_review_service",
            "turn_decision_service",
        )
        from app.orchestrators.runtime.policy_interpreted_runtime import PolicyInterpretedRuntime
        from app.orchestrators.runtime.stage_executor import TurnStageExecutor
        from app.orchestrators.runtime.stage_plan import TurnStagePlanner
        from app.orchestrators.runtime.stage_reducer import TurnStageReducer
        from app.orchestrators.runtime.turn_strategy_service import TurnStrategyService

        return PolicyInterpretedRuntime(
            turn_context_builder=self.turn_context_builder,
            provider_call_service=self.provider_call_service,
            provider_call_log_service=self.provider_call_log_service,
            spec_tree_service=self.spec_tree_service,
            spec_projection_service=self.spec_projection_service,
            summary_artifact_service=self.summary_artifact_service,
            turn_audit_service=self.turn_audit_service,
            turn_output_service=self.turn_output_service,
            next_interaction_service=self.next_interaction_service,
            turn_strategy_service=TurnStrategyService(),
            turn_stage_planner=TurnStagePlanner(),
            turn_stage_executor=TurnStageExecutor(
                provider_call_service=self.provider_call_service,
            ),
            turn_stage_reducer=TurnStageReducer(),
            working_document_service=self.working_document_service,
            working_document_review_service=self.working_document_review_service,
            turn_decision_service=self.turn_decision_service,
        )

    def run_policy_interpreted(
        self,
        request: OrchestratorRunRequest,
        manifest: OrchestratorPluginManifest,
    ):
        runtime_input = OrchestratorRunRequestMapper().build(request=request, manifest=manifest)
        return self.build_policy_interpreted_runtime().run_turn(
            runtime_input.session_snapshot,
            runtime_input.turn_payload,
        )

    def build_local_xg_turn_runtime(
        self,
        *,
        runtime_cls,
        turn_strategy_service_cls,
        turn_stage_planner_cls,
        turn_stage_executor_cls,
        turn_stage_reducer_cls,
    ):
        self._require(
            "turn_context_builder",
            "provider_call_service",
            "provider_call_log_service",
            "spec_tree_service",
            "spec_projection_service",
            "summary_artifact_service",
            "turn_audit_service",
            "turn_output_service",
            "next_interaction_service",
            "working_document_service",
            "working_document_review_service",
            "turn_decision_service",
        )
        return runtime_cls(
            turn_context_builder=self.turn_context_builder,
            provider_call_service=self.provider_call_service,
            provider_call_log_service=self.provider_call_log_service,
            spec_tree_service=self.spec_tree_service,
            spec_projection_service=self.spec_projection_service,
            summary_artifact_service=self.summary_artifact_service,
            turn_audit_service=self.turn_audit_service,
            turn_output_service=self.turn_output_service,
            next_interaction_service=self.next_interaction_service,
            turn_strategy_service=turn_strategy_service_cls(),
            turn_stage_planner=turn_stage_planner_cls(),
            turn_stage_executor=turn_stage_executor_cls(
                provider_call_service=self.provider_call_service,
            ),
            turn_stage_reducer=turn_stage_reducer_cls(),
            working_document_service=self.working_document_service,
            working_document_review_service=self.working_document_review_service,
            turn_decision_service=self.turn_decision_service,
        )

    def _require(self, *names: str) -> None:
        missing = [name for name in names if getattr(self, name) is None]
        if missing:
            raise RuntimeError(f"orchestrator runtime host missing dependencies: {', '.join(missing)}")
