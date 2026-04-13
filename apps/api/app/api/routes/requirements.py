from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.db.session import get_session
from app.requirements.schemas import RequirementSpecWrite
from app.requirements.service import RequirementSpecService

router = APIRouter(prefix="/requirements", tags=["requirements"])


def get_requirement_spec_service(session=Depends(get_session)) -> RequirementSpecService:
    return RequirementSpecService(session)


def get_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


@router.get("/formal-elements")
def list_formal_elements(
    item_type: Literal["entity", "process"] = "entity",
    archive_id: str = settings.default_archive_id,
    service: RequirementSpecService = Depends(get_requirement_spec_service),
    archive_service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.list_formal_elements(
        item_type=item_type,
        archive_id=archive_id,
        archive_service=archive_service,
    )


@router.get("/specs")
def list_requirement_specs(service: RequirementSpecService = Depends(get_requirement_spec_service)):
    return service.list_specs()


@router.post("/specs")
def create_requirement_spec(
    payload: RequirementSpecWrite,
    service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    return service.create_spec(payload)


@router.get("/specs/{spec_id}")
def get_requirement_spec(spec_id: str, service: RequirementSpecService = Depends(get_requirement_spec_service)):
    detail = service.get_spec(spec_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Requirement spec not found")
    return detail


@router.put("/specs/{spec_id}")
def update_requirement_spec(
    spec_id: str,
    payload: RequirementSpecWrite,
    service: RequirementSpecService = Depends(get_requirement_spec_service),
):
    detail = service.update_spec(spec_id, payload)
    if detail is None:
        raise HTTPException(status_code=404, detail="Requirement spec not found")
    return detail
