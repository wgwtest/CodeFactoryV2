from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StageWorkArtifactRecord(Base):
    __tablename__ = "stage_work_artifacts"

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"swa-{uuid4().hex[:16]}")
    owner_user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    producer_stage: Mapped[str] = mapped_column(String(16), index=True)
    artifact_type: Mapped[str] = mapped_column(String(128), index=True)
    artifact_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(128))
    scope_type: Mapped[str] = mapped_column(String(128), index=True)
    scope_id: Mapped[str] = mapped_column(String(255), index=True)
    source_artifact_ids: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="working", index=True)
    payload_mode: Mapped[str] = mapped_column(String(32), default="inline")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128), index=True)
    parent_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source_trace: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)
