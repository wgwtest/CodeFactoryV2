from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(255))
    document_key: Mapped[str] = mapped_column(String(255), unique=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    document: Mapped[Document] = relationship(back_populates="versions")


class ParseRun(Base):
    __tablename__ = "parse_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[str] = mapped_column(String(32))
    parser_version: Mapped[str] = mapped_column(String(32), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class DocumentSegment(Base):
    __tablename__ = "document_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    parse_run_id: Mapped[str] = mapped_column(ForeignKey("parse_runs.id"))
    segment_order: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    anchor: Mapped[dict] = mapped_column(JSON, default=dict)
