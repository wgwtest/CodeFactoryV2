from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkspaceLayoutRecord(Base):
    __tablename__ = "workspace_layouts"

    layout_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"wsl-{uuid4().hex[:16]}")
    owner_user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    scope_type: Mapped[str] = mapped_column(String(128), index=True)
    scope_id: Mapped[str] = mapped_column(String(255), index=True)
    layout_kind: Mapped[str] = mapped_column(String(128), index=True)
    layout_role: Mapped[str] = mapped_column(String(64), default="named_snapshot", index=True)
    name: Mapped[str] = mapped_column(String(255), default="未命名布局")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_schema_version: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
