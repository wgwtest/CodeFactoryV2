from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PublishArtifactCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    artifact_version: str
    schema_version: str
    producer_stage: str
    producer_ref_id: str
    producer_ref_type: str | None = None
    payload_mode: str = "inline"
    payload: dict | None = None
    payload_ref: str | None = None
    parent_artifact_ids: list[str] = Field(default_factory=list)
    source_trace: dict = Field(default_factory=dict)
    frozen_at: str | None = None
    published_by: str | None = None


class ConsumeArtifactCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consumer_stage: str
    consumer_ref_id: str
    consumer_ref_type: str | None = None
    consumption_mode: str = "snapshot"
    accepted_schema_version: str
    result_status: str = "accepted"
    result_message: str | None = None


class ArtifactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    artifact_type: str
    artifact_version: str
    schema_version: str
    producer_stage: str
    producer_ref_id: str
    producer_ref_type: str | None = None
    lifecycle_status: str
    payload_mode: str
    payload: dict | None = None
    payload_ref: str | None = None
    payload_hash: str
    parent_artifact_ids: list[str] = Field(default_factory=list)
    source_trace: dict = Field(default_factory=dict)
    idempotency_key: str
    frozen_at: str | None = None
    published_at: str
    published_by: str | None = None
    created_at: str


class ArtifactEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ArtifactSummary]


class ConsumptionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consumption_id: str
    artifact_id: str
    consumer_stage: str
    consumer_ref_id: str
    consumer_ref_type: str | None = None
    consumption_mode: str
    accepted_schema_version: str
    result_status: str
    result_message: str | None = None
    consumed_at: str


class ConsumptionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConsumptionSummary]
