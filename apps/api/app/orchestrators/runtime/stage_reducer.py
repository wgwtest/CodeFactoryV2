from __future__ import annotations

from dataclasses import dataclass

from .stage_executor import TurnStageResult
from .stage_plan import TurnStagePlan


@dataclass(frozen=True)
class TurnStageAudit:
    stage_id: str
    stage_kind: str
    stage_type: str
    execution_mode: str
    provider_call_log_id: str | None
    validation_status: str
    blocking_used: bool
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
            "blocking_used": self.blocking_used,
            "adopted_fields": list(self.adopted_fields),
            "summary": self.summary,
        }


class TurnStageReducer:
    def reduce_intent_stage(self, *, plan: TurnStagePlan, stage_results: list[TurnStageResult]) -> dict:
        intent_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "intent"]
        if not intent_results:
            return {
                "intent_understanding_result": {},
                "target_document_structure": {},
                "stage_task_definition": {},
                "stage_quality_constraints": {},
                "confidence": "medium",
            }
        return dict(intent_results[-1].model_output)

    def reduce_write_stage(self, *, plan: TurnStagePlan, stage_results: list[TurnStageResult]) -> dict:
        write_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "write"]
        if not write_results:
            raise ValueError("turn stage results include no write stage")
        return dict(write_results[0].model_output)

    def reduce_decision_state_delta_stage(self, *, plan: TurnStagePlan, stage_results: list[TurnStageResult]) -> dict:
        results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "decision_state_delta"]
        if not results:
            raise ValueError("turn stage results include no decision_state_delta stage")
        return dict(results[-1].model_output)

    def reduce_review_stage(
        self,
        *,
        plan: TurnStagePlan,
        stage_results: list[TurnStageResult],
        target_review: dict,
        global_review: dict,
    ) -> dict:
        review_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "review"]
        resolved_target_review = dict(target_review)
        resolved_global_review = dict(global_review)
        if review_results:
            review_output = dict(review_results[-1].model_output)
            if isinstance(review_output.get("target_review"), dict):
                resolved_target_review = self._merge_target_review(
                    fallback=target_review,
                    override=review_output["target_review"],
                )
            if isinstance(review_output.get("global_review"), dict):
                resolved_global_review = self._merge_global_review(
                    fallback=global_review,
                    override=review_output["global_review"],
                )
        if resolved_global_review.get("status") == "continue_same_target":
            resolved_global_review["status"] = "continue_same_topic"
        return {
            "target_review": resolved_target_review,
            "global_review": resolved_global_review,
            "review_stage_output": dict(review_results[-1].model_output) if review_results else {},
        }

    def reduce_next_interaction_stage(self, *, plan: TurnStagePlan, stage_results: list[TurnStageResult]) -> dict:
        next_results = [result for result in stage_results if self._stage_kind(plan, result.stage_id) == "next_interaction"]
        if not next_results:
            return {
                "next_interaction_plan": {},
                "planning_trace": [],
                "confidence": "medium",
            }
        return dict(next_results[-1].model_output)

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _merge_target_review(self, *, fallback: dict, override: dict) -> dict:
        return {
            "status": str(override.get("status") or fallback.get("status") or "insufficient"),
            "review_target": self._string_list(override.get("review_target"))
            or self._string_list(fallback.get("review_target")),
            "reason": str(override.get("reason") or fallback.get("reason") or ""),
            "covered_points": self._string_list(override.get("covered_points"))
            or self._string_list(fallback.get("covered_points")),
            "missing_aspects": self._string_list(override.get("missing_aspects"))
            or self._string_list(fallback.get("missing_aspects")),
            "evidence_block_ids": self._string_list(override.get("evidence_block_ids"))
            or self._string_list(fallback.get("evidence_block_ids")),
            "evidence_fragment_ids": self._string_list(override.get("evidence_fragment_ids"))
            or self._string_list(fallback.get("evidence_fragment_ids")),
        }

    def _merge_global_review(self, *, fallback: dict, override: dict) -> dict:
        return {
            "status": str(override.get("status") or fallback.get("status") or "continue_same_topic"),
            "summary": str(override.get("summary") or fallback.get("summary") or ""),
            "remaining_gaps": self._string_list(override.get("remaining_gaps"))
            or self._string_list(fallback.get("remaining_gaps")),
        }

    def stage_audit(
        self,
        *,
        stage: dict,
        validation_status: str,
        adopted_fields: list[str],
        provider_call_log_id: str | None = None,
        summary: str = "",
        blocking_used: bool = False,
    ) -> TurnStageAudit:
        return TurnStageAudit(
            stage_id=str(stage.get("stage_id") or "stage-001"),
            stage_kind=str(stage.get("stage_kind") or "write"),
            stage_type=str(stage.get("stage_type") or ""),
            execution_mode=str(stage.get("execution_mode") or ""),
            provider_call_log_id=provider_call_log_id,
            validation_status=validation_status,
            blocking_used=blocking_used,
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
        if stage_kind == "intent":
            return f"阶段 {stage_id} 已生成意图理解、目标文档结构和阶段任务定义。"
        if stage_kind == "review":
            return f"阶段 {stage_id} 已基于应用后的临时正文生成回看审计。"
        if stage_kind == "decision_state_delta":
            return f"阶段 {stage_id} 已生成结构化状态增量与正文投影候选。"
        if stage_kind == "next_interaction":
            return f"阶段 {stage_id} 已基于结构化状态生成下一步交互规划。"
        return f"阶段 {stage_id} 已生成理解、事实和正文 patch 候选。"

    @staticmethod
    def _stage_kind(plan: TurnStagePlan, stage_id: str) -> str:
        for stage in plan.stages:
            if stage.get("stage_id") == stage_id:
                return str(stage.get("stage_kind") or "write")
        return "write"
