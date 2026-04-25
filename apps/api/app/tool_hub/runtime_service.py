from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Callable
from uuid import uuid4

from app.tool_hub.models import ToolManufacturePlan, now_iso
from app.tool_hub.runtime_models import RuntimeCycleRunResult, RuntimeJob
from app.tool_hub.runtime_repository import RuntimeRepository

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class ToolHubRuntimeService:
    def __init__(self, tool_hub_service: "ToolHubService", *, worker_id: str = "p4-runtime-worker") -> None:
        self.tool_hub_service = tool_hub_service
        self.runtime_repository = RuntimeRepository(tool_hub_service.root)
        self.worker_id = worker_id
        self.lease_seconds = 30

    def enqueue_manufacture_job(self, plan: ToolManufacturePlan, actor_id: str) -> RuntimeJob:
        existing = self._find_open_job(queue_name="p4-manufacture", aggregate_id=plan.item_id)
        if existing is not None:
            return existing
        return self.runtime_repository.save_job(
            RuntimeJob(
                job_id=f"job-{uuid4().hex[:12]}",
                job_type="manufacture_execution",
                queue_name="p4-manufacture",
                aggregate_type="tool_manufacture_plan",
                aggregate_id=plan.item_id,
                trigger_source="internal_command",
                trigger_actor_id=actor_id,
                payload_ref=plan.item_id,
            )
        )

    def enqueue_build_job(self, build_run_id: str, actor_id: str) -> RuntimeJob:
        existing = self._find_open_job(queue_name="p4-build", aggregate_id=build_run_id)
        if existing is not None:
            return existing
        return self.runtime_repository.save_job(
            RuntimeJob(
                job_id=f"job-{uuid4().hex[:12]}",
                job_type="frontend_component_build",
                queue_name="p4-build",
                aggregate_type="tool_build_run",
                aggregate_id=build_run_id,
                trigger_source="internal_command",
                trigger_actor_id=actor_id,
                payload_ref=build_run_id,
            )
        )

    def enqueue_evolution_task_job(self, task_id: str, actor_id: str) -> RuntimeJob | None:
        task = self.tool_hub_service.repository.get_evolution_task(task_id)
        if task is None or task.task_type != "auto_apply":
            return None
        existing = self._find_open_job(queue_name="p4-evolution", aggregate_id=task_id)
        if existing is not None:
            return existing
        return self.runtime_repository.save_job(
            RuntimeJob(
                job_id=f"job-{uuid4().hex[:12]}",
                job_type="evolution_auto_apply",
                queue_name="p4-evolution",
                aggregate_type="evolution_task",
                aggregate_id=task_id,
                trigger_source="internal_command",
                trigger_actor_id=actor_id,
                payload_ref=task_id,
            )
        )

    def enqueue_scheduled_evolution_job(self, actor_id: str = "system") -> RuntimeJob:
        existing = self._find_open_job(queue_name="p4-evolution", aggregate_id="scheduled-evolution-scan")
        if existing is not None:
            return existing
        return self.runtime_repository.save_job(
            RuntimeJob(
                job_id=f"job-{uuid4().hex[:12]}",
                job_type="scheduled_evolution_scan",
                queue_name="p4-evolution",
                aggregate_type="tool_registry",
                aggregate_id="scheduled-evolution-scan",
                trigger_source="scheduler",
                trigger_actor_id=actor_id,
                payload_ref="scheduled-evolution-scan",
            )
        )

    def run_once(self) -> RuntimeCycleRunResult:
        scheduled_job_count = self._run_due_evolution_scan()
        scheduled_job_count += self._enqueue_due_manufacture_jobs()
        processed_queues: list[str] = []
        build_count = self._run_queue("p4-build", self._execute_build_job)
        if build_count > 0:
            processed_queues.append("p4-build")
        evolution_count = self._run_queue("p4-evolution", self._execute_evolution_job)
        if evolution_count > 0:
            processed_queues.append("p4-evolution")
        manufacture_count = self._run_queue("p4-manufacture", self._execute_manufacture_job)
        if manufacture_count > 0:
            processed_queues.append("p4-manufacture")

        refresh_result = None
        processed_job_count = build_count + evolution_count + manufacture_count
        if processed_job_count > 0 or scheduled_job_count > 0:
            refresh_result = self.tool_hub_service.refresh_query_projections()
        return RuntimeCycleRunResult(
            processed_job_count=processed_job_count,
            processed_queues=processed_queues,
            scheduled_job_count=scheduled_job_count,
            refreshed_projection_names=[] if refresh_result is None else refresh_result.refreshed_projection_names,
            snapshot_id=None if refresh_result is None else refresh_result.snapshot_id,
        )
    def _run_due_evolution_scan(self) -> int:
        config = self.tool_hub_service.repository.get_evolution_config()
        runtime_state = self.tool_hub_service.repository.get_runtime_state()
        if not config.enabled or not runtime_state.evolution_dirty:
            return 0

        last_scheduled = runtime_state.last_scheduled_evolution_at
        if last_scheduled is not None:
            elapsed_seconds = (datetime.now(tz=UTC) - datetime.fromisoformat(last_scheduled)).total_seconds()
            if elapsed_seconds < max(config.interval_minutes * 60, 0):
                return 0

        self.enqueue_scheduled_evolution_job()
        return 1

    def _enqueue_due_manufacture_jobs(self) -> int:
        now = datetime.now(tz=UTC)
        queued_or_released = 0
        for plan in self.tool_hub_service.repository.list_manufacture_plans():
            if plan.status not in {"manufacturing_pending", "manufacturing_in_progress"}:
                continue
            if datetime.fromisoformat(plan.estimated_ready_at) > now:
                continue
            existing = self._find_open_job(queue_name="p4-manufacture", aggregate_id=plan.item_id)
            if existing is None:
                self.runtime_repository.save_job(
                    RuntimeJob(
                        job_id=f"job-{uuid4().hex[:12]}",
                        job_type="manufacture_execution",
                        queue_name="p4-manufacture",
                        aggregate_type="tool_manufacture_plan",
                        aggregate_id=plan.item_id,
                        trigger_source="runtime_due_scan",
                        trigger_actor_id="system",
                        payload_ref=plan.item_id,
                    )
                )
                queued_or_released += 1
                continue
            if (
                existing.status == "queued"
                and existing.not_before is not None
                and datetime.fromisoformat(existing.not_before) > now
            ):
                released = existing.model_copy(
                    update={
                        "not_before": None,
                        "updated_at": now_iso(),
                    }
                )
                self.runtime_repository.save_job(released)
                queued_or_released += 1
        return queued_or_released
    def _run_queue(self, queue_name: str, executor: Callable[[RuntimeJob], None]) -> int:
        processed = 0
        while True:
            leased = self.runtime_repository.acquire_job(
                queue_name=queue_name,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            if leased is None:
                return processed
            self._execute_job(leased, executor)
            processed += 1

    def _execute_job(self, job: RuntimeJob, executor: Callable[[RuntimeJob], None]) -> None:
        started_at = job.started_at or now_iso()
        running = job.model_copy(
            update={
                "status": "running",
                "attempt_count": job.attempt_count + 1,
                "started_at": started_at,
                "updated_at": now_iso(),
            }
        )
        self.runtime_repository.save_job(running)

        try:
            executor(running)
        except Exception as exc:
            should_retry = running.attempt_count < running.max_attempts
            failed = running.model_copy(
                update={
                    "status": "queued" if should_retry else "failed",
                    "leased_by": None,
                    "leased_until": None,
                    "finished_at": None if should_retry else now_iso(),
                    "error_code": "runtime_execution_failed",
                    "error_message": str(exc),
                    "updated_at": now_iso(),
                }
            )
            self.runtime_repository.save_job(failed)
            self.runtime_repository.save_execution_record(
                job_id=running.job_id,
                attempt_number=running.attempt_count,
                worker_id=self.worker_id,
                status="failed",
                error_code="runtime_execution_failed",
                error_message=str(exc),
            )
            if not should_retry:
                raise
            return

        completed = running.model_copy(
            update={
                "status": "completed",
                "leased_by": None,
                "leased_until": None,
                "finished_at": now_iso(),
                "error_code": None,
                "error_message": None,
                "updated_at": now_iso(),
            }
        )
        self.runtime_repository.save_job(completed)
        self.runtime_repository.save_execution_record(
            job_id=running.job_id,
            attempt_number=running.attempt_count,
            worker_id=self.worker_id,
            status="completed",
        )

    def _execute_manufacture_job(self, job: RuntimeJob) -> None:
        plan = self.tool_hub_service.repository.get_manufacture_plan(job.aggregate_id)
        if plan is None:
            return
        item = self.tool_hub_service.repository.get_demand_item(plan.item_id)
        if item is None:
            return

        self.tool_hub_service._advance_manufacture_plan(plan, item)

        refreshed_plan = self.tool_hub_service.repository.get_manufacture_plan(plan.item_id)
        if refreshed_plan is None:
            return
        if refreshed_plan.status in {"manufacturing_pending", "manufacturing_in_progress"}:
            self._schedule_followup_manufacture_job(refreshed_plan, actor_id=job.trigger_actor_id)

    def _execute_build_job(self, job: RuntimeJob) -> None:
        self.tool_hub_service.delivery_service.execute_build_run(job.aggregate_id)

    def _execute_evolution_job(self, job: RuntimeJob) -> None:
        if job.job_type == "scheduled_evolution_scan":
            self.tool_hub_service.evolution_service.run_evolution(
                actor_id=job.trigger_actor_id or "system",
                trigger_type="scheduled",
            )
            return

        if job.job_type != "evolution_auto_apply":
            return

        task = self.tool_hub_service.repository.get_evolution_task(job.aggregate_id)
        if task is None or task.task_status not in {"queued", "running"}:
            return
        self.tool_hub_service._advance_evolution_task(task)

    def _schedule_followup_manufacture_job(self, plan: ToolManufacturePlan, actor_id: str) -> RuntimeJob:
        not_before = (datetime.now(tz=UTC) + timedelta(seconds=max(plan.suggested_poll_after_seconds, 5))).isoformat()
        return self.runtime_repository.save_job(
            RuntimeJob(
                job_id=f"job-{uuid4().hex[:12]}",
                job_type="manufacture_execution",
                queue_name="p4-manufacture",
                aggregate_type="tool_manufacture_plan",
                aggregate_id=plan.item_id,
                trigger_source="runtime_followup",
                trigger_actor_id=actor_id,
                payload_ref=plan.item_id,
                not_before=not_before,
            )
        )

    def _find_open_job(self, *, queue_name: str, aggregate_id: str) -> RuntimeJob | None:
        for job in self.runtime_repository.list_jobs():
            if job.queue_name != queue_name or job.aggregate_id != aggregate_id:
                continue
            if job.status in {"queued", "leased", "running"}:
                return job
        return None
