from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.session_application_service import RequirementAnalysisApplicationService


router = APIRouter(prefix="/requirement-analysis", tags=["requirement-analysis"])


def get_requirement_analysis_service(session=Depends(get_session)) -> RequirementAnalysisApplicationService:
    return RequirementAnalysisApplicationService(session)


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


@router.get("/orchestrators")
def list_requirement_analysis_orchestrators(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_orchestrators()


@router.get("/providers")
def list_requirement_analysis_providers(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_providers()


@router.post("/sessions")
def create_requirement_analysis_session(
    payload: RequirementAnalysisSessionCreate,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    try:
        return service.create_session(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sessions/{session_id}")
def get_requirement_analysis_session(
    session_id: str,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    session = service.get_session(session_id)
    if session is None:
        raise _not_found("Requirement Analysis session not found")
    return session


@router.post("/sessions/{session_id}/turns")
def create_requirement_analysis_turn(
    session_id: str,
    payload: RequirementAnalysisTurnCreate,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    turn = service.add_turn(session_id, payload)
    if turn is None:
        raise _not_found("Requirement Analysis session not found")
    return turn
