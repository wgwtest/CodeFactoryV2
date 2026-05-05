from __future__ import annotations

from app.db.models.requirements import RequirementAuthoringTemplate
from app.requirement_authoring.models import RequirementAuthoringTemplateWrite, default_template_payload
from app.requirement_configuration.template_validation_service import TemplateValidationService


class RequirementTemplateService:
    def __init__(self) -> None:
        self.validation_service = TemplateValidationService()

    def build_template_payload(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        base_payload = default_template_payload(payload.template_code)
        if payload.sections is not None:
            base_payload["sections"] = payload.sections
        if payload.form_groups is not None:
            base_payload["form_groups"] = payload.form_groups
        if payload.field_mappings is not None:
            base_payload["field_mappings"] = payload.field_mappings
        if payload.questionnaire_policy is not None:
            base_payload["questionnaire_policy"] = payload.questionnaire_policy
        if payload.gap_rules is not None:
            base_payload["gap_rules"] = payload.gap_rules
        if payload.knowledge_bindings is not None:
            base_payload["knowledge_bindings"] = payload.knowledge_bindings
        base_payload["description"] = payload.description
        base_payload["validation_result"] = self.validation_service.validate_all(base_payload)
        return base_payload

    def create_template(self, payload: RequirementAuthoringTemplateWrite) -> RequirementAuthoringTemplate:
        return RequirementAuthoringTemplate(
            template_code=payload.template_code.strip(),
            name=payload.name.strip() or payload.template_code.strip(),
            status=payload.status,
            payload=self.build_template_payload(payload),
        )

    def update_template(self, template: RequirementAuthoringTemplate, payload: RequirementAuthoringTemplateWrite) -> RequirementAuthoringTemplate:
        template.template_code = payload.template_code.strip()
        template.name = payload.name.strip() or payload.template_code.strip()
        template.status = payload.status
        template.payload = self.build_template_payload(payload)
        return template

    def activate_template(self, template: RequirementAuthoringTemplate) -> RequirementAuthoringTemplate:
        validation_result = self.validation_service.validate_all(template.payload or {})
        if not validation_result["valid"]:
            raise ValueError("template validation failed")
        template.status = "active"
        template.payload = {**dict(template.payload or {}), "validation_result": validation_result}
        return template

