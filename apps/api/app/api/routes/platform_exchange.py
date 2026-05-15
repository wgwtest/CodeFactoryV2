from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.platform_exchange.models import ConsumeArtifactCommand, PublishArtifactCommand
from app.platform_exchange.service import PlatformExchangeService

router = APIRouter(prefix="/platform-exchange", tags=["platform-exchange"])


def get_platform_exchange_service(session=Depends(get_session)) -> PlatformExchangeService:
    return PlatformExchangeService(session)


def _bad_request(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    if "conflict" in message or "revoked" in message:
        return HTTPException(status_code=409, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.get("/artifacts")
def list_artifacts(
    artifact_type: str | None = None,
    producer_stage: str | None = None,
    lifecycle_status: str | None = "published",
    service: PlatformExchangeService = Depends(get_platform_exchange_service),
):
    return service.list_artifacts(
        artifact_type=artifact_type,
        producer_stage=producer_stage,
        lifecycle_status=lifecycle_status,
    )


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, service: PlatformExchangeService = Depends(get_platform_exchange_service)):
    artifact = service.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return artifact


@router.post("/artifacts")
def publish_artifact(
    payload: PublishArtifactCommand,
    service: PlatformExchangeService = Depends(get_platform_exchange_service),
):
    try:
        return service.publish_artifact(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/artifacts/{artifact_id}/consume")
def consume_artifact(
    artifact_id: str,
    payload: ConsumeArtifactCommand,
    service: PlatformExchangeService = Depends(get_platform_exchange_service),
):
    try:
        return service.consume_artifact(artifact_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/consumptions")
def list_consumptions(
    artifact_id: str | None = None,
    service: PlatformExchangeService = Depends(get_platform_exchange_service),
):
    return service.list_consumptions(artifact_id=artifact_id)


@router.get("/monitor")
def get_monitor_snapshot(service: PlatformExchangeService = Depends(get_platform_exchange_service)):
    return service.get_monitor_snapshot()
