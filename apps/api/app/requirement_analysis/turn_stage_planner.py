from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.turn_context_builder import TurnContext
from app.requirement_analysis.turn_strategy_service import XGTurnStrategy


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
        stage_id = str(stage.get("stage_id") or "stage-001")
        stage_type = str(stage.get("stage_type") or orchestrator.mode)
        stage_kind = str(stage.get("stage_kind") or TurnStagePlanner._infer_stage_kind(stage_id, stage_type))
        execution_mode = str(stage.get("execution_mode") or TurnStagePlanner._execution_mode(stage_type))
        return {
            **stage,
            "stage_id": stage_id,
            "stage_type": stage_type,
            "stage_kind": stage_kind,
            "execution_mode": execution_mode,
            "provider_id": str(stage.get("provider_id") or context.provider_id),
            "model": str(stage.get("model") or context.model),
            "input_sources": list(stage.get("input_sources") or TurnStagePlanner._input_sources(stage_kind)),
            "requires_provider_call": bool(
                stage.get("requires_provider_call")
                if "requires_provider_call" in stage
                else execution_mode in {"model", "local_runner"}
            ),
            "adopt_fields": list(stage.get("adopt_fields") or TurnStagePlanner._adopt_fields(stage_kind)),
            "failure_policy": str(stage.get("failure_policy") or "block_turn"),
        }

    @staticmethod
    def _infer_stage_kind(stage_id: str, stage_type: str) -> str:
        if "intent" in stage_id:
            return "intent"
        if "next_interaction" in stage_id or "planning" in stage_id:
            return "next_interaction"
        if "review" in stage_id:
            return "review"
        if stage_type == "local_runner":
            return "write"
        return "write"

    @staticmethod
    def _execution_mode(stage_type: str) -> str:
        if stage_type == "local_runner":
            return "local_runner"
        return "model"

    @staticmethod
    def _input_sources(stage_kind: str) -> list[str]:
        if stage_kind == "intent":
            return ["turn_context", "previous_interaction", "working_document", "spec_tree"]
        if stage_kind == "review":
            return ["working_document_after_apply", "working_document_update"]
        if stage_kind == "next_interaction":
            return ["review_after_apply", "spec_tree", "working_document"]
        return ["session_snapshot", "turn_context"]

    @staticmethod
    def _adopt_fields(stage_kind: str) -> list[str]:
        if stage_kind == "intent":
            return [
                "intent_understanding_result",
                "target_document_structure",
                "stage_task_definition",
                "stage_quality_constraints",
                "confidence",
            ]
        if stage_kind == "review":
            return ["post_update_review", "annotations"]
        if stage_kind == "next_interaction":
            return ["next_interaction_plan", "planning_trace", "confidence"]
        return ["organizer_interpretation", "confirmed_facts_delta", "document_patch", "next_interaction_candidate"]
