from __future__ import annotations

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument


class RequirementAuthoringRepository:
    def __init__(self, session) -> None:
        self.session = session

    def list_documents(self) -> list[RequirementAuthoringDocument]:
        return self.session.scalars(
            select(RequirementAuthoringDocument).order_by(RequirementAuthoringDocument.updated_at.desc())
        ).all()

    def get_document(self, document_id: str) -> RequirementAuthoringDocument | None:
        return self.session.get(RequirementAuthoringDocument, document_id)

    def add_document(self, document: RequirementAuthoringDocument) -> RequirementAuthoringDocument:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def save_document(self, document: RequirementAuthoringDocument) -> RequirementAuthoringDocument:
        self.session.commit()
        self.session.refresh(document)
        return document

    def delete_document(self, document: RequirementAuthoringDocument) -> None:
        self.session.delete(document)
        self.session.commit()
