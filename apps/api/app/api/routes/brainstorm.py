from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.brainstorm.models import BrainstormSessionCreate, BrainstormTurnCreate
from app.brainstorm.service import BrainstormService
from app.db.session import get_session


router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])


def get_brainstorm_service(session=Depends(get_session)) -> BrainstormService:
    return BrainstormService(session)


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


@router.get("/orchestrators")
def list_brainstorm_orchestrators(service: BrainstormService = Depends(get_brainstorm_service)):
    return service.list_orchestrators()


@router.get("/providers")
def list_brainstorm_providers(service: BrainstormService = Depends(get_brainstorm_service)):
    return service.list_providers()


@router.post("/sessions")
def create_brainstorm_session(
    payload: BrainstormSessionCreate,
    service: BrainstormService = Depends(get_brainstorm_service),
):
    try:
        return service.create_session(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sessions/{session_id}")
def get_brainstorm_session(session_id: str, service: BrainstormService = Depends(get_brainstorm_service)):
    session = service.get_session(session_id)
    if session is None:
        raise _not_found("Brainstorming session not found")
    return session


@router.post("/sessions/{session_id}/turns")
def create_brainstorm_turn(
    session_id: str,
    payload: BrainstormTurnCreate,
    service: BrainstormService = Depends(get_brainstorm_service),
):
    turn = service.add_turn(session_id, payload)
    if turn is None:
        raise _not_found("Brainstorming session not found")
    return turn
