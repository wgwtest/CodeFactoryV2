from __future__ import annotations

from sqlalchemy import select

from app.db.models.requirements import RequirementAuthoringTemplate
from app.requirement_authoring.models import default_template_payload


class RequirementTemplateRepository:
    def __init__(self, session) -> None:
        self.session = session

    def list_templates(self) -> list[RequirementAuthoringTemplate]:
        return self.session.scalars(
            select(RequirementAuthoringTemplate).order_by(RequirementAuthoringTemplate.template_code)
        ).all()

    def list_templates_by_code(self, template_code: str) -> list[RequirementAuthoringTemplate]:
        return self.session.scalars(
            select(RequirementAuthoringTemplate)
            .where(RequirementAuthoringTemplate.template_code == template_code)
            .order_by(RequirementAuthoringTemplate.updated_at.desc())
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

