from __future__ import annotations

from pydantic import BaseModel, Field

from app.tool_hub.models import now_iso


class RuntimeJob(BaseModel):
    job_id: str
    job_type: str
    queue_name: str
    aggregate_type: str
    aggregate_id: str
    trigger_source: str
    trigger_actor_id: str
    payload_ref: str
    status: str = "queued"
    attempt_count: int = 0
    max_attempts: int = 3
    priority: int = 100
    not_before: str | None = None
    leased_by: str | None = None
    leased_until: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class RuntimeExecutionRecord(BaseModel):
    record_id: str
    job_id: str
    attempt_number: int
    worker_id: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    started_at: str = Field(default_factory=now_iso)
    finished_at: str = Field(default_factory=now_iso)


class RuntimeLease(BaseModel):
    job_id: str
    worker_id: str
    leased_until: str


class RuntimeCycleRunResult(BaseModel):
    cycled_at: str = Field(default_factory=now_iso)
    processed_job_count: int = 0
    processed_queues: list[str] = Field(default_factory=list)
    scheduled_job_count: int = 0
    refreshed_projection_names: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
