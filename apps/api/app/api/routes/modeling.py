from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.application_modeling.models import RequirementDraftCreateRequest, RequirementDraftUpdate
from app.application_modeling.service import ApplicationModelingService
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings

router = APIRouter(prefix="/modeling", tags=["modeling"])


def get_application_modeling_service() -> ApplicationModelingService:
    archive_service = ArchiveKnowledgeService(settings.knowledge_output_root)
    return ApplicationModelingService(
        draft_root=settings.application_modeling_root,
        archive_service=archive_service,
    )


@router.post("/requirement-drafts", status_code=status.HTTP_201_CREATED)
def create_requirement_draft(
    payload: RequirementDraftCreateRequest,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    return service.create_draft(payload.archive_id)


@router.get("/requirement-drafts")
def list_requirement_drafts(
    archive_id: str | None = None,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    return {"items": service.list_drafts(archive_id=archive_id)}


@router.get("/requirement-drafts/{draft_id}")
def get_requirement_draft(
    draft_id: str,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    draft = service.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Requirement draft not found")
    return draft


@router.put("/requirement-drafts/{draft_id}")
def update_requirement_draft(
    draft_id: str,
    payload: RequirementDraftUpdate,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    draft = service.save_draft(draft_id, payload)
    if draft is None:
        raise HTTPException(status_code=404, detail="Requirement draft not found")
    return draft


@router.post("/requirement-drafts/{draft_id}/complete")
def complete_requirement_draft(
    draft_id: str,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    try:
        draft = service.complete_draft(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if draft is None:
        raise HTTPException(status_code=404, detail="Requirement draft not found")
    return draft


@router.get("/requirement-drafts/{draft_id}/export")
def export_requirement_draft(
    draft_id: str,
    service: ApplicationModelingService = Depends(get_application_modeling_service),
):
    draft = service.export_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Requirement draft not found")
    return draft
