from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.workspace_layouts.models import (
    WorkspaceLayoutCreateCommand,
    WorkspaceLayoutCurrentCommand,
    WorkspaceLayoutUpdateCommand,
)
from app.workspace_layouts.service import WorkspaceLayoutService

router = APIRouter(prefix="/workspace-layouts", tags=["workspace-layouts"])


def get_workspace_layout_service(session=Depends(get_session)) -> WorkspaceLayoutService:
    return WorkspaceLayoutService(session)


def _layout_not_found(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("")
def list_layouts(
    scope_type: str,
    scope_id: str,
    layout_kind: str,
    owner_user_id: str | None = None,
    layout_role: str | None = None,
    service: WorkspaceLayoutService = Depends(get_workspace_layout_service),
):
    return service.list_layouts(
        owner_user_id=owner_user_id,
        scope_type=scope_type,
        scope_id=scope_id,
        layout_kind=layout_kind,
        layout_role=layout_role,
    )


@router.put("/current")
def upsert_current_layout(
    payload: WorkspaceLayoutCurrentCommand,
    service: WorkspaceLayoutService = Depends(get_workspace_layout_service),
):
    return service.upsert_current_layout(payload)


@router.get("/{layout_id}")
def get_layout(layout_id: str, service: WorkspaceLayoutService = Depends(get_workspace_layout_service)):
    layout = service.get_layout(layout_id)
    if layout is None:
        raise HTTPException(status_code=404, detail="layout not found")
    return layout


@router.post("")
def create_layout(
    payload: WorkspaceLayoutCreateCommand,
    service: WorkspaceLayoutService = Depends(get_workspace_layout_service),
):
    return service.create_layout(payload)


@router.put("/{layout_id}")
def update_layout(
    layout_id: str,
    payload: WorkspaceLayoutUpdateCommand,
    service: WorkspaceLayoutService = Depends(get_workspace_layout_service),
):
    try:
        return service.update_layout(layout_id, payload)
    except ValueError as exc:
        raise _layout_not_found(exc) from exc


@router.post("/{layout_id}/default")
def set_default_layout(layout_id: str, service: WorkspaceLayoutService = Depends(get_workspace_layout_service)):
    try:
        return service.set_default_layout(layout_id)
    except ValueError as exc:
        raise _layout_not_found(exc) from exc


@router.delete("/{layout_id}")
def delete_layout(layout_id: str, service: WorkspaceLayoutService = Depends(get_workspace_layout_service)):
    try:
        return service.delete_layout(layout_id)
    except ValueError as exc:
        raise _layout_not_found(exc) from exc
