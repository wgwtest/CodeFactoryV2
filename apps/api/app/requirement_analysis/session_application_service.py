from __future__ import annotations

from app.requirement_analysis.lab_config_service import RequirementAnalysisLabConfigService
from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.session_service import RequirementAnalysisSessionService
from app.requirement_analysis.template_service import RequirementAnalysisTemplateService


class RequirementAnalysisApplicationService:
    """Application entry for Requirement Analysis session and turn use cases."""

    def __init__(self, session) -> None:
        self.session_service = RequirementAnalysisSessionService(session)
        self.lab_config_service = RequirementAnalysisLabConfigService()
        self.template_service = RequirementAnalysisTemplateService()

    def get_lab_config(self) -> dict:
        return self.lab_config_service.get_config()

    def list_orchestrators(self) -> dict:
        return self.session_service.list_orchestrators()

    def list_providers(self) -> dict:
        return self.session_service.list_providers()

    def list_templates(self) -> dict:
        return self.template_service.list_templates()

    def get_template(self, template_id: str) -> dict | None:
        return self.template_service.get_template(template_id)

    def save_template(self, template_id: str, content: str) -> dict | None:
        return self.template_service.save_template(template_id, content)

    def create_session(self, payload: RequirementAnalysisSessionCreate) -> dict:
        return self.session_service.create_session(payload)

    def get_session(self, session_id: str) -> dict | None:
        return self.session_service.get_session(session_id)

    def add_turn(self, session_id: str, payload: RequirementAnalysisTurnCreate) -> dict | None:
        return self.session_service.add_turn(session_id, payload)
