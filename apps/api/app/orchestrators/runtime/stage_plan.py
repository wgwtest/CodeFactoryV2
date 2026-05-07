from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.turn_context_builder import TurnContext
from .turn_strategy_service import XGTurnStrategy


@dataclass(frozen=True)
class TurnStagePlan:
    strategy_id: str
    orchestrator_id: str
    stages: tuple[dict, ...]
    adoption_policy: str

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "orchestrator_id": self.orchestrator_id,
            "stages": list(self.stages),
            "adoption_policy": self.adoption_policy,
        }


class TurnStagePlanner:
    def build_plan(
        self,
        *,
        strategy: XGTurnStrategy,
        context: TurnContext,
        orchestrator: OrchestratorPackage,
    ) -> TurnStagePlan:
        stages = tuple(self._normalize_stage(stage, context=context, orchestrator=orchestrator) for stage in strategy.stages)
        self.validate_plan(stages)
        return TurnStagePlan(
            strategy_id=strategy.strategy_id,
            orchestrator_id=strategy.orchestrator_id,
            stages=stages,
            adoption_policy=strategy.adoption_policy,
        )

    @staticmethod
    def validate_plan(stages: tuple[dict, ...]) -> None:
        if not stages:
            raise ValueError("turn stage plan has no stages")
        ids = [stage["stage_id"] for stage in stages]
        if len(ids) != len(set(ids)):
            raise ValueError("turn stage plan has duplicate stage_id")

    @staticmethod
    def _normalize_stage(stage: dict, *, context: TurnContext, orchestrator: OrchestratorPackage) -> dict:
        TurnStagePlanner._require_explicit_fields(stage)
        stage_id = str(stage["stage_id"])
        stage_type = str(stage.get("stage_type") or orchestrator.mode)
        stage_kind = str(stage["stage_kind"])
        execution_mode = str(stage["execution_mode"])
        return {
            **stage,
            "stage_id": stage_id,
            "stage_type": stage_type,
            "stage_kind": stage_kind,
            "execution_mode": execution_mode,
            "provider_id": str(stage.get("provider_id") or context.provider_id),
            "model": str(stage.get("model") or context.model),
            "input_sources": list(stage["input_sources"]),
            "requires_provider_call": bool(
                stage.get("requires_provider_call")
                if "requires_provider_call" in stage
                else execution_mode in {"model", "local_runner"}
            ),
            "adopt_fields": list(stage["adopt_fields"]),
            "schema_id": str(stage["schema_id"]),
            "adoption_id": str(stage["adoption_id"]),
            "output_targets": list(stage["output_targets"]),
            "failure_policy": str(stage["failure_policy"]),
        }

    @staticmethod
    def _require_explicit_fields(stage: dict) -> None:
        required = [
            "stage_id",
            "stage_kind",
            "execution_mode",
            "input_sources",
            "adopt_fields",
            "schema_id",
            "adoption_id",
            "output_targets",
            "failure_policy",
        ]
        missing = [field for field in required if field not in stage]
        if missing:
            stage_id = str(stage.get("stage_id") or "<unknown>")
            raise ValueError(f"turn stage {stage_id} missing explicit fields: {', '.join(missing)}")
