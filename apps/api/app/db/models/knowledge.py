from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateItem(Base):
    __tablename__ = "candidate_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    item_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    version_label: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    knowledge_version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_versions.id"))
    item_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
