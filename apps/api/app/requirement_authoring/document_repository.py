from __future__ import annotations

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringDocument, RequirementAuthoringTemplate
from app.requirement_authoring.models import default_template_payload


class RequirementAuthoringRepository:
    def __init__(self, session) -> None:
        self.session = session

    def list_templates(self) -> list[RequirementAuthoringTemplate]:
        return self.session.scalars(
            select(RequirementAuthoringTemplate).order_by(RequirementAuthoringTemplate.template_code)
        ).all()

    def get_template(self, template_id: str) -> RequirementAuthoringTemplate | None:
        return self.session.get(RequirementAuthoringTemplate, template_id)

    def add_template(self, template: RequirementAuthoringTemplate) -> RequirementAuthoringTemplate:
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def save_template(self, template: RequirementAuthoringTemplate) -> RequirementAuthoringTemplate:
        self.session.commit()
        self.session.refresh(template)
        return template

    def ensure_default_templates(self) -> None:
        existing_codes = {template.template_code for template in self.session.scalars(select(RequirementAuthoringTemplate)).all()}
        for template_code, name in [
            ("81433", "软件级需求规格说明模板"),
            ("82259", "平台级需求规格说明模板"),
        ]:
            if template_code in existing_codes:
                continue
            self.session.add(
                RequirementAuthoringTemplate(
                    id=f"tpl-{template_code}-default",
                    template_code=template_code,
                    name=name,
                    status="active",
                    payload=default_template_payload(template_code),
                )
            )
        self.session.commit()

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
