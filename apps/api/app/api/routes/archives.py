from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from logging import getLogger
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.archive_knowledge.coordination import ArchiveExtractionCoordinator, coordinator
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.archive_knowledge.policy_config import (
    DEFAULT_STAGE_ORDER,
    build_policy_run_snapshot,
    normalize_archive_policy_config,
)
from app.archive_knowledge.registry import ArchiveRegistryService
from app.config import settings

router = APIRouter(prefix="/archives", tags=["archives"])
logger = getLogger(__name__)


class ArchiveCreatePayload(BaseModel):
    archive_id: str
    name: str
    source_dir: str
    extract_root: str | None = None


class ArchiveStagePolicyRulePayload(BaseModel):
    key: str
    name: str
    meaning: str
    threshold: str
    action: str


class ArchiveStagePolicyConfigPayload(BaseModel):
    stage_id: str
    label: str
    group: str
    enabled: bool = True
    ai_mode: str
    default_action: str
    objective: str
    inputs: list[str]
    ai_adaptation: str
    rules: list[ArchiveStagePolicyRulePayload]
    branches: list[str]
    outputs: list[str]
    observability: list[str]


class ArchivePolicyConfigPayload(BaseModel):
    version_label: str
    scope_label: str
    ai_autoadapt_enabled: bool = True
    stage_order: list[str] = Field(default_factory=lambda: DEFAULT_STAGE_ORDER[:])
    stages: dict[str, ArchiveStagePolicyConfigPayload]


class ArchivePolicyConfigResponse(ArchivePolicyConfigPayload):
    archive_id: str
    updated_at: str | None = None


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


def _raise_busy_archive_conflict(extraction_coordinator: ArchiveExtractionCoordinator) -> None:
    current_archive_id = extraction_coordinator.current_archive_id or "unknown"
    raise HTTPException(
        status_code=409,
        detail=f"当前已有知识库正在抽取中：{current_archive_id}，请等待完成后再试。",
    )


def _seed_extract_build_state(
    *,
    output_root: Path,
    archive_id: str,
    archive_name: str,
    policy_snapshot: dict,
) -> None:
    DocumentArtifactRepository(output_root).save_build_state(
        archive_id,
        {
            "archive_id": archive_id,
            "archive_name": archive_name,
            "mode": "formal",
            "status": "running",
            "started_at": policy_snapshot.get("captured_at"),
            "expected_document_count": 0,
            "completed_document_ids": [],
            "skipped_document_ids": [],
            "pending_document_ids": [],
            "failed_document_id": None,
            "failed_message": None,
            "current_document_id": None,
            "current_document_title": None,
            "current_document_path": None,
            "current_chunk": None,
            "policy_snapshot": policy_snapshot,
            "warning_count": 0,
            "warnings": [],
            "documents": [],
        },
    )


def _run_archive_extract(
    *,
    archive_id: str,
    archive: dict,
    policy_snapshot: dict | None,
    registry_service: ArchiveRegistryService,
    extraction_service: ArchiveExtractionService,
    extraction_coordinator: ArchiveExtractionCoordinator,
) -> None:
    try:
        extraction_service.build_archive(
            archive_id,
            source_dir=Path(archive["source_dir"]),
            extract_root=Path(archive["extract_root"]),
            archive_name=archive["name"],
            policy_snapshot=policy_snapshot,
        )
        registry_service.mark_extracted(archive_id)
    except (ValueError, FileNotFoundError) as exc:
        registry_service.mark_error(archive_id, message=str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        registry_service.mark_error(archive_id, message=str(exc))
        logger.exception("Archive extraction failed for %s", archive_id)
    finally:
        extraction_coordinator.finish(archive_id)


@router.get("")
def list_archives(service: ArchiveRegistryService = Depends(get_archive_registry_service)):
    return service.list_archives()


@router.get("/{archive_id}")
def get_archive_detail(archive_id: str, service: ArchiveRegistryService = Depends(get_archive_registry_service)):
    archive = service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive


@router.get("/{archive_id}/policy-config", response_model=ArchivePolicyConfigResponse)
def get_archive_policy_config(
    archive_id: str,
    service: ArchiveRegistryService = Depends(get_archive_registry_service),
):
    config = service.get_policy_config(archive_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return config


@router.put("/{archive_id}/policy-config", response_model=ArchivePolicyConfigResponse)
def update_archive_policy_config(
    archive_id: str,
    payload: ArchivePolicyConfigPayload,
    service: ArchiveRegistryService = Depends(get_archive_registry_service),
):
    config = service.update_policy_config(archive_id, normalize_archive_policy_config(archive_id, payload.model_dump()))
    if config is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return config


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
    background_tasks: BackgroundTasks,
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    extraction_service: ArchiveExtractionService = Depends(get_archive_extraction_service),
    extraction_coordinator: ArchiveExtractionCoordinator = Depends(get_archive_extraction_coordinator),
):
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not extraction_coordinator.try_start(archive_id):
        _raise_busy_archive_conflict(extraction_coordinator)

    policy_snapshot = build_policy_run_snapshot(
        archive_id,
        registry_service.get_policy_config(archive_id),
        captured_at=datetime.now(UTC).isoformat(),
    )
    _seed_extract_build_state(
        output_root=extraction_service.output_root,
        archive_id=archive_id,
        archive_name=archive["name"],
        policy_snapshot=policy_snapshot,
    )
    refreshed = registry_service.mark_extracting(archive_id)
    if refreshed is None:
        extraction_coordinator.finish(archive_id)
        raise HTTPException(status_code=404, detail="Archive not found")

    background_tasks.add_task(
        _run_archive_extract,
        archive_id=archive_id,
        archive=deepcopy(archive),
        policy_snapshot=policy_snapshot,
        registry_service=registry_service,
        extraction_service=extraction_service,
        extraction_coordinator=extraction_coordinator,
    )
    return deepcopy(refreshed)


@router.post("/{archive_id}/documents/{document_id}/formalize")
def formalize_archive_document(
    archive_id: str,
    document_id: str,
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    extraction_service: ArchiveExtractionService = Depends(get_archive_extraction_service),
    extraction_coordinator: ArchiveExtractionCoordinator = Depends(get_archive_extraction_coordinator),
):
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not extraction_coordinator.try_start(archive_id):
        _raise_busy_archive_conflict(extraction_coordinator)

    registry_service.mark_extracting(archive_id)
    try:
        result = extraction_service.formalize_document(
            archive_id,
            document_id=document_id,
            source_dir=Path(archive["source_dir"]),
            extract_root=Path(archive["extract_root"]),
            archive_name=archive["name"],
        )
        registry_service.mark_extracted(archive_id)
        return result
    except ValueError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        extraction_coordinator.finish(archive_id)


@router.post("/{archive_id}/documents/import")
async def import_archive_document(
    archive_id: str,
    file: UploadFile = File(...),
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    extraction_service: ArchiveExtractionService = Depends(get_archive_extraction_service),
    extraction_coordinator: ArchiveExtractionCoordinator = Depends(get_archive_extraction_coordinator),
):
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not extraction_coordinator.try_start(archive_id):
        _raise_busy_archive_conflict(extraction_coordinator)

    registry_service.mark_extracting(archive_id)
    try:
        result = extraction_service.import_document(
            archive_id,
            file_name=file.filename or "",
            file_bytes=await file.read(),
            source_dir=Path(archive["source_dir"]),
            extract_root=Path(archive["extract_root"]),
            archive_name=archive["name"],
        )
        registry_service.mark_extracted(archive_id)
        return result
    except ValueError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
        extraction_coordinator.finish(archive_id)


@router.post("/{archive_id}/documents/{document_id}/remove")
def remove_archive_document(
    archive_id: str,
    document_id: str,
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    extraction_service: ArchiveExtractionService = Depends(get_archive_extraction_service),
    extraction_coordinator: ArchiveExtractionCoordinator = Depends(get_archive_extraction_coordinator),
):
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    if not extraction_coordinator.try_start(archive_id):
        _raise_busy_archive_conflict(extraction_coordinator)

    registry_service.mark_extracting(archive_id)
    try:
        result = extraction_service.remove_document(
            archive_id,
            document_id=document_id,
            source_dir=Path(archive["source_dir"]),
            extract_root=Path(archive["extract_root"]),
            archive_name=archive["name"],
        )
        registry_service.mark_extracted(archive_id)
        return result
    except ValueError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        registry_service.mark_error(archive_id, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        extraction_coordinator.finish(archive_id)
