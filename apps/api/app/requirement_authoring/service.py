from __future__ import annotations

from app.requirement_authoring.document_application_service import RequirementAuthoringApplicationService
from app.requirement_authoring.models import RequirementAuthoringTemplateWrite
from app.requirement_authoring.workbench_config_service import RequirementAuthoringWorkbenchConfigService
from app.requirement_configuration.template_application_service import RequirementConfigurationApplicationService


class RequirementAuthoringService(RequirementAuthoringApplicationService):
    """Public authoring service used by the existing API route."""

    def __init__(self, session) -> None:
        super().__init__(session)
        self.template_application_service = RequirementConfigurationApplicationService(session)
        self.workbench_config_service = RequirementAuthoringWorkbenchConfigService()

    def get_workbench_config(self) -> dict:
        return self.workbench_config_service.get_config()

    def list_templates(self) -> list[dict]:
        return self.template_application_service.list_templates()

    def create_template(self, payload: RequirementAuthoringTemplateWrite) -> dict:
        return self.template_application_service.create_template(payload)

    def update_template(self, template_id: str, payload: RequirementAuthoringTemplateWrite) -> dict | None:
        return self.template_application_service.update_template(template_id, payload)

    def activate_template(self, template_id: str) -> dict | None:
        return self.template_application_service.activate_template(template_id)
