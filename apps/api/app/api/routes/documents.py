from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.db.session import get_session
from app.documents.service import DocumentService
from app.documents.storage import LocalStorage
from app.parsing.service import ParsingService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(session=Depends(get_session)) -> DocumentService:
    return DocumentService(session, LocalStorage(settings.storage_root))


def get_parsing_service(session=Depends(get_session)) -> ParsingService:
    return ParsingService(session, LocalStorage(settings.storage_root))


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    source_name: str = Form(...),
    document_key: str | None = Form(default=None),
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
    parsing_service: ParsingService = Depends(get_parsing_service),
):
    document, version = service.upload(
        title=title,
        source_name=source_name,
        document_key=document_key,
        file_name=file.filename,
        content=await file.read(),
    )
    parse_run = parsing_service.parse_document_version(version.id)
    return {
        "id": document.id,
        "title": document.title,
        "latest_version": {
            "id": version.id,
            "version_number": version.version_number,
            "status": version.status,
            "latest_parse_run": {
                "id": parse_run.id,
                "status": parse_run.status,
                "parser_name": parse_run.parser_name,
            },
        },
    }


@router.get("")
def list_documents(service: DocumentService = Depends(get_document_service)):
    return service.list_documents()


@router.get("/{document_id}")
def get_document_detail(document_id: str, service: DocumentService = Depends(get_document_service)):
    detail = service.get_document_detail(document_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return detail
