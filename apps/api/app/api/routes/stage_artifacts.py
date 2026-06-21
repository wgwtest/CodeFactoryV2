from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.stage_artifacts.models import (
    StageArtifactCurrentCommand,
    StageArtifactPublishCommand,
    StageArtifactSnapshotCommand,
)
from app.stage_artifacts.service import StageArtifactService

router = APIRouter(prefix="/stage-artifacts", tags=["stage-artifacts"])


def get_stage_artifact_service(session=Depends(get_session)) -> StageArtifactService:
    return StageArtifactService(session)


def _stage_artifact_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    if "cannot be overwritten" in message or "version conflict" in message:
        return HTTPException(status_code=409, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.get("")
def list_stage_artifacts(
    owner_user_id: str | None = None,
    producer_stage: str | None = None,
    artifact_type: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    lifecycle_status: str | None = None,
    parent_artifact_id: str | None = None,
    service: StageArtifactService = Depends(get_stage_artifact_service),
):
    return service.list_artifacts(
        owner_user_id=owner_user_id,
        producer_stage=producer_stage,
        artifact_type=artifact_type,
        scope_type=scope_type,
        scope_id=scope_id,
        lifecycle_status=lifecycle_status,
        parent_artifact_id=parent_artifact_id,
    )


@router.put("/current")
def upsert_current_stage_artifact(
    payload: StageArtifactCurrentCommand,
    service: StageArtifactService = Depends(get_stage_artifact_service),
):
    try:
        return service.upsert_current_artifact(payload)
    except ValueError as exc:
        raise _stage_artifact_error(exc) from exc


@router.get("/{artifact_id}")
def get_stage_artifact(artifact_id: str, service: StageArtifactService = Depends(get_stage_artifact_service)):
    artifact = service.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="stage artifact not found")
    return artifact


@router.post("/{artifact_id}/snapshots")
def create_stage_artifact_snapshot(
    artifact_id: str,
    payload: StageArtifactSnapshotCommand,
    service: StageArtifactService = Depends(get_stage_artifact_service),
):
    try:
        return service.create_snapshot(artifact_id, payload)
    except ValueError as exc:
        raise _stage_artifact_error(exc) from exc


@router.post("/{artifact_id}/freeze")
def freeze_stage_artifact(artifact_id: str, service: StageArtifactService = Depends(get_stage_artifact_service)):
    try:
        return service.freeze_artifact(artifact_id)
    except ValueError as exc:
        raise _stage_artifact_error(exc) from exc


@router.post("/{artifact_id}/publish")
def publish_stage_artifact(
    artifact_id: str,
    payload: StageArtifactPublishCommand,
    service: StageArtifactService = Depends(get_stage_artifact_service),
):
    try:
        return service.publish_artifact(artifact_id, payload)
    except ValueError as exc:
        raise _stage_artifact_error(exc) from exc
