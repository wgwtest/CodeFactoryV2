from __future__ import annotations

from collections.abc import Generator

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.config import settings
from app.db.session import SessionLocal
from app.documents.service import DocumentService
from app.documents.storage import LocalStorage

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> Generator[DocumentService, None, None]:
    session = SessionLocal()
    try:
        yield DocumentService(session, LocalStorage(settings.storage_root))
    finally:
        session.close()


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    source_name: str = Form(...),
    document_key: str | None = Form(default=None),
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    document, version = service.upload(
        title=title,
        source_name=source_name,
        document_key=document_key,
        file_name=file.filename,
        content=await file.read(),
    )
    return {
        "id": document.id,
        "title": document.title,
        "latest_version": {"id": version.id, "version_number": version.version_number},
    }
