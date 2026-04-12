from __future__ import annotations

from sqlalchemy import func, select

from app.db.models.document import Document, DocumentSegment, DocumentVersion, ParseRun


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

    def list_documents(self) -> list[dict]:
        documents = self.session.scalars(select(Document).order_by(Document.created_at.desc())).all()
        return [self._serialize_document_summary(document) for document in documents]

    def get_document_detail(self, document_id: str) -> dict | None:
        document = self.session.get(Document, document_id)
        if document is None:
            return None

        versions = sorted(document.versions, key=lambda item: item.version_number, reverse=True)
        serialized_versions = [self._serialize_version_detail(version) for version in versions]
        latest_version = serialized_versions[0] if serialized_versions else None

        return {
            "id": document.id,
            "title": document.title,
            "source_name": document.source_name,
            "document_key": document.document_key,
            "latest_version": latest_version,
            "versions": serialized_versions,
        }

    def _serialize_document_summary(self, document: Document) -> dict:
        detail = self.get_document_detail(document.id)
        if detail is None:
            raise ValueError(f"Document not found: {document.id}")

        latest_version = detail["latest_version"]
        return {
            "id": document.id,
            "title": document.title,
            "source_name": document.source_name,
            "document_key": document.document_key,
            "latest_version": latest_version,
            "version_count": len(detail["versions"]),
        }

    def _serialize_version_detail(self, version: DocumentVersion) -> dict:
        parse_runs = self.session.scalars(
            select(ParseRun)
            .where(ParseRun.document_version_id == version.id)
            .order_by(ParseRun.created_at.desc())
        ).all()

        latest_parse_run = parse_runs[0] if parse_runs else None
        preview_segments = []
        if latest_parse_run is not None:
            preview_segments = self.session.scalars(
                select(DocumentSegment)
                .where(DocumentSegment.parse_run_id == latest_parse_run.id)
                .order_by(DocumentSegment.segment_order.asc())
            ).all()

        return {
            "id": version.id,
            "version_number": version.version_number,
            "file_name": version.file_name,
            "mime_type": version.mime_type,
            "status": version.status,
            "created_at": version.created_at.isoformat(),
            "latest_parse_run": self._serialize_parse_run(latest_parse_run),
            "parse_runs": [self._serialize_parse_run(parse_run) for parse_run in parse_runs],
            "segments_preview": [
                {
                    "id": segment.id,
                    "block_type": segment.block_type,
                    "heading": segment.heading,
                    "content": segment.content,
                    "anchor": segment.anchor,
                }
                for segment in preview_segments[:10]
            ],
        }

    def _serialize_parse_run(self, parse_run: ParseRun | None) -> dict | None:
        if parse_run is None:
            return None

        segment_count = self.session.scalar(
            select(func.count()).select_from(DocumentSegment).where(DocumentSegment.parse_run_id == parse_run.id)
        )
        return {
            "id": parse_run.id,
            "status": parse_run.status,
            "parser_name": parse_run.parser_name,
            "parser_version": parse_run.parser_version,
            "failure_reason": parse_run.failure_reason,
            "segment_count": segment_count or 0,
            "created_at": parse_run.created_at.isoformat(),
        }
