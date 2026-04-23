from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.archive_knowledge.runtime_service import ArchiveDocumentRuntimeService
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


class ArchivePublishPayload(BaseModel):
    version_label: str
    publisher: str


def get_query_service(session=Depends(get_session)) -> QueryService:
    return QueryService(session)


def get_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


def get_archive_document_runtime_service() -> ArchiveDocumentRuntimeService:
    return ArchiveDocumentRuntimeService(settings.knowledge_output_root)


def parse_document_ids(document_ids: str | None) -> list[str] | None:
    if document_ids is None:
        return None
    values = [value.strip() for value in document_ids.split(",") if value.strip()]
    return values or None


def _encode_sse_event(
    event: str,
    data: object,
    *,
    event_id: str | None = None,
    retry_ms: int | None = None,
) -> str:
    lines: list[str] = []
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


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
def get_archive_summary(
    archive_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_summary(archive_id, parse_document_ids(document_ids))


@router.get("/archive/{archive_id}/graph")
def get_archive_graph(
    archive_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_graph(archive_id, parse_document_ids(document_ids))


@router.get("/archive/{archive_id}/processes")
def get_archive_processes(
    archive_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_processes(archive_id, parse_document_ids(document_ids))


@router.get("/archive/{archive_id}/entities")
def get_archive_entities(
    archive_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_entities(archive_id, parse_document_ids(document_ids))


@router.get("/archive/{archive_id}/events")
def get_archive_events(
    archive_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_events(archive_id, parse_document_ids(document_ids))


@router.get("/archive/{archive_id}/items/{item_id}")
def get_archive_item_detail(
    archive_id: str,
    item_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.get_item_detail(archive_id, item_id, parse_document_ids(document_ids))
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail


@router.get("/archive/{archive_id}/items/{item_id}/graph")
def get_archive_item_graph(
    archive_id: str,
    item_id: str,
    document_ids: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    detail = service.get_item_graph(archive_id, item_id, parse_document_ids(document_ids))
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


@router.get("/archive/{archive_id}/documents/{document_id}/runtime")
def get_archive_document_runtime(
    archive_id: str,
    document_id: str,
    service: ArchiveDocumentRuntimeService = Depends(get_archive_document_runtime_service),
):
    runtime = service.get_document_runtime(archive_id, document_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail="Archive document runtime not found")
    return runtime


@router.get("/archive/{archive_id}/documents/{document_id}/runtime/stream")
async def stream_archive_document_runtime(
    archive_id: str,
    document_id: str,
    request: Request,
    interval_ms: int = Query(default=2000, ge=250, le=30000),
    heartbeat_ms: int = Query(default=15000, ge=1000, le=60000),
    max_events: int | None = Query(default=None, ge=1, le=1000),
    service: ArchiveDocumentRuntimeService = Depends(get_archive_document_runtime_service),
):
    initial_runtime = await asyncio.to_thread(service.get_document_runtime, archive_id, document_id)
    if initial_runtime is None:
        raise HTTPException(status_code=404, detail="Archive document runtime not found")

    async def event_stream():
        loop = asyncio.get_running_loop()
        previous_payload = json.dumps(initial_runtime, ensure_ascii=False, separators=(",", ":"))
        last_emit_at = loop.time()
        sequence = 0
        emitted_events = 0

        yield _encode_sse_event(
            "runtime",
            initial_runtime,
            event_id=f"{document_id}:{sequence}",
            retry_ms=interval_ms,
        )
        emitted_events += 1
        if max_events is not None and emitted_events >= max_events:
            return

        while not await request.is_disconnected():
            await asyncio.sleep(interval_ms / 1000)

            runtime = await asyncio.to_thread(service.get_document_runtime, archive_id, document_id)
            if runtime is None:
                sequence += 1
                yield _encode_sse_event(
                    "error",
                    {"detail": "Archive document runtime not found"},
                    event_id=f"{document_id}:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                break

            payload = json.dumps(runtime, ensure_ascii=False, separators=(",", ":"))
            now = loop.time()
            should_emit_heartbeat = now - last_emit_at >= heartbeat_ms / 1000

            if payload != previous_payload:
                previous_payload = payload
                sequence += 1
                last_emit_at = now
                yield _encode_sse_event(
                    "runtime",
                    runtime,
                    event_id=f"{document_id}:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                if max_events is not None and emitted_events >= max_events:
                    return
                continue

            if should_emit_heartbeat:
                sequence += 1
                last_emit_at = now
                yield _encode_sse_event(
                    "heartbeat",
                    {
                        "archive_id": archive_id,
                        "document_id": document_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    event_id=f"{document_id}:heartbeat:{sequence}",
                    retry_ms=interval_ms,
                )
                emitted_events += 1
                if max_events is not None and emitted_events >= max_events:
                    return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.get("/archive/{archive_id}/publication")
def get_archive_publication(
    archive_id: str,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    return service.get_publication_overview(archive_id)


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


@router.post("/archive/{archive_id}/publish")
def publish_archive_knowledge(
    archive_id: str,
    payload: ArchivePublishPayload,
    service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
):
    try:
        return service.publish_snapshot(
            archive_id,
            version_label=payload.version_label,
            publisher=payload.publisher,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
