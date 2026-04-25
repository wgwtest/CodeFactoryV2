from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.config import settings
from app.db.session import get_session
from app.requirements.service import RequirementSpecService
from app.software_design.models import P3OrderCreate, ReviewThreadWrite
from app.software_design.service import SoftwareDesignService

router = APIRouter(prefix="/software-design", tags=["software-design"])


def get_requirement_spec_service(session=Depends(get_session)) -> RequirementSpecService:
    return RequirementSpecService(session)


def get_software_design_service() -> SoftwareDesignService:
    return SoftwareDesignService(root=settings.software_design_root)


def _raise_http_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail.endswith("not found"):
        status_code = 404
    elif "already exists" in detail:
        status_code = 409
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=detail)


@router.get("/overview")
def get_software_design_overview(service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.get_overview()


@router.get("/reference-center")
def get_reference_center(service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.get_reference_center()


@router.get("/standards/search")
def search_standard_library(q: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    return {"items": service.search_standard_library(q)}


@router.get("/reference-assets/{asset_name}")
def get_reference_asset(asset_name: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        asset_path = service.get_reference_asset_path(asset_name)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc
    return FileResponse(asset_path, media_type="application/pdf")


@router.get("/orders")
def list_software_design_orders(service: SoftwareDesignService = Depends(get_software_design_service)):
    return service.list_orders()


@router.get("/orders/{order_id}")
def get_software_design_order_detail(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.get_order_detail(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_software_design_order(
    payload: P3OrderCreate,
    service: SoftwareDesignService = Depends(get_software_design_service),
    requirement_service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    try:
        return service.create_order(payload, requirement_service)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/approve")
def approve_software_design_order(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.approve_order(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/reject")
def reject_software_design_order(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.reject_order(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/generate-draft")
def generate_software_design_draft(
    order_id: str,
    service: SoftwareDesignService = Depends(get_software_design_service),
    requirement_service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    try:
        return service.generate_draft(order_id, requirement_service)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/review-threads", status_code=status.HTTP_201_CREATED)
def create_review_thread(
    order_id: str,
    payload: ReviewThreadWrite,
    service: SoftwareDesignService = Depends(get_software_design_service),
):
    try:
        return service.add_review_thread(order_id, payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/freeze")
def freeze_software_design(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.freeze_order(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/workorder-batch", status_code=status.HTTP_201_CREATED)
def build_workorder_batch(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.build_workorder_batch(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{order_id}/push-to-p4")
def push_workorder_batch_to_p4(order_id: str, service: SoftwareDesignService = Depends(get_software_design_service)):
    try:
        return service.push_to_p4(order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc
