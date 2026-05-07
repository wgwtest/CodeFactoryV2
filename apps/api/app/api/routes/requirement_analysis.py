from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.session import get_session
from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.session_application_service import RequirementAnalysisApplicationService


router = APIRouter(prefix="/requirement-analysis", tags=["requirement-analysis"])


class RequirementAnalysisTemplateSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    name: str | None = None
    description: str | None = None


class RequirementAnalysisTemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_template_id: str
    name: str
    description: str = ""


def get_requirement_analysis_service(session=Depends(get_session)) -> RequirementAnalysisApplicationService:
    return RequirementAnalysisApplicationService(session)


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


@router.get("/lab-config")
def get_requirement_analysis_lab_config(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.get_lab_config()


@router.get("/orchestrators")
def list_requirement_analysis_orchestrators(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_orchestrators()


@router.post("/orchestrators/reload")
def reload_requirement_analysis_orchestrators(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    try:
        return service.reload_orchestrators()
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/providers")
def list_requirement_analysis_providers(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_providers()


@router.get("/templates")
def list_requirement_analysis_templates(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_templates()


@router.get("/template-bases")
def list_requirement_analysis_template_bases(
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    return service.list_base_templates()


@router.post("/templates")
def create_requirement_analysis_template(
    payload: RequirementAnalysisTemplateCreate,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    template = service.create_template(
        base_template_id=payload.base_template_id,
        name=payload.name,
        description=payload.description,
    )
    if template is None:
        raise _not_found("Requirement Analysis base template not found")
    return template


@router.get("/templates/{template_id}")
def get_requirement_analysis_template(
    template_id: str,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    template = service.get_template(template_id)
    if template is None:
        raise _not_found("Requirement Analysis template not found")
    return template


@router.put("/templates/{template_id}")
def save_requirement_analysis_template(
    template_id: str,
    payload: RequirementAnalysisTemplateSave,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    template = service.save_template(
        template_id,
        payload.content,
        name=payload.name,
        description=payload.description,
    )
    if template is None:
        raise _not_found("Requirement Analysis template not found")
    return template


@router.delete("/templates/{template_id}")
def delete_requirement_analysis_template(
    template_id: str,
    service: RequirementAnalysisApplicationService = Depends(get_requirement_analysis_service),
):
    result = service.delete_template(template_id)
    if result is None:
        raise _not_found("Requirement Analysis template not found")
    return result


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
