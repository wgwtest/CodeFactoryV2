from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.workspace_layouts import WorkspaceLayoutRecord
from app.workspace_layouts.models import (
    WorkspaceLayoutCreateCommand,
    WorkspaceLayoutCurrentCommand,
    WorkspaceLayoutUpdateCommand,
)
from app.workspace_layouts.repository import WorkspaceLayoutRepository


class WorkspaceLayoutService:
    def __init__(self, session) -> None:
        self.session = session
        self.repository = WorkspaceLayoutRepository(session)

    def list_layouts(
        self,
        *,
        owner_user_id: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        layout_kind: str | None = None,
        layout_role: str | None = None,
    ) -> dict:
        return {
            "items": [
                self.serialize_layout(layout)
                for layout in self.repository.list_layouts(
                    owner_user_id=owner_user_id,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    layout_kind=layout_kind,
                    layout_role=layout_role,
                )
            ]
        }

    def get_layout(self, layout_id: str) -> dict | None:
        layout = self.repository.get_layout(layout_id)
        if layout is None:
            return None
        layout.last_used_at = datetime.now(UTC)
        return self.serialize_layout(self.repository.save_layout(layout))

    def create_layout(self, command: WorkspaceLayoutCreateCommand) -> dict:
        if command.is_default:
            self.repository.clear_default_layouts(
                owner_user_id=command.owner_user_id,
                scope_type=command.scope_type,
                scope_id=command.scope_id,
                layout_kind=command.layout_kind,
            )
        layout = WorkspaceLayoutRecord(
            owner_user_id=command.owner_user_id,
            scope_type=command.scope_type,
            scope_id=command.scope_id,
            layout_kind=command.layout_kind,
            layout_role=command.layout_role,
            name=command.name,
            is_default=command.is_default,
            payload_schema_version=command.payload_schema_version,
            payload=command.payload,
        )
        return self.serialize_layout(self.repository.add_layout(layout))

    def upsert_current_layout(self, command: WorkspaceLayoutCurrentCommand) -> dict:
        now = datetime.now(UTC)
        layout = self.repository.get_current_layout(
            owner_user_id=command.owner_user_id,
            scope_type=command.scope_type,
            scope_id=command.scope_id,
            layout_kind=command.layout_kind,
        )
        if layout is None:
            layout = WorkspaceLayoutRecord(
                owner_user_id=command.owner_user_id,
                scope_type=command.scope_type,
                scope_id=command.scope_id,
                layout_kind=command.layout_kind,
                layout_role="current_auto",
                name=command.name,
                is_default=False,
                payload_schema_version=command.payload_schema_version,
                payload=command.payload,
                created_at=now,
                updated_at=now,
                last_used_at=now,
            )
            return self.serialize_layout(self.repository.add_layout(layout))

        layout.name = command.name
        layout.payload_schema_version = command.payload_schema_version
        layout.payload = command.payload
        layout.updated_at = now
        layout.last_used_at = now
        return self.serialize_layout(self.repository.save_layout(layout))

    def update_layout(self, layout_id: str, command: WorkspaceLayoutUpdateCommand) -> dict:
        layout = self.repository.get_layout(layout_id)
        if layout is None:
            raise ValueError("layout not found")
        if command.is_default is True:
            self.repository.clear_default_layouts(
                owner_user_id=layout.owner_user_id,
                scope_type=layout.scope_type,
                scope_id=layout.scope_id,
                layout_kind=layout.layout_kind,
                except_layout_id=layout.layout_id,
            )
        update_data = command.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(layout, field, value)
        layout.updated_at = datetime.now(UTC)
        return self.serialize_layout(self.repository.save_layout(layout))

    def set_default_layout(self, layout_id: str) -> dict:
        layout = self.repository.get_layout(layout_id)
        if layout is None:
            raise ValueError("layout not found")
        self.repository.clear_default_layouts(
            owner_user_id=layout.owner_user_id,
            scope_type=layout.scope_type,
            scope_id=layout.scope_id,
            layout_kind=layout.layout_kind,
            except_layout_id=layout.layout_id,
        )
        layout.is_default = True
        layout.updated_at = datetime.now(UTC)
        return self.serialize_layout(self.repository.save_layout(layout))

    def delete_layout(self, layout_id: str) -> dict:
        layout = self.repository.get_layout(layout_id)
        if layout is None:
            raise ValueError("layout not found")
        self.repository.delete_layout(layout)
        return {"deleted_layout_id": layout_id}

    @staticmethod
    def serialize_layout(layout: WorkspaceLayoutRecord) -> dict:
        return {
            "layout_id": layout.layout_id,
            "owner_user_id": layout.owner_user_id,
            "scope_type": layout.scope_type,
            "scope_id": layout.scope_id,
            "layout_kind": layout.layout_kind,
            "layout_role": layout.layout_role,
            "name": layout.name,
            "is_default": layout.is_default,
            "payload_schema_version": layout.payload_schema_version,
            "payload": layout.payload or {},
            "created_at": layout.created_at.isoformat(),
            "updated_at": layout.updated_at.isoformat(),
            "last_used_at": layout.last_used_at.isoformat(),
        }
