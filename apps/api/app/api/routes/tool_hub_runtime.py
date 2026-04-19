from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.routes.tool_hub_deps import get_tool_hub_service
from app.tool_hub.query_models import ProjectionRefreshResult
from app.tool_hub.runtime_models import RuntimeCycleRunResult
from app.tool_hub.service import ToolHubService

router = APIRouter(tags=["tool-hub-runtime"])


@router.post("/internal-runtime/projections/refresh", response_model=ProjectionRefreshResult)
def refresh_tool_hub_projections(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.refresh_query_projections()


@router.post("/internal-runtime/cycles/run-once", response_model=RuntimeCycleRunResult)
def run_tool_hub_runtime_cycle(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.run_runtime_cycle()
