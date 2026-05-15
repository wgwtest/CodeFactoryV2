from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformExchangeArtifact(Base):
    __tablename__ = "platform_exchange_artifacts"

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"art-{uuid4().hex[:16]}")
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    artifact_version: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[str] = mapped_column(String(32))
    producer_stage: Mapped[str] = mapped_column(String(16), index=True)
    producer_ref_id: Mapped[str] = mapped_column(String(255), index=True)
    producer_ref_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    payload_mode: Mapped[str] = mapped_column(String(32), default="inline")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    parent_artifact_ids: Mapped[list] = mapped_column(JSON, default=list)
    source_trace: Mapped[dict] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    frozen_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    published_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PlatformExchangeConsumption(Base):
    __tablename__ = "platform_exchange_consumptions"

    consumption_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"con-{uuid4().hex[:16]}")
    artifact_id: Mapped[str] = mapped_column(String, index=True)
    consumer_stage: Mapped[str] = mapped_column(String(16), index=True)
    consumer_ref_id: Mapped[str] = mapped_column(String(255), index=True)
    consumer_ref_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    consumption_mode: Mapped[str] = mapped_column(String(32), default="snapshot")
    accepted_schema_version: Mapped[str] = mapped_column(String(32))
    result_status: Mapped[str] = mapped_column(String(32), default="accepted")
    result_message: Mapped[str | None] = mapped_column(String, nullable=True)
    consumed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
