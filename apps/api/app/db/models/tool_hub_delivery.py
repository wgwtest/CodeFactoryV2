from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ToolBuildRequestRecord(Base):
    __tablename__ = "tool_build_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(255), index=True)
    request_type: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(255))
    recipe_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ToolBuildRunRecord(Base):
    __tablename__ = "tool_build_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    build_request_id: Mapped[str] = mapped_column(String(255), index=True)
    tool_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    queue_name: Mapped[str] = mapped_column(String(64), default="p4-build")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ToolArtifactVersionRecord(Base):
    __tablename__ = "tool_artifact_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(255), index=True)
    build_run_id: Mapped[str] = mapped_column(String(255), index=True)
    version_label: Mapped[str] = mapped_column(String(64), default="v1")
    artifact_root: Mapped[str] = mapped_column(String(1024))
    manifest_path: Mapped[str] = mapped_column(String(1024))
    packaging_type: Mapped[str] = mapped_column(String(64), default="descriptor_only")
    integration_mode: Mapped[str] = mapped_column(String(64), default="manual")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ToolValidationReportRecord(Base):
    __tablename__ = "tool_validation_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    build_run_id: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    overall_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
