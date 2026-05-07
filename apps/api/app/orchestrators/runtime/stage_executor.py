from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.provider_call_service import ProviderRunResult, RequirementAnalysisProviderCallService
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.turn_context_builder import TurnContext


@dataclass(frozen=True)
class TurnStageResult:
    stage_id: str
    stage_type: str
    provider_run_result: ProviderRunResult
    model_output: dict


class TurnStageExecutor:
    def __init__(self, *, provider_call_service: RequirementAnalysisProviderCallService) -> None:
        self.provider_call_service = provider_call_service

    def run(
        self,
        *,
        stage: dict,
        orchestrator: OrchestratorPackage,
        session: SessionSnapshot,
        context: TurnContext,
        stage_input: dict | None = None,
    ) -> TurnStageResult:
        stage_type = str(stage.get("stage_type") or orchestrator.mode)
        if session.provider_id == "mock" and orchestrator.mode != "local_runner":
            provider_run_result = self._mock_stage_provider(orchestrator=orchestrator).run(
                orchestrator=orchestrator,
                session=session,
                user_input=context.user_input,
                normalized=context.normalized_input,
                stage=stage,
                stage_input=stage_input or {},
            )
        else:
            provider_run_result = self.provider_call_service.run_orchestrator(
                orchestrator=orchestrator,
                session=session,
                user_input=context.user_input,
                normalized=context.normalized_input,
                stage=stage,
                stage_input=stage_input or {},
            )
        return TurnStageResult(
            stage_id=str(stage.get("stage_id") or "stage-001"),
            stage_type=stage_type,
            provider_run_result=provider_run_result,
            model_output=provider_run_result.model_output,
        )

    def _mock_stage_provider(self, *, orchestrator: OrchestratorPackage):
        from app.orchestrators.plugin_registry import get_orchestrator_plugin_registry

        plugin = get_orchestrator_plugin_registry().require(orchestrator.orchestrator_id)
        package_path = plugin.package_path
        if package_path.endswith("brainstorm-v1"):
            from _codefactory_plugin_brainstorm_v1.local_xg_mock_stage_provider import LocalXGMockStageProvider

            return LocalXGMockStageProvider(provider_call_service=self.provider_call_service)
        if package_path.endswith("xg-heuristic-orchestrator"):
            from _codefactory_plugin_xg_local_heuristic_orchestrator.local_xg_mock_stage_provider import LocalXGMockStageProvider

            return LocalXGMockStageProvider(provider_call_service=self.provider_call_service)
        raise ValueError(f"unsupported local mock stage provider package: {package_path}")
