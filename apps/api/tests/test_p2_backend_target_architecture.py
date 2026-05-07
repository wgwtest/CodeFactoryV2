from importlib import import_module
import inspect
from dataclasses import is_dataclass

from app.orchestrators.adapters.base import load_orchestrator_plugin_adapter
from app.orchestrators.plugin_registry import OrchestratorPluginRegistry
from app.requirement_analysis.session_service import RequirementAnalysisSessionService
from app.requirement_analysis.turn_engine import RequirementAnalysisTurnEngine


def test_p2_backend_target_modules_are_exposed() -> None:
    requirement_configuration = import_module("app.requirement_configuration")
    requirement_exchange = import_module("app.requirement_exchange")
    requirement_authoring = import_module("app.requirement_authoring")

    assert requirement_configuration is not None
    assert requirement_exchange is not None
    assert requirement_authoring is not None


def test_p2_backend_target_services_can_be_imported() -> None:
    template_application_service = import_module("app.requirement_configuration.template_application_service")
    exchange_application_service = import_module("app.requirement_exchange.exchange_application_service")
    document_application_service = import_module("app.requirement_authoring.document_application_service")
    analysis_application_service = import_module("app.requirement_analysis.session_application_service")

    assert hasattr(template_application_service, "RequirementConfigurationApplicationService")
    assert hasattr(exchange_application_service, "RequirementExchangeApplicationService")
    assert hasattr(document_application_service, "RequirementAuthoringApplicationService")
    assert hasattr(analysis_application_service, "RequirementAnalysisApplicationService")


def test_requirement_analysis_j5_services_can_be_imported() -> None:
    session_snapshot = import_module("app.requirement_analysis.session_snapshot")
    turn_context_builder = import_module("app.requirement_analysis.turn_context_builder")
    turn_execution_result = import_module("app.requirement_analysis.turn_execution_result")
    turn_decision_service = import_module("app.requirement_analysis.turn_decision_service")
    spec_projection_service = import_module("app.requirement_analysis.spec_projection_service")
    next_interaction_service = import_module("app.requirement_analysis.next_interaction_service")
    provider_call_log_service = import_module("app.requirement_analysis.provider_call_log_service")
    provider_call_service = import_module("app.requirement_analysis.provider_call_service")
    summary_artifact_service = import_module("app.requirement_analysis.summary_artifact_service")
    spec_tree_service = import_module("app.requirement_analysis.spec_tree_service")
    stage_prompt_resolver = import_module("app.orchestrators.stage_prompt_resolver")
    stage_schema_resolver = import_module("app.orchestrators.stage_schema_resolver")
    stage_adoption_policy_resolver = import_module("app.orchestrators.stage_adoption_policy_resolver")
    stage_prompt_bundle_builder = import_module("app.orchestrators.stage_prompt_bundle_builder")
    manifest = OrchestratorPluginRegistry().require("xg-local-heuristic-orchestrator")
    adapter = load_orchestrator_plugin_adapter(manifest)
    plugin_module_prefix = adapter.__class__.__module__.rsplit(".", 1)[0]
    turn_strategy_service = import_module(f"{plugin_module_prefix}.turn_strategy_service")
    turn_stage_planner = import_module(f"{plugin_module_prefix}.turn_stage_planner")
    turn_stage_executor = import_module(f"{plugin_module_prefix}.turn_stage_executor")
    turn_stage_reducer = import_module(f"{plugin_module_prefix}.turn_stage_reducer")
    stage_runtime_context_builder = import_module(f"{plugin_module_prefix}.stage_runtime_context_builder")

    assert hasattr(session_snapshot, "SessionSnapshot")
    assert hasattr(turn_context_builder, "TurnContext")
    assert hasattr(turn_context_builder, "TurnContextBuilder")
    assert hasattr(turn_execution_result, "TurnExecutionResult")
    assert hasattr(turn_strategy_service, "TurnStrategyService")
    assert hasattr(turn_strategy_service, "XGTurnStrategy")
    assert hasattr(turn_stage_planner, "TurnStagePlanner")
    assert hasattr(turn_stage_planner, "TurnStagePlan")
    assert hasattr(turn_stage_executor, "TurnStageExecutor")
    assert hasattr(turn_stage_executor, "TurnStageResult")
    assert hasattr(turn_stage_reducer, "TurnStageReducer")
    assert hasattr(turn_stage_reducer, "TurnStageAudit")
    assert hasattr(stage_runtime_context_builder, "StageRuntimeContext")
    assert hasattr(stage_runtime_context_builder, "StageRuntimeContextBuilder")
    assert hasattr(turn_decision_service, "TurnDecisionService")
    assert hasattr(turn_decision_service, "TurnDecisionResult")
    assert hasattr(spec_projection_service, "SpecProjectionService")
    assert hasattr(next_interaction_service, "NextInteractionService")
    assert hasattr(provider_call_log_service, "ProviderCallLogService")
    assert hasattr(provider_call_service, "ProviderRunResult")
    assert hasattr(summary_artifact_service, "ArtifactUpdateResult")
    assert hasattr(spec_tree_service, "SpecTreeUpdateResult")
    assert hasattr(stage_prompt_resolver, "StagePromptResolver")
    assert hasattr(stage_prompt_resolver, "StagePrompt")
    assert hasattr(stage_schema_resolver, "StageSchemaResolver")
    assert hasattr(stage_adoption_policy_resolver, "StageAdoptionPolicyResolver")
    assert hasattr(stage_prompt_bundle_builder, "StagePromptBundleBuilder")

    assert is_dataclass(session_snapshot.SessionSnapshot)
    assert is_dataclass(turn_execution_result.TurnExecutionResult)
    assert is_dataclass(turn_stage_planner.TurnStagePlan)
    assert is_dataclass(turn_stage_reducer.TurnStageAudit)
    assert is_dataclass(stage_runtime_context_builder.StageRuntimeContext)
    assert is_dataclass(turn_decision_service.TurnDecisionResult)
    assert is_dataclass(provider_call_service.ProviderRunResult)
    assert is_dataclass(summary_artifact_service.ArtifactUpdateResult)
    assert is_dataclass(spec_tree_service.SpecTreeUpdateResult)
    assert is_dataclass(stage_prompt_resolver.StagePrompt)


def test_requirement_analysis_turn_engine_has_no_owner_back_reference() -> None:
    source = inspect.getsource(RequirementAnalysisTurnEngine)

    assert "self.owner" not in source
    assert "owner:" not in source


def test_requirement_analysis_turn_engine_returns_result_without_writing_session_state() -> None:
    source = inspect.getsource(RequirementAnalysisTurnEngine)

    assert hasattr(RequirementAnalysisTurnEngine, "run_turn")
    assert not hasattr(RequirementAnalysisTurnEngine, "add_turn")
    assert "session.payload =" not in source
    assert "session.status =" not in source


def test_requirement_analysis_plugin_runtime_passes_full_context_to_review_stage() -> None:
    manifest = OrchestratorPluginRegistry().require("xg-local-heuristic-orchestrator")
    adapter = load_orchestrator_plugin_adapter(manifest)
    plugin_module_prefix = adapter.__class__.__module__.rsplit(".", 1)[0]
    runtime_module = import_module(f"{plugin_module_prefix}.local_xg_turn_runtime")
    source = inspect.getsource(runtime_module.LocalXGTurnRuntime)

    assert "stage_input=review_stage_input" not in source
    assert "review_stage_input = self._review_stage_input" in source
    assert "stage_input.update(review_stage_input)" in source
    assert "decision_state=decision_state" in source
    assert "decision_state_document=decision_state_document" in source
    assert "review_after_apply_result=review_after_apply_result" in source


def test_requirement_analysis_session_service_owns_turn_result_write_boundary() -> None:
    assert hasattr(RequirementAnalysisSessionService, "apply_turn_execution_result")
    assert hasattr(RequirementAnalysisSessionService, "load_snapshot")


def test_requirement_analysis_session_service_does_not_expose_turn_delegate_methods() -> None:
    forbidden_methods = {
        "_normalize_input",
        "_normalize_quick_options",
        "_run_orchestrator",
        "_build_structured_summary_update",
        "_update_spec_tree",
        "_select_projection_spec_node_id",
        "_ensure_next_open_question",
        "_affected_spec_nodes",
        "_previous_interaction",
        "_classify_input_relation",
        "_spec_execution",
        "_post_update_review",
        "_closure_decision",
        "_next_interaction",
        "_provider_log",
    }

    service_methods = set(dir(RequirementAnalysisSessionService))

    assert forbidden_methods.isdisjoint(service_methods)
