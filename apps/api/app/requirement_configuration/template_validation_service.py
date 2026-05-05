from __future__ import annotations

from app.requirement_configuration.clause_schema_service import ClauseSchemaService
from app.requirement_configuration.field_mapping_service import FieldMappingService
from app.requirement_configuration.field_schema_service import FieldSchemaService
from app.requirement_configuration.form_schema_service import FormSchemaService
from app.requirement_configuration.gap_rule_service import GapRuleService
from app.requirement_configuration.questionnaire_policy_service import QuestionnairePolicyService
from app.requirement_configuration.section_schema_service import SectionSchemaService


class TemplateValidationService:
    def __init__(self) -> None:
        self.section_schema_service = SectionSchemaService()
        self.clause_schema_service = ClauseSchemaService()
        self.form_schema_service = FormSchemaService()
        self.field_schema_service = FieldSchemaService()
        self.field_mapping_service = FieldMappingService()
        self.questionnaire_policy_service = QuestionnairePolicyService()
        self.gap_rule_service = GapRuleService()

    def validate_all(self, template_payload: dict) -> dict:
        sections = list(template_payload.get("sections", []))
        form_groups = list(template_payload.get("form_groups", []))
        field_mappings = list(template_payload.get("field_mappings", []))
        field_keys = self.field_schema_service.field_keys(form_groups)
        clause_ids = self.clause_schema_service.clause_ids(sections)
        errors = [
            *self.section_schema_service.validate(sections),
            *self.form_schema_service.validate(form_groups),
            *self.field_mapping_service.validate(field_mappings, field_keys=field_keys, clause_ids=clause_ids),
            *self.questionnaire_policy_service.validate(template_payload.get("questionnaire_policy")),
            *self.gap_rule_service.validate(template_payload.get("gap_rules"), field_keys=field_keys),
        ]
        return {"valid": not errors, "errors": errors}

