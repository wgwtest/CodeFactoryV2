from __future__ import annotations

from sqlalchemy import select

from app.db.models.document import Document, DocumentVersion


class DocumentService:
    def __init__(self, session, storage) -> None:
        self.session = session
        self.storage = storage

    def upload(
        self,
        title: str,
        source_name: str,
        file_name: str,
        document_key: str | None,
        content: bytes,
    ):
        document = None
        if document_key:
            document = self.session.scalar(select(Document).where(Document.document_key == document_key))

        if document is None:
            document = Document(title=title, source_name=source_name, document_key=document_key or file_name)
            self.session.add(document)
            self.session.flush()

        current_versions = list(document.versions)
        stored_key = self.storage.save(content, file_name)
        version = DocumentVersion(
            document_id=document.id,
            version_number=len(current_versions) + 1,
            file_name=file_name,
            storage_key=stored_key,
            mime_type="application/octet-stream",
            status="uploaded",
        )
        self.session.add(version)
        self.session.commit()
        return document, version
