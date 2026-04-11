from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.db.session import get_session
from app.query.service import QueryService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ArchiveItemUpdatePayload(BaseModel):
    name: str
    category: str
    aliases: list[str] = Field(default_factory=list)


class ArchiveItemReviewPayload(BaseModel):
    review_status: Literal["pending", "approved", "rejected"]


class ArchiveBatchApprovePayload(BaseModel):
    item_ids: list[str] = Field(default_factory=list)


class ArchiveMergePayload(BaseModel):
    primary_item_id: str
    secondary_item_id: str


def get_query_service(session=Depends(get_session)) -> QueryService:
    return QueryService(session)


def get_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


@router.get("/graph")
def get_graph(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_graph(version_label)


@router.get("/processes")
def get_processes(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_processes(version_label)


@router.get("/search")
def search_knowledge(version_label: str, query: str, service: QueryService = Depends(get_query_service)):
    return service.search(version_label, query)


@router.get("/archive/{archive_id}/summary")
def get_archive_summary(archive_id: str, service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service)):
    return service.get_summary(archive_id)


@router.get("/archive/{archive_id}/graph")
def get_archive_graph(archive_id: str, service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service)):
    return service.get_graph(archive_id)


@router.get("/archive/{archive_id}/processes")
def get_archive_processes(archive_id: str, service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service)):
    return service.get_processes(archive_id)


@router.get("/archive/{archive_id}/entities")
def get_archive_entities(archive_id: str, service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service)):
    return service.get_entities(archive_id)


@router.get("/archive/{archive_id}/items/{item_id}")
def get_archive_item_detail(
    archive_id: str,
    item_id: str,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.get_item_detail(archive_id, item_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail


@router.get("/archive/{archive_id}/documents")
def get_archive_documents(archive_id: str, service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service)):
    return service.get_documents(archive_id)


@router.get("/archive/{archive_id}/documents/{document_id}")
def get_archive_document_detail(
    archive_id: str,
    document_id: str,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.get_document_detail(archive_id, document_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive document not found")
    return detail


@router.get("/archive/{archive_id}/review-candidates")
def get_archive_review_candidates(
    archive_id: str,
    query: str | None = None,
    item_type: str | None = None,
    review_status: str | None = None,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_review_candidates(
        archive_id,
        query=query,
        item_type=item_type,
        review_status=review_status,
    )


@router.get("/archive/{archive_id}/search")
def search_archive_knowledge(
    archive_id: str,
    query: str,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.search(archive_id, query)


@router.patch("/archive/{archive_id}/items/{item_id}")
def update_archive_item(
    archive_id: str,
    item_id: str,
    payload: ArchiveItemUpdatePayload,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.update_item(
        archive_id,
        item_id,
        name=payload.name,
        category=payload.category,
        aliases=payload.aliases,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail


@router.post("/archive/{archive_id}/items/{item_id}/review")
def review_archive_item(
    archive_id: str,
    item_id: str,
    payload: ArchiveItemReviewPayload,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.set_review_status(archive_id, item_id, payload.review_status)
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail


@router.post("/archive/{archive_id}/reviews/batch-approve")
def batch_approve_archive_items(
    archive_id: str,
    payload: ArchiveBatchApprovePayload,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.batch_approve(archive_id, payload.item_ids)


@router.post("/archive/{archive_id}/items/merge")
def merge_archive_items(
    archive_id: str,
    payload: ArchiveMergePayload,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    try:
        detail = service.merge_items(
            archive_id,
            primary_item_id=payload.primary_item_id,
            secondary_item_id=payload.secondary_item_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail
