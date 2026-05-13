from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.software_design_v2.models import P3DesignSessionCreate, P3DesignTurnWrite
from app.software_design_v2.service import SoftwareDesignV2Service

router = APIRouter(prefix="/software-design-v2", tags=["software-design-v2"])


def get_software_design_v2_service(session=Depends(get_session)) -> SoftwareDesignV2Service:
    return SoftwareDesignV2Service(session)


def _bad_request(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.get("/input-packages")
def list_input_packages(service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    return service.list_input_packages()


@router.post("/sessions")
def create_design_session(
    payload: P3DesignSessionCreate,
    service: SoftwareDesignV2Service = Depends(get_software_design_v2_service),
):
    try:
        return service.create_session(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/sessions/{session_id}")
def get_design_session(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    design_session = service.get_session(session_id)
    if design_session is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return design_session


@router.post("/sessions/{session_id}/generate")
def generate_design_session(
    session_id: str,
    service: SoftwareDesignV2Service = Depends(get_software_design_v2_service),
):
    design_session = service.generate(session_id)
    if design_session is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return design_session


@router.post("/sessions/{session_id}/turns")
def append_design_turn(
    session_id: str,
    payload: P3DesignTurnWrite,
    service: SoftwareDesignV2Service = Depends(get_software_design_v2_service),
):
    result = service.append_turn(session_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result


@router.post("/sessions/{session_id}/check")
def run_design_check(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    result = service.run_check(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result


@router.post("/sessions/{session_id}/save")
def save_design_draft(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    result = service.save_draft(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result


@router.post("/sessions/{session_id}/projection")
def generate_projection(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    result = service.generate_projection(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result


@router.post("/sessions/{session_id}/freeze")
def freeze_design_session(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    try:
        result = service.freeze(session_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result


@router.delete("/sessions/{session_id}")
def delete_design_session(session_id: str, service: SoftwareDesignV2Service = Depends(get_software_design_v2_service)):
    try:
        result = service.delete_session(session_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="P3 design session not found")
    return result
