from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StageArtifactCurrentCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str | None = None
    owner_user_id: str = "default"
    producer_stage: str
    artifact_type: str
    artifact_version: str
    schema_version: str
    scope_type: str
    scope_id: str
    source_artifact_ids: list[str] = Field(default_factory=list)
    lifecycle_status: str = "working"
    payload_mode: str = "inline"
    payload: dict = Field(default_factory=dict)
    payload_ref: str | None = None
    parent_artifact_id: str | None = None
    source_trace: dict = Field(default_factory=dict)


class StageArtifactSnapshotCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str | None = None
    artifact_version: str | None = None
    schema_version: str | None = None
    lifecycle_status: str = "snapshot"
    source_trace: dict | None = None


class StageArtifactPublishCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str | None = None
    artifact_version: str | None = None
    schema_version: str | None = None
    published_by: str | None = None
