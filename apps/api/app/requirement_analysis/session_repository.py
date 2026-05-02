from __future__ import annotations

from app.db.models.requirements import RequirementAnalysisSession


class RequirementAnalysisSessionRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add(self, analysis_session: RequirementAnalysisSession) -> RequirementAnalysisSession:
        self.session.add(analysis_session)
        self.session.commit()
        self.session.refresh(analysis_session)
        return analysis_session

    def get(self, session_id: str) -> RequirementAnalysisSession | None:
        return self.session.get(RequirementAnalysisSession, session_id)

    def save(self, analysis_session: RequirementAnalysisSession) -> RequirementAnalysisSession:
        self.session.commit()
        self.session.refresh(analysis_session)
        return analysis_session
