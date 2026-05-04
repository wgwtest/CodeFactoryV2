from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import OrchestratorPackage, OrchestratorRegistry, get_orchestrator_registry
from app.requirement_analysis.turn_context_builder import TurnContext


@dataclass(frozen=True)
class XGTurnStrategy:
    strategy_id: str
    orchestrator_id: str
    orchestrator_mode: str
    stages: tuple[dict, ...]
    adoption_policy: str


class TurnStrategyService:
    def __init__(self, *, registry: OrchestratorRegistry | None = None) -> None:
        self.registry = registry or get_orchestrator_registry()

    def load(self, *, orchestrator: OrchestratorPackage, context: TurnContext) -> XGTurnStrategy:
        loaded = self.registry.require_loaded(orchestrator.orchestrator_id)
        declared = dict(loaded.spec_strategy.get("turn_strategy") or {})
        stages = tuple(self._normalize_stage(item, context=context, orchestrator=orchestrator) for item in declared.get("stages", []))
        if not stages:
            stages = (
                self._normalize_stage(
                    {"stage_id": "stage-001", "stage_type": orchestrator.mode},
                    context=context,
                    orchestrator=orchestrator,
                ),
            )
        return XGTurnStrategy(
            strategy_id=f"{orchestrator.orchestrator_id}:{str(declared.get('strategy_id') or 'single_stage')}",
            orchestrator_id=orchestrator.orchestrator_id,
            orchestrator_mode=orchestrator.mode,
            stages=stages,
            adoption_policy=str(declared.get("adoption_policy") or "adopt_first_completed_stage"),
        )

    @staticmethod
    def _normalize_stage(stage: dict, *, context: TurnContext, orchestrator: OrchestratorPackage) -> dict:
        return {
            "stage_id": str(stage.get("stage_id") or "stage-001"),
            "stage_type": str(stage.get("stage_type") or orchestrator.mode),
            "provider_id": str(stage.get("provider_id") or context.provider_id),
            "model": str(stage.get("model") or context.model),
        }
