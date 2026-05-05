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
