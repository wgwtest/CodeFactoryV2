from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.tool_hub_deps import get_tool_hub_service
from app.tool_hub.models import (
    EvolutionConfigReadEnvelope,
    EvolutionConfigUpdateRequest,
    EvolutionFinding,
    EvolutionFindingDecisionRequest,
    EvolutionInspectionConfig,
    EvolutionRun,
    EvolutionRunCreateRequest,
    EvolutionRunReadEnvelope,
    EvolutionTask,
    EvolutionTaskReadEnvelope,
    EvolutionTaskRollbackRequest,
    ToolDefinition,
    ToolDefinitionWrite,
    ToolDemandItem,
    ToolDemandReviewDecisionRequest,
    ToolDemandSheetActionRequest,
    ToolDemandSheetDetail,
    ToolDemandTestingClearResult,
    ToolHubOverviewReadEnvelope,
    ToolListReadEnvelope,
    ToolManufacturePlanEnvelope,
    ToolMatchRequest,
    ToolMatchRun,
    ToolRegistryDeleteResult,
    ToolRegistryTestingClearResult,
)
from app.tool_hub.service import ToolHubService

router = APIRouter(tags=["tool-hub-operator"])


@router.get("/overview", response_model=ToolHubOverviewReadEnvelope)
def get_tool_hub_overview(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.get_overview()


@router.get("/tools", response_model=ToolListReadEnvelope)
def list_tool_definitions(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_tools()


@router.post("/tools", status_code=status.HTTP_201_CREATED, response_model=ToolDefinition)
def create_tool_definition(
    payload: ToolDefinitionWrite,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        return service.create_tool(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tools/{tool_id}", response_model=ToolDefinition)
def get_tool_definition(tool_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    tool = service.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.put("/tools/{tool_id}", response_model=ToolDefinition)
def update_tool_definition(
    tool_id: str,
    payload: ToolDefinitionWrite,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        tool = service.update_tool(tool_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.delete("/tools/{tool_id}", response_model=ToolRegistryDeleteResult)
def delete_tool_definition(
    tool_id: str,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        result = service.delete_tool(tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return result


@router.post("/match-runs", status_code=status.HTTP_201_CREATED, response_model=ToolMatchRun)
def create_match_run(
    payload: ToolMatchRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.run_match(payload)


@router.get("/manufacture-plans", response_model=ToolManufacturePlanEnvelope)
def list_manufacture_plans(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_manufacture_plans()


@router.post("/demand-items/{item_id}/review", response_model=ToolDemandItem)
def review_demand_item(
    item_id: str,
    payload: ToolDemandReviewDecisionRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        item = service.review_demand_item(item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Demand item not found")
    return item


@router.post("/demand-sheets/{sheet_id}/reject", response_model=ToolDemandSheetDetail)
def reject_demand_sheet(
    sheet_id: str,
    payload: ToolDemandSheetActionRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        sheet = service.reject_demand_sheet(sheet_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if sheet is None:
        raise HTTPException(status_code=404, detail="Demand sheet not found")
    return sheet


@router.post("/testing/clear-demand-sheets", response_model=ToolDemandTestingClearResult)
def clear_demand_sheets_for_testing(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.clear_demand_chain_for_testing()


@router.post("/testing/clear-tools", response_model=ToolRegistryTestingClearResult)
def clear_tools_for_testing(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.clear_tool_registry_for_testing()


@router.get("/evolution/config", response_model=EvolutionConfigReadEnvelope)
def get_evolution_config(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.get_evolution_config()


@router.patch("/evolution/config", response_model=EvolutionInspectionConfig)
def update_evolution_config(
    payload: EvolutionConfigUpdateRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.update_evolution_config(payload, actor_id="p4-workspace")


@router.get("/evolution/runs", response_model=EvolutionRunReadEnvelope)
def list_evolution_runs_v2(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_evolution_runs()


@router.post("/evolution/runs", status_code=status.HTTP_201_CREATED, response_model=EvolutionRun)
def create_evolution_run_v2(
    payload: EvolutionRunCreateRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.run_evolution(actor_id=payload.actor_id, trigger_type="manual")


@router.get("/evolution/runs/{run_id}", response_model=EvolutionRun)
def get_evolution_run(run_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    run = service.get_evolution_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evolution run not found")
    return run


@router.post("/evolution/findings/{finding_id}/decision", response_model=EvolutionFinding)
def decide_evolution_finding(
    finding_id: str,
    payload: EvolutionFindingDecisionRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        finding = service.decide_evolution_finding(finding_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if finding is None:
        raise HTTPException(status_code=404, detail="Evolution finding not found")
    return finding


@router.get("/evolution/tasks", response_model=EvolutionTaskReadEnvelope)
def list_evolution_tasks(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_evolution_tasks()


@router.get("/evolution/tasks/{task_id}", response_model=EvolutionTask)
def get_evolution_task(task_id: str, service: ToolHubService = Depends(get_tool_hub_service)):
    task = service.get_evolution_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Evolution task not found")
    return task


@router.post("/evolution/tasks/{task_id}/rollback", response_model=EvolutionTask)
def rollback_evolution_task(
    task_id: str,
    payload: EvolutionTaskRollbackRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    try:
        task = service.rollback_evolution_task(task_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Evolution task not found")
    return task


@router.get("/evolution-runs", response_model=EvolutionRunReadEnvelope)
def list_evolution_runs(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_evolution_runs()


@router.post("/evolution-runs", status_code=status.HTTP_201_CREATED, response_model=EvolutionRun)
def create_evolution_run(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.run_evolution(actor_id="legacy-evolution-api", trigger_type="manual")
