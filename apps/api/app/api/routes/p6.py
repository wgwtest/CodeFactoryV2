from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.p6.models import (
    MockScenarioCatalog,
    ObservationProjectionReadEnvelope,
    PortalDataViewReadEnvelope,
    PortalProjectionReadEnvelope,
    P6SimulatorContractSubmission,
    P6SimulatorSubmissionResponse,
    SourceMode,
    StageSnapshotReadEnvelope,
)
from app.p6.service import P6ProjectionService

router = APIRouter(prefix="/p6", tags=["p6"])


def get_p6_projection_service() -> P6ProjectionService:
    return P6ProjectionService()


def _raise_p6_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotImplementedError):
        return HTTPException(status_code=501, detail=str(exc))

    detail = str(exc)
    if detail.startswith("P6 mock scenario not found:"):
        return HTTPException(status_code=404, detail=detail)
    return HTTPException(status_code=400, detail=detail)


@router.get("/mock-scenarios", response_model=MockScenarioCatalog)
def list_p6_mock_scenarios(service: P6ProjectionService = Depends(get_p6_projection_service)):
    return service.list_mock_scenarios()


@router.post("/simulator/contracts", response_model=P6SimulatorSubmissionResponse, status_code=201)
def submit_p6_simulator_contracts(
    payload: P6SimulatorContractSubmission,
    service: P6ProjectionService = Depends(get_p6_projection_service),
):
    try:
        return service.submit_simulator_contracts(payload)
    except Exception as exc:  # pragma: no cover - mapping branch is verified by API tests.
        raise _raise_p6_error(exc) from exc


@router.get("/stage-snapshots", response_model=StageSnapshotReadEnvelope)
def get_p6_stage_snapshots(
    source: SourceMode = Query(default="mock"),
    scenario: str = Query(default="baseline"),
    service: P6ProjectionService = Depends(get_p6_projection_service),
):
    try:
        return service.get_stage_snapshots(source=source, scenario=scenario)
    except Exception as exc:  # pragma: no cover - mapping branch is verified by API tests.
        raise _raise_p6_error(exc) from exc


@router.get("/portal-projection", response_model=PortalProjectionReadEnvelope)
def get_p6_portal_projection(
    source: SourceMode = Query(default="mock"),
    scenario: str = Query(default="baseline"),
    service: P6ProjectionService = Depends(get_p6_projection_service),
):
    try:
        return service.get_portal_projection(source=source, scenario=scenario)
    except Exception as exc:  # pragma: no cover - mapping branch is verified by API tests.
        raise _raise_p6_error(exc) from exc


@router.get("/portal-data", response_model=PortalDataViewReadEnvelope)
def get_p6_portal_data_view(
    source: SourceMode = Query(default="mock"),
    scenario: str = Query(default="baseline"),
    selected_stage_id: str = Query(default="P3"),
    service: P6ProjectionService = Depends(get_p6_projection_service),
):
    try:
        return service.get_portal_data_view(source=source, scenario=scenario, selected_stage_id=selected_stage_id)
    except Exception as exc:  # pragma: no cover - mapping branch is verified by API tests.
        raise _raise_p6_error(exc) from exc


@router.get("/observation-projection", response_model=ObservationProjectionReadEnvelope)
def get_p6_observation_projection(
    source: SourceMode = Query(default="mock"),
    scenario: str = Query(default="baseline"),
    service: P6ProjectionService = Depends(get_p6_projection_service),
):
    try:
        return service.get_observation_projection(source=source, scenario=scenario)
    except Exception as exc:  # pragma: no cover - mapping branch is verified by API tests.
        raise _raise_p6_error(exc) from exc
