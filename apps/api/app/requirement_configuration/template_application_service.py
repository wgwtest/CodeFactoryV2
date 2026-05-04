from __future__ import annotations

from app.db.models.requirements import RequirementAuthoringTemplate
from app.requirement_authoring.models import RequirementAuthoringTemplateWrite
from app.requirement_configuration.template_repository import RequirementTemplateRepository
from app.requirement_configuration.template_service import RequirementTemplateService


class RequirementConfigurationApplicationService:
    def __init__(self, session) -> None:
        self.repository = RequirementTemplateRepository(session)
        self.template_service = RequirementTemplateService()

    def ensure_default_templates(self) -> None:
        self.repository.ensure_default_templates()

    def list_templates(self) -> list[dict]:
        self.ensure_default_templates()
        return [self.serialize_template(template) for template in self.repository.list_templates()]

    def get_template_model(self, template_id: str) -> RequirementAuthoringTemplate | None:
        return self.repository.get_template(template_id)

    def create_template(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        template = self.template_service.create_template(payload)
        return self.serialize_template(self.repository.add_template(template))

    def update_template(self, template_id: str, payload: RequirementAuthoringTemplateWrite) -> dict | None:
        template = self.repository.get_template(template_id)
        if template is None:
            return None
        return self.serialize_template(self.repository.save_template(self.template_service.update_template(template, payload)))

    def activate_template(self, template_id: str) -> dict | None:
        template = self.repository.get_template(template_id)
        if template is None:
            return None
        return self.serialize_template(self.repository.save_template(self.template_service.activate_template(template)))

    def validate_template(self, payload: dict) -> dict:
        return self.template_service.validation_service.validate_all(payload)

    @staticmethod
    def serialize_template(template: RequirementAuthoringTemplate) -> dict:
        payload = dict(template.payload or {})
        return {
            "template_id": template.id,
            "template_code": template.template_code,
            "name": template.name,
            "status": template.status,
            "description": payload.get("description", ""),
            "sections": payload.get("sections", []),
            "form_groups": payload.get("form_groups", []),
            "field_mappings": payload.get("field_mappings", []),
            "questionnaire_policy": payload.get("questionnaire_policy", {}),
            "gap_rules": payload.get("gap_rules", {}),
            "knowledge_bindings": payload.get("knowledge_bindings", []),
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }
