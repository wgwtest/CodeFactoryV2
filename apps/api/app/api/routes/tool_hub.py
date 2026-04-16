from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.tool_hub.models import (
    EvolutionRun,
    EvolutionRunReadEnvelope,
    ToolDefinition,
    ToolDefinitionWrite,
    ToolHubOverviewReadEnvelope,
    ToolListReadEnvelope,
    ToolMatchRequest,
    ToolMatchRun,
)
from app.tool_hub.service import ToolHubService

router = APIRouter(prefix="/tool-hub", tags=["tool-hub"])


def get_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


def get_tool_hub_service(
    archive_service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
) -> ToolHubService:
    return ToolHubService(
        root=settings.tool_hub_root,
        archive_service=archive_service,
    )


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


@router.post("/match-runs", status_code=status.HTTP_201_CREATED, response_model=ToolMatchRun)
def create_match_run(
    payload: ToolMatchRequest,
    service: ToolHubService = Depends(get_tool_hub_service),
):
    return service.run_match(payload)


@router.get("/evolution-runs", response_model=EvolutionRunReadEnvelope)
def list_evolution_runs(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.list_evolution_runs()


@router.post("/evolution-runs", status_code=status.HTTP_201_CREATED, response_model=EvolutionRun)
def create_evolution_run(service: ToolHubService = Depends(get_tool_hub_service)):
    return service.run_evolution()
