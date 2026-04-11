from __future__ import annotations

from collections.abc import Generator

from fastapi import APIRouter, Depends, Response

from app.db.session import SessionLocal
from app.governance.service import GovernanceService

router = APIRouter(prefix="/governance", tags=["governance"])


def get_governance_service() -> Generator[GovernanceService, None, None]:
    session = SessionLocal()
    try:
        yield GovernanceService(session)
    finally:
        session.close()


@router.post("/candidates/{candidate_id}/approve", status_code=204)
def approve_candidate(candidate_id: str, reviewer: str, service: GovernanceService = Depends(get_governance_service)) -> Response:
    service.approve(candidate_id, reviewer)
    return Response(status_code=204)


@router.post("/publish")
def publish_knowledge(version_label: str, publisher: str, service: GovernanceService = Depends(get_governance_service)):
    version = service.publish(version_label=version_label, publisher=publisher)
    return {"id": version.id, "version_label": version.version_label}
