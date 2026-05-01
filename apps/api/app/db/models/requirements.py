from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequirementSpec(Base):
    __tablename__ = "requirement_specs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    application_name: Mapped[str] = mapped_column(String(255))
    domain_name: Mapped[str] = mapped_column(String(255), default="")
    archive_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RequirementAuthoringTemplate(Base):
    __tablename__ = "requirement_authoring_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    template_code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RequirementAuthoringDocument(Base):
    __tablename__ = "requirement_authoring_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    template_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    layout_ratio: Mapped[str] = mapped_column(String(16), default="2:3")
    archive_ids: Mapped[list] = mapped_column(JSON, default=list)
    semantic_state: Mapped[dict] = mapped_column(JSON, default=dict)
    document: Mapped[dict] = mapped_column(JSON, default=dict)
    conversation: Mapped[list] = mapped_column(JSON, default=list)
    annotations: Mapped[list] = mapped_column(JSON, default=list)
    check_result: Mapped[dict] = mapped_column(JSON, default=dict)
    frozen_package: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class BrainstormSession(Base):
    __tablename__ = "brainstorm_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    topic: Mapped[str] = mapped_column(String(255))
    orchestrator_id: Mapped[str] = mapped_column(String(128), default="xg-brainstorming-orchestrator")
    provider_id: Mapped[str] = mapped_column(String(64), default="mock")
    model: Mapped[str] = mapped_column(String(128), default="mock-brainstorm-v1")
    template_id: Mapped[str] = mapped_column(String(128), default="81433号")
    knowledge_package_id: Mapped[str] = mapped_column(String(128), default="airspace-domain-demo")
    write_policy: Mapped[str] = mapped_column(String(64), default="patch_suggestion_only")
    status: Mapped[str] = mapped_column(String(32), default="created")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
