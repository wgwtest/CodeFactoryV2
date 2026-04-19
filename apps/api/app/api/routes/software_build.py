from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.software_build.models import (
    P5AssemblyAttemptCreate,
    P5DeliveryOrderCreate,
    P5WorkspaceBootstrapRequest,
)
from app.software_build.service import SoftwareBuildService

router = APIRouter(prefix="/software-build", tags=["software-build"])


def get_software_build_service() -> SoftwareBuildService:
    return SoftwareBuildService(
        root=settings.software_build_root,
        software_design_root=settings.software_design_root,
        tool_hub_root=settings.tool_hub_root,
    )


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
def get_software_build_overview(service: SoftwareBuildService = Depends(get_software_build_service)):
    return service.get_overview()


@router.get("/orders")
def list_software_build_orders(service: SoftwareBuildService = Depends(get_software_build_service)):
    return service.list_orders()


@router.get("/orders/{delivery_order_id}")
def get_software_build_order_detail(
    delivery_order_id: str,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.get_order_detail(delivery_order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_software_build_order(
    payload: P5DeliveryOrderCreate,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.create_delivery_order(payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{delivery_order_id}/attempts", status_code=status.HTTP_201_CREATED)
def create_software_build_attempt(
    delivery_order_id: str,
    payload: P5AssemblyAttemptCreate,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.create_attempt(delivery_order_id, payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/workspace/bootstrap-demo", status_code=status.HTTP_201_CREATED)
def bootstrap_software_build_workspace(
    payload: P5WorkspaceBootstrapRequest,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.bootstrap_demo(payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc
