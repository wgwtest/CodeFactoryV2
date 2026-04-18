from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock, RLock
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.tool_hub.models import now_iso
from app.tool_hub.runtime_models import RuntimeExecutionRecord, RuntimeJob

ModelT = TypeVar("ModelT", bound=BaseModel)


class RuntimeRepository:
    _root_locks: dict[str, RLock] = {}
    _root_locks_guard = Lock()

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        root_key = str(self.root.resolve())
        with self._root_locks_guard:
            if root_key not in self._root_locks:
                self._root_locks[root_key] = RLock()
            self._lock = self._root_locks[root_key]
        self.runtime_dir = self.root / "runtime"
        self.jobs_dir = self.runtime_dir / "jobs"
        self.execution_records_dir = self.runtime_dir / "execution_records"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.execution_records_dir.mkdir(parents=True, exist_ok=True)

    def list_jobs(self, status: str | None = None) -> list[RuntimeJob]:
        with self._lock:
            jobs = sorted(
                self._read_models(self.jobs_dir, RuntimeJob),
                key=lambda item: (item.priority, item.created_at, item.job_id),
            )
            if status is None:
                return jobs
            return [item for item in jobs if item.status == status]

    def get_job(self, job_id: str) -> RuntimeJob | None:
        with self._lock:
            path = self.jobs_dir / f"{job_id}.json"
            if not path.exists():
                return None
            return RuntimeJob.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_job(self, job: RuntimeJob) -> RuntimeJob:
        with self._lock:
            self._write_json(self.jobs_dir / f"{job.job_id}.json", job.model_dump(mode="json"))
            return job

    def acquire_job(self, *, queue_name: str, worker_id: str, lease_seconds: int) -> RuntimeJob | None:
        with self._lock:
            now = datetime.now(tz=UTC)
            for job in self.list_jobs(status="queued"):
                if job.queue_name != queue_name:
                    continue
                if job.not_before is not None and datetime.fromisoformat(job.not_before) > now:
                    continue
                leased = job.model_copy(
                    update={
                        "status": "leased",
                        "leased_by": worker_id,
                        "leased_until": (now + timedelta(seconds=lease_seconds)).isoformat(),
                        "updated_at": now_iso(),
                    }
                )
                return self.save_job(leased)
        return None

    def save_execution_record(
        self,
        *,
        job_id: str,
        attempt_number: int,
        worker_id: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> RuntimeExecutionRecord:
        with self._lock:
            record = RuntimeExecutionRecord(
                record_id=f"rte-{uuid4().hex[:12]}",
                job_id=job_id,
                attempt_number=attempt_number,
                worker_id=worker_id,
                status=status,
                error_code=error_code,
                error_message=error_message,
            )
            self._write_json(
                self.execution_records_dir / f"{record.record_id}.json",
                record.model_dump(mode="json"),
            )
            return record

    def list_execution_records(self, job_id: str | None = None) -> list[RuntimeExecutionRecord]:
        with self._lock:
            records = sorted(
                self._read_models(self.execution_records_dir, RuntimeExecutionRecord),
                key=lambda item: (item.started_at, item.record_id),
            )
            if job_id is None:
                return records
            return [item for item in records if item.job_id == job_id]

    def _read_models(self, directory: Path, model_type: type[ModelT]) -> list[ModelT]:
        items: list[ModelT] = []
        for path in sorted(directory.glob("*.json")):
            items.append(model_type.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items

    def _write_json(self, path: Path, payload: dict) -> None:
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
