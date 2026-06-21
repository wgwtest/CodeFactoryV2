from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceLayoutCreateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_user_id: str = "default"
    scope_type: str
    scope_id: str
    layout_kind: str
    layout_role: str = "named_snapshot"
    name: str = "未命名布局"
    is_default: bool = False
    payload_schema_version: str
    payload: dict = Field(default_factory=dict)


class WorkspaceLayoutCurrentCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_user_id: str = "default"
    scope_type: str
    scope_id: str
    layout_kind: str
    name: str = "当前布局"
    payload_schema_version: str
    payload: dict = Field(default_factory=dict)


class WorkspaceLayoutUpdateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_role: str | None = None
    name: str | None = None
    is_default: bool | None = None
    payload_schema_version: str | None = None
    payload: dict | None = None


class WorkspaceLayoutSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_id: str
    owner_user_id: str
    scope_type: str
    scope_id: str
    layout_kind: str
    layout_role: str
    name: str
    is_default: bool
    payload_schema_version: str
    payload: dict
    created_at: str
    updated_at: str
    last_used_at: str


class WorkspaceLayoutEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkspaceLayoutSummary] = Field(default_factory=list)
