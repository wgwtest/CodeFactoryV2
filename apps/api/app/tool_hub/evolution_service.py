from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from app.tool_hub.models import (
    EvolutionConfigReadEnvelope,
    EvolutionConfigUpdateRequest,
    EvolutionFinding,
    EvolutionFindingDecisionRequest,
    EvolutionInspectionConfig,
    EvolutionRollbackRecord,
    EvolutionRun,
    EvolutionRunEnvelope,
    EvolutionRunReadEnvelope,
    EvolutionTask,
    EvolutionTaskEnvelope,
    EvolutionTaskReadEnvelope,
    EvolutionTaskRollbackRequest,
    ToolDefinition,
    now_iso,
)
from app.tool_hub.snapshot import build_evolution_run

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class EvolutionService:
    def __init__(self, hub: "ToolHubService") -> None:
        self.hub = hub
        self.repository = hub.repository

    def list_evolution_runs(self) -> EvolutionRunReadEnvelope:
        projection = self.hub.query_service.get_evolution_workspace_projection()
        return EvolutionRunReadEnvelope(
            meta=projection.meta,
            data=EvolutionRunEnvelope(items=projection.runs),
        )

    def get_evolution_run(self, run_id: str) -> EvolutionRun | None:
        return self.repository.get_evolution_run(run_id)

    def get_evolution_config(self) -> EvolutionConfigReadEnvelope:
        projection = self.hub.query_service.get_evolution_workspace_projection()
        return EvolutionConfigReadEnvelope(
            meta=projection.meta,
            data=projection.config,
        )

    def update_evolution_config(
        self,
        payload: EvolutionConfigUpdateRequest | dict,
        *,
        actor_id: str,
    ) -> EvolutionInspectionConfig:
        current = self.repository.get_evolution_config()
        request = payload if isinstance(payload, EvolutionConfigUpdateRequest) else EvolutionConfigUpdateRequest.model_validate(payload)
        updated = current.model_copy(
            update={
                **{
                    field: value
                    for field, value in request.model_dump(exclude_none=True).items()
                },
                "updated_by": actor_id,
                "updated_at": now_iso(),
            }
        )
        saved = self.repository.save_evolution_config(updated)
        self.mark_dirty()
        return saved

    def list_evolution_tasks(self) -> EvolutionTaskReadEnvelope:
        projection = self.hub.query_service.get_evolution_workspace_projection()
        return EvolutionTaskReadEnvelope(
            meta=projection.meta,
            data=EvolutionTaskEnvelope(items=projection.tasks),
        )

    def get_evolution_task(self, task_id: str) -> EvolutionTask | None:
        return self.repository.get_evolution_task(task_id)

    def run_evolution(
        self,
        *,
        actor_id: str = "p4-system",
        trigger_type: str = "manual",
    ) -> EvolutionRun:
        self.hub._ensure_demo_data()
        config = self.repository.get_evolution_config()
        snapshot_id = self.hub.get_snapshot().meta.snapshot_id
        run = build_evolution_run(
            self.repository.list_tools(),
            overlap_threshold=config.overlap_threshold,
            include_draft_tools=config.include_draft_tools,
            trigger_type=trigger_type,
            triggered_by=actor_id,
            snapshot_id=snapshot_id,
        )
        saved = self.repository.save_evolution_run(run)
        current_state = self.repository.get_runtime_state()
        state = current_state.model_copy(
            update={
                "evolution_dirty": False,
                "last_scheduled_evolution_at": now_iso()
                if trigger_type == "scheduled"
                else current_state.last_scheduled_evolution_at,
                "updated_at": now_iso(),
            }
        )
        self.repository.save_runtime_state(state)
        self.hub._trim_evolution_run_history(config.max_run_history)
        return saved

    def decide_evolution_finding(
        self,
        finding_id: str,
        payload: EvolutionFindingDecisionRequest,
    ) -> EvolutionFinding | None:
        located = self.repository.get_evolution_finding(finding_id)
        if located is None:
            return None
        run, finding_index = located
        finding = run.findings[finding_index]
        if finding.decision_status != "pending":
            raise ValueError("Evolution finding is already decided")

        updated_finding = finding.model_copy(
            update={
                "decision_status": "ignored" if payload.decision == "ignore" else "accepted_to_task",
                "decision_by": payload.actor_id,
                "decision_at": now_iso(),
                "decision_note": payload.note,
                "updated_at": now_iso(),
            }
        )

        if payload.decision == "accept":
            task = self.hub._build_evolution_task(updated_finding, payload.actor_id)
            self.repository.save_evolution_task(task)
            self.hub.runtime_service.enqueue_evolution_task_job(task.task_id, payload.actor_id)
            updated_finding = updated_finding.model_copy(
                update={"linked_task_id": task.task_id, "updated_at": now_iso()}
            )

        updated_run = run.model_copy(
            update={
                "findings": [
                    item if index != finding_index else updated_finding
                    for index, item in enumerate(run.findings)
                ],
                "updated_at": now_iso(),
            }
        )
        refreshed_run = updated_run.model_copy(
            update={"summary": self.hub._build_evolution_run_summary(updated_run.findings, updated_run.summary.tool_count)}
        )
        self.repository.save_evolution_run(refreshed_run)
        return refreshed_run.findings[finding_index]

    def rollback_evolution_task(
        self,
        task_id: str,
        payload: EvolutionTaskRollbackRequest,
    ) -> EvolutionTask | None:
        task = self.repository.get_evolution_task(task_id)
        if task is None:
            return None
        if task.task_status != "completed" or not task.rollback_available:
            raise ValueError("Current evolution task cannot be rolled back")

        change_sets = list(reversed(self.repository.list_evolution_change_sets(task_id)))
        if not change_sets:
            raise ValueError("Current evolution task has no reversible change set")

        for change_set in change_sets:
            restored = ToolDefinition.model_validate(change_set.before_snapshot)
            self.repository.save_tool(restored)

        rollback = EvolutionRollbackRecord(
            rollback_id=f"erb-{uuid4().hex[:12]}",
            task_id=task.task_id,
            change_set_ids=[item.change_set_id for item in change_sets],
            rolled_back_by=payload.actor_id,
            rollback_summary=payload.note or f"已回退 {len(change_sets)} 项自动改写。",
        )
        self.repository.save_evolution_rollback(rollback)

        updated_task = task.model_copy(
            update={
                "task_status": "rolled_back",
                "rollback_available": False,
                "result_summary": rollback.rollback_summary,
                "updated_at": now_iso(),
            }
        )
        self.repository.save_evolution_task(updated_task)
        self.mark_dirty()
        return updated_task

    def mark_dirty(self):
        state = self.repository.get_runtime_state().model_copy(
            update={"evolution_dirty": True, "updated_at": now_iso()}
        )
        return self.repository.save_runtime_state(state)

    def run_scheduled_cycle(self) -> None:
        config = self.repository.get_evolution_config()
        runtime_state = self.repository.get_runtime_state()
        if not config.enabled or not runtime_state.evolution_dirty:
            return

        last_scheduled = runtime_state.last_scheduled_evolution_at
        if last_scheduled is not None:
            elapsed_seconds = (datetime.now(tz=UTC) - datetime.fromisoformat(last_scheduled)).total_seconds()
            if elapsed_seconds < max(config.interval_minutes * 60, 0):
                return

        self.run_evolution(actor_id="system", trigger_type="scheduled")

    def run_task_cycle(self) -> None:
        for task in self.repository.list_evolution_tasks():
            if task.task_type != "auto_apply" or task.task_status not in {"queued", "running"}:
                continue
            self.hub._advance_evolution_task(task)
