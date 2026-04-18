from pathlib import Path

from app.tool_hub.runtime_models import RuntimeJob, RuntimeLease
from app.tool_hub.runtime_repository import RuntimeRepository


def test_runtime_repository_can_save_list_and_lease_jobs(tmp_path: Path) -> None:
    repository = RuntimeRepository(tmp_path)
    job = RuntimeJob(
        job_id="job-001",
        job_type="manufacture_execution",
        queue_name="p4-manufacture",
        aggregate_type="tool_manufacture_plan",
        aggregate_id="plan-001",
        trigger_source="internal_command",
        trigger_actor_id="p4-system",
        payload_ref="plan-001",
    )

    repository.save_job(job)
    queued = repository.list_jobs(status="queued")

    assert [item.job_id for item in queued] == ["job-001"]

    leased = repository.acquire_job(
        queue_name="p4-manufacture",
        worker_id="worker-a",
        lease_seconds=30,
    )

    assert leased is not None
    assert leased.status == "leased"
    assert leased.leased_by == "worker-a"
    assert RuntimeLease(
        job_id=leased.job_id,
        worker_id=leased.leased_by,
        leased_until=leased.leased_until,
    )


def test_runtime_repository_records_execution_attempts(tmp_path: Path) -> None:
    repository = RuntimeRepository(tmp_path)
    repository.save_execution_record(
        job_id="job-001",
        attempt_number=1,
        worker_id="worker-a",
        status="failed",
        error_code="dependency_unavailable",
        error_message="queue timeout",
    )

    records = repository.list_execution_records("job-001")

    assert len(records) == 1
    assert records[0].error_code == "dependency_unavailable"
