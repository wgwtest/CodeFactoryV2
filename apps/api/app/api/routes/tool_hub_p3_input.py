from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.tool_hub_deps import get_tool_hub_service
from app.tool_hub.models import (
    FrontendComponentBuildRequest,
    ToolBuildRun,
    ToolDemandSheetActionRequest,
    ToolDemandSheetCreateRequest,
    ToolDemandSheetDetail,
    ToolDemandSheetEnvelope,
)
from app.tool_hub.service import ToolHubService

router = APIRouter(tags=["tool-hub-p3-input"])


@router.post(
    "/mock-generators/blue-force-demand-sheets",
    status_code=status.HTTP_201_CREATED,
    response_model=ToolDemandSheetDetail,
)
def create_mock_blue_force_demand_sheet(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.create_mock_blue_force_demand_sheet()


@router.post(
    "/mock-generators/demand-sheets/{scenario_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=ToolDemandSheetDetail,
)
def create_mock_demand_sheet(scenario_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    try:
        return service.create_mock_demand_sheet(scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/demand-sheets", status_code=status.HTTP_201_CREATED, response_model=ToolDemandSheetDetail)
def create_demand_sheet(
    payload: ToolDemandSheetCreateRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.create_demand_sheet(payload)


@router.post(
    "/build-requests/frontend-components",
    status_code=status.HTTP_201_CREATED,
    response_model=ToolBuildRun,
)
def create_frontend_component_build_request(
    payload: FrontendComponentBuildRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.delivery_service.create_frontend_component_build_request(payload)


@router.get("/demand-sheets", response_model=ToolDemandSheetEnvelope)
def list_demand_sheets(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_demand_sheets()


@router.post("/demand-sheets/{sheet_id}/withdraw", response_model=ToolDemandSheetDetail)
def withdraw_demand_sheet(
    sheet_id: str,
    payload: ToolDemandSheetActionRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        sheet = service.withdraw_demand_sheet(sheet_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if sheet is None:
        raise HTTPException(status_code=404, detail="Demand sheet not found")
    return sheet
