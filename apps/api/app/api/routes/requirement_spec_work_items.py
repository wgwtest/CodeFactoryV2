from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.requirement_spec_work_items.models import (
    RequirementSpecWorkItemConfigure,
    RequirementSpecWorkItemCreate,
    RequirementSpecWorkItemRevisionCreate,
    RequirementSpecWorkItemSaveAs,
    RequirementSpecWorkItemUpdate,
)
from app.requirement_spec_work_items.service import RequirementSpecWorkItemService


router = APIRouter(prefix="/requirement-analysis/spec-items", tags=["requirement-spec-work-items"])


def get_requirement_spec_work_item_service(session=Depends(get_session)) -> RequirementSpecWorkItemService:
    return RequirementSpecWorkItemService(session)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Requirement spec work item not found")


def _bad_request(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "blocking gaps" in message:
        return HTTPException(status_code=409, detail=message)
    if "published" in message:
        return HTTPException(status_code=409, detail=message)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.get("")
@router.get("/")
def list_requirement_spec_work_items(
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    return service.list_items()


@router.post("")
@router.post("/")
def create_requirement_spec_work_item(
    payload: RequirementSpecWorkItemCreate,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        return service.create_item(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/{spec_item_id}")
def get_requirement_spec_work_item(
    spec_item_id: str,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    item = service.get_item(spec_item_id)
    if item is None:
        raise _not_found()
    return item


@router.patch("/{spec_item_id}")
def update_requirement_spec_work_item(
    spec_item_id: str,
    payload: RequirementSpecWorkItemUpdate,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.update_item(spec_item_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.post("/{spec_item_id}/configure")
def configure_requirement_spec_work_item(
    spec_item_id: str,
    payload: RequirementSpecWorkItemConfigure,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.configure_item(spec_item_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.post("/{spec_item_id}/publish")
def publish_requirement_spec_work_item(
    spec_item_id: str,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.publish_item(spec_item_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.post("/{spec_item_id}/revision")
def create_requirement_spec_work_item_revision(
    spec_item_id: str,
    payload: RequirementSpecWorkItemRevisionCreate | None = None,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.create_revision(spec_item_id, payload or RequirementSpecWorkItemRevisionCreate())
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.post("/{spec_item_id}/save-session-artifacts")
def save_requirement_spec_work_item_session_artifacts(
    spec_item_id: str,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.save_session_artifacts(spec_item_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.post("/{spec_item_id}/save-session-artifacts-as")
def save_requirement_spec_work_item_session_artifacts_as(
    spec_item_id: str,
    payload: RequirementSpecWorkItemSaveAs,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        item = service.save_session_artifacts_as(spec_item_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if item is None:
        raise _not_found()
    return item


@router.delete("/{spec_item_id}")
def delete_requirement_spec_work_item(
    spec_item_id: str,
    service: RequirementSpecWorkItemService = Depends(get_requirement_spec_work_item_service),
):
    try:
        deleted = service.delete_item(spec_item_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if not deleted:
        raise _not_found()
    return {"deleted": True, "spec_item_id": spec_item_id}
