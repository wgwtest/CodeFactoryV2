from __future__ import annotations

from dataclasses import dataclass

from app.requirement_analysis.turn_stage_executor import TurnStageResult
from app.requirement_analysis.turn_stage_planner import TurnStagePlan


@dataclass(frozen=True)
class TurnStageAudit:
    stage_id: str
    stage_kind: str
    stage_type: str
    execution_mode: str
    provider_call_log_id: str | None
    validation_status: str
    fallback_used: bool
    adopted_fields: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "stage_kind": self.stage_kind,
            "stage_type": self.stage_type,
            "execution_mode": self.execution_mode,
            "provider_call_log_id": self.provider_call_log_id,
            "validation_status": self.validation_status,
            "fallback_used": self.fallback_used,
            "adopted_fields": list(self.adopted_fields),
            "summary": self.summary,
        }


class TurnStageReducer:
    def reduce_write_stage(self, *, plan: TurnStagePlan, stage_results: list[TurnStageResult]) -> dict:
        write_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "write"]
        if not write_results:
            raise ValueError("turn stage results include no write stage")
        return dict(write_results[0].model_output)

    def reduce_review_stage(
        self,
        *,
        plan: TurnStagePlan,
        stage_results: list[TurnStageResult],
        target_review: dict,
        global_review: dict,
    ) -> dict:
        review_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "review"]
        return {
            "target_review": target_review,
            "global_review": global_review,
            "review_stage_output": dict(review_results[-1].model_output) if review_results else {},
        }

    def stage_audit(
        self,
        *,
        stage: dict,
        validation_status: str,
        adopted_fields: list[str],
        provider_call_log_id: str | None = None,
        summary: str = "",
        fallback_used: bool = False,
    ) -> TurnStageAudit:
        return TurnStageAudit(
            stage_id=str(stage.get("stage_id") or "stage-001"),
            stage_kind=str(stage.get("stage_kind") or "write"),
            stage_type=str(stage.get("stage_type") or ""),
            execution_mode=str(stage.get("execution_mode") or ""),
            provider_call_log_id=provider_call_log_id,
            validation_status=validation_status,
            fallback_used=fallback_used,
            adopted_fields=list(adopted_fields),
            summary=summary,
        )

    def build_audits(
        self,
        *,
        plan: TurnStagePlan,
        stage_results: list[TurnStageResult],
        provider_logs: list[dict],
    ) -> list[TurnStageAudit]:
        provider_log_by_stage = {log.get("stage_id"): log for log in provider_logs}
        result_by_stage = {result.stage_id: result for result in stage_results}
        audits: list[TurnStageAudit] = []
        for stage in plan.stages:
            stage_id = str(stage.get("stage_id"))
            result = result_by_stage.get(stage_id)
            provider_log = provider_log_by_stage.get(stage_id)
            stage_kind = str(stage.get("stage_kind") or "write")
            audits.append(
                self.stage_audit(
                    stage=stage,
                    validation_status="accepted" if result is not None else "skipped",
                    adopted_fields=list(stage.get("adopt_fields") or []),
                    provider_call_log_id=provider_log.get("call_id") if provider_log else None,
                    summary=self._summary(stage_kind=stage_kind, stage_id=stage_id),
                )
            )
        return audits

    @staticmethod
    def _summary(*, stage_kind: str, stage_id: str) -> str:
        if stage_kind == "review":
            return f"阶段 {stage_id} 已基于应用后的临时正文生成回看审计。"
        return f"阶段 {stage_id} 已生成理解、事实和正文 patch 候选。"

    @staticmethod
    def _stage_kind(plan: TurnStagePlan, stage_id: str) -> str:
        for stage in plan.stages:
            if stage.get("stage_id") == stage_id:
                return str(stage.get("stage_kind") or "write")
        return "write"
