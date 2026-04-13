from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.archive_knowledge.coordination import ArchiveExtractionCoordinator, coordinator
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.archive_knowledge.registry import ArchiveRegistryService
from app.config import settings

router = APIRouter(prefix="/archives", tags=["archives"])


class ArchiveCreatePayload(BaseModel):
    archive_id: str
    name: str
    source_dir: str
    extract_root: str | None = None


def get_archive_registry_service() -> ArchiveRegistryService:
    return ArchiveRegistryService(
        settings.knowledge_output_root,
        default_archive_id=settings.default_archive_id,
        default_archive_name=settings.default_archive_name,
        default_source_dir=settings.default_archive_source_dir,
        default_extract_root=settings.default_archive_extract_root,
        extract_root_parent=settings.archive_extract_root,
    )


def get_archive_extraction_service() -> ArchiveExtractionService:
    return ArchiveExtractionService(settings.knowledge_output_root)


def get_archive_extraction_coordinator() -> ArchiveExtractionCoordinator:
    return coordinator


@router.get("")
def list_archives(service: ArchiveRegistryService = Depends(get_archive_registry_service)):
    return service.list_archives()


@router.get("/{archive_id}")
def get_archive_detail(archive_id: str, service: ArchiveRegistryService = Depends(get_archive_registry_service)):
    archive = service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive


@router.post("")
def create_archive(
    payload: ArchiveCreatePayload,
    service: ArchiveRegistryService = Depends(get_archive_registry_service),
):
    try:
        return service.create_archive(
            archive_id=payload.archive_id,
            name=payload.name,
            source_dir=payload.source_dir,
            extract_root=payload.extract_root,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{archive_id}/activate")
def activate_archive(archive_id: str, service: ArchiveRegistryService = Depends(get_archive_registry_service)):
    archive = service.activate_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive


@router.post("/{archive_id}/extract")
def extract_archive(
    archive_id: str,
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    extraction_service: ArchiveExtractionService = Depends(get_archive_extraction_service),
    extraction_coordinator: ArchiveExtractionCoordinator = Depends(get_archive_extraction_coordinator),
):
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not extraction_coordinator.try_start(archive_id):
        current_archive_id = extraction_coordinator.current_archive_id or "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"当前已有知识库正在抽取中：{current_archive_id}，请等待完成后再试",
        )

    registry_service.mark_extracting(archive_id)
    try:
        extraction_service.build_archive(
            archive_id,
            source_dir=Path(archive["source_dir"]),
            extract_root=Path(archive["extract_root"]),
            archive_name=archive["name"],
        )
        refreshed = registry_service.mark_extracted(archive_id)
        return refreshed
    except ValueError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        extraction_coordinator.finish(archive_id)
