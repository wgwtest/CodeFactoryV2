from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.tool_hub_deps import get_tool_hub_service
from app.tool_hub.models import ItemProgressView, ToolDemandItem, ToolDemandSheetDetail, ToolFetchManifest
from app.tool_hub.service import ToolHubService

router = APIRouter(tags=["tool-hub-p5-query"])


@router.get("/tools/{tool_id}/fetch", response_model=ToolFetchManifest)
def get_tool_fetch_manifest(tool_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    manifest = service.get_tool_fetch_manifest(tool_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return manifest


@router.get("/demand-sheets/{sheet_id}", response_model=ToolDemandSheetDetail)
def get_demand_sheet(sheet_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    sheet = service.get_demand_sheet(sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Demand sheet not found")
    return sheet


@router.get("/demand-items/{item_id}", response_model=ToolDemandItem)
def get_demand_item(item_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    item = service.get_demand_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Demand item not found")
    return item


@router.get("/demand-items/{item_id}/progress", response_model=ItemProgressView)
def get_demand_item_progress(item_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    progress = service.get_demand_item_progress(item_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Demand item not found")
    return progress
