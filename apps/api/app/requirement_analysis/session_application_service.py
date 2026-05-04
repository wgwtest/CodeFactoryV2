from __future__ import annotations

from app.requirement_analysis.models import RequirementAnalysisSessionCreate, RequirementAnalysisTurnCreate
from app.requirement_analysis.session_service import RequirementAnalysisSessionService


class RequirementAnalysisApplicationService:
    """Application entry for Requirement Analysis session and turn use cases."""

    def __init__(self, session) -> None:
        self.session_service = RequirementAnalysisSessionService(session)

    def list_orchestrators(self) -> dict:
        return self.session_service.list_orchestrators()

    def list_providers(self) -> dict:
        return self.session_service.list_providers()

    def create_session(self, payload: RequirementAnalysisSessionCreate) -> dict:
        return self.session_service.create_session(payload)

    def get_session(self, session_id: str) -> dict | None:
        return self.session_service.get_session(session_id)

    def add_turn(self, session_id: str, payload: RequirementAnalysisTurnCreate) -> dict | None:
        return self.session_service.add_turn(session_id, payload)
