from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_session
from app.requirement_authoring.models import (
    RequirementAuthoringClausePatch,
    RequirementAuthoringDocumentCreate,
    RequirementAuthoringFormPatch,
    RequirementAuthoringKnowledgeBindingWrite,
    RequirementAuthoringMessageWrite,
    RequirementAuthoringTemplateWrite,
)
from app.requirement_authoring.service import RequirementAuthoringService

router = APIRouter(prefix="/requirement-authoring", tags=["requirement-authoring"])


def get_requirement_authoring_service(session=Depends(get_session)) -> RequirementAuthoringService:
    return RequirementAuthoringService(session)


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def _bad_request(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "blocking gaps" in message:
        return HTTPException(status_code=409, detail=message)
    if "frozen" in message:
        return HTTPException(status_code=409, detail=message)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.get("/templates")
def list_requirement_authoring_templates(
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    return service.list_templates()


@router.post("/templates")
def create_requirement_authoring_template(
    payload: RequirementAuthoringTemplateWrite,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    return service.create_template(payload)


@router.put("/templates/{template_id}")
def update_requirement_authoring_template(
    template_id: str,
    payload: RequirementAuthoringTemplateWrite,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    template = service.update_template(template_id, payload)
    if template is None:
        raise _not_found("Requirement authoring template not found")
    return template


@router.post("/templates/{template_id}/activate")
def activate_requirement_authoring_template(
    template_id: str,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    template = service.activate_template(template_id)
    if template is None:
        raise _not_found("Requirement authoring template not found")
    return template


@router.get("/documents")
def list_requirement_authoring_documents(
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    return service.list_documents()


@router.post("/documents")
def create_requirement_authoring_document(
    payload: RequirementAuthoringDocumentCreate,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        return service.create_document(payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/knowledge-providers")
def list_requirement_authoring_knowledge_providers(
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    return service.list_knowledge_providers()


@router.post("/knowledge-bindings")
def bind_requirement_authoring_knowledge(
    payload: RequirementAuthoringKnowledgeBindingWrite,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    binding = service.bind_knowledge(payload.provider_id, payload.domain_id)
    if binding is None:
        raise _not_found("Requirement authoring knowledge binding source not found")
    return binding


@router.get("/documents/{document_id}")
def get_requirement_authoring_document(
    document_id: str,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    document = service.get_document(document_id)
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document


@router.post("/documents/{document_id}/messages")
def append_requirement_authoring_message(
    document_id: str,
    payload: RequirementAuthoringMessageWrite,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        document = service.append_message(document_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document


@router.patch("/documents/{document_id}/form-fields")
def patch_requirement_authoring_form_fields(
    document_id: str,
    payload: RequirementAuthoringFormPatch,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        document = service.patch_form_fields(document_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document


@router.patch("/documents/{document_id}/clauses/{clause_id}")
def patch_requirement_authoring_clause(
    document_id: str,
    clause_id: str,
    payload: RequirementAuthoringClausePatch,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        document = service.patch_clause(document_id, clause_id, payload.content)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document


@router.post("/documents/{document_id}/check")
def run_requirement_authoring_check(
    document_id: str,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        document = service.run_check(document_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document


@router.post("/documents/{document_id}/freeze")
def freeze_requirement_authoring_document(
    document_id: str,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        document = service.freeze(document_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if document is None:
        raise _not_found("Requirement authoring document not found")
    return document
