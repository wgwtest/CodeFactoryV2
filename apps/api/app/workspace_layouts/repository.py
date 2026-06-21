from __future__ import annotations

from sqlalchemy import select

from app.db.models.workspace_layouts import WorkspaceLayoutRecord


class WorkspaceLayoutRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add_layout(self, layout: WorkspaceLayoutRecord) -> WorkspaceLayoutRecord:
        self.session.add(layout)
        self.session.commit()
        self.session.refresh(layout)
        return layout

    def save_layout(self, layout: WorkspaceLayoutRecord) -> WorkspaceLayoutRecord:
        self.session.commit()
        self.session.refresh(layout)
        return layout

    def delete_layout(self, layout: WorkspaceLayoutRecord) -> None:
        self.session.delete(layout)
        self.session.commit()

    def get_layout(self, layout_id: str) -> WorkspaceLayoutRecord | None:
        return self.session.get(WorkspaceLayoutRecord, layout_id)

    def list_layouts(
        self,
        *,
        owner_user_id: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        layout_kind: str | None = None,
        layout_role: str | None = None,
    ) -> list[WorkspaceLayoutRecord]:
        stmt = select(WorkspaceLayoutRecord).order_by(
            WorkspaceLayoutRecord.is_default.desc(),
            WorkspaceLayoutRecord.updated_at.desc(),
        )
        if owner_user_id is not None:
            stmt = stmt.where(WorkspaceLayoutRecord.owner_user_id == owner_user_id)
        if scope_type is not None:
            stmt = stmt.where(WorkspaceLayoutRecord.scope_type == scope_type)
        if scope_id is not None:
            stmt = stmt.where(WorkspaceLayoutRecord.scope_id == scope_id)
        if layout_kind is not None:
            stmt = stmt.where(WorkspaceLayoutRecord.layout_kind == layout_kind)
        if layout_role is not None:
            stmt = stmt.where(WorkspaceLayoutRecord.layout_role == layout_role)
        return self.session.scalars(stmt).all()

    def get_current_layout(
        self,
        *,
        owner_user_id: str,
        scope_type: str,
        scope_id: str,
        layout_kind: str,
    ) -> WorkspaceLayoutRecord | None:
        return self.session.scalar(
            select(WorkspaceLayoutRecord)
            .where(WorkspaceLayoutRecord.owner_user_id == owner_user_id)
            .where(WorkspaceLayoutRecord.scope_type == scope_type)
            .where(WorkspaceLayoutRecord.scope_id == scope_id)
            .where(WorkspaceLayoutRecord.layout_kind == layout_kind)
            .where(WorkspaceLayoutRecord.layout_role == "current_auto")
        )

    def clear_default_layouts(
        self,
        *,
        owner_user_id: str,
        scope_type: str,
        scope_id: str,
        layout_kind: str,
        except_layout_id: str | None = None,
    ) -> None:
        layouts = self.list_layouts(
            owner_user_id=owner_user_id,
            scope_type=scope_type,
            scope_id=scope_id,
            layout_kind=layout_kind,
        )
        for layout in layouts:
            if except_layout_id is not None and layout.layout_id == except_layout_id:
                continue
            layout.is_default = False
