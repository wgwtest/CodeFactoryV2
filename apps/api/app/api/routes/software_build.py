from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.software_build.models import (
    P5AssemblyAttemptCreate,
    P5DeliveryRuntimeClearResult,
    P5DeliveryOrderCreate,
    P5DesignInputSimCreate,
    P5FeedbackTaskReview,
    P5InputBindingConfirmRequest,
    P5ModuleBindingUpdate,
    P5SupplyInputSimCreate,
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


@router.get("/design-inputs")
def list_software_build_design_inputs(service: SoftwareBuildService = Depends(get_software_build_service)):
    return service.list_design_inputs()


@router.get("/supply-inputs")
def list_software_build_supply_inputs(service: SoftwareBuildService = Depends(get_software_build_service)):
    return service.list_supply_inputs()


@router.get("/orders/{delivery_order_id}")
def get_software_build_order_detail(
    delivery_order_id: str,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.get_order_detail(delivery_order_id)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/design-inputs/sim", status_code=status.HTTP_201_CREATED)
def create_simulated_design_input(
    payload: P5DesignInputSimCreate,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.create_simulated_design_input(payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/supply-inputs/sim", status_code=status.HTTP_201_CREATED)
def create_simulated_supply_input(
    payload: P5SupplyInputSimCreate,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.create_simulated_supply_input(payload)
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


@router.post("/orders/{delivery_order_id}/binding/confirm")
def confirm_software_build_binding(
    delivery_order_id: str,
    payload: P5InputBindingConfirmRequest,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.confirm_input_binding(delivery_order_id, payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/orders/{delivery_order_id}/module-bindings/{module_id}")
def update_software_build_module_binding(
    delivery_order_id: str,
    module_id: str,
    payload: P5ModuleBindingUpdate,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.update_module_binding(delivery_order_id, module_id, payload)
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


@router.post("/orders/{delivery_order_id}/attempts/{attempt_id}/feedback-tasks/{task_id}/review")
def review_software_build_feedback_task(
    delivery_order_id: str,
    attempt_id: str,
    task_id: str,
    payload: P5FeedbackTaskReview,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.review_feedback_task(delivery_order_id, attempt_id, task_id, payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc


@router.post("/testing/clear-deliveries", response_model=P5DeliveryRuntimeClearResult)
def clear_software_build_deliveries_for_testing(
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    return service.clear_delivery_runtime_for_testing()


@router.post("/workspace/bootstrap-demo", status_code=status.HTTP_201_CREATED)
def bootstrap_software_build_workspace(
    payload: P5WorkspaceBootstrapRequest,
    service: SoftwareBuildService = Depends(get_software_build_service),
):
    try:
        return service.bootstrap_demo(payload)
    except ValueError as exc:
        raise _raise_http_error(exc) from exc
