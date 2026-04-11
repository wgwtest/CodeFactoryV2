from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.audit.service import AuditService
from app.auth.service import require_role
from app.db.session import get_session
from app.governance.service import GovernanceService

router = APIRouter(prefix="/governance", tags=["governance"])


def get_governance_service(session=Depends(get_session)) -> GovernanceService:
    return GovernanceService(session)


def get_audit_service(session=Depends(get_session)) -> AuditService:
    return AuditService(session)


@router.post("/candidates/{candidate_id}/approve", status_code=204)
def approve_candidate(candidate_id: str, reviewer: str, service: GovernanceService = Depends(get_governance_service)) -> Response:
    service.approve(candidate_id, reviewer)
    return Response(status_code=204)


@router.post("/publish")
def publish_knowledge(
    version_label: str,
    publisher: str,
    role: str = Depends(require_role("publisher")),
    service: GovernanceService = Depends(get_governance_service),
    audit: AuditService = Depends(get_audit_service),
):
    version = service.publish(version_label=version_label, publisher=publisher)
    audit.record("publish_knowledge", actor=publisher, payload={"version_label": version_label, "role": role})
    return {"id": version.id, "version_label": version.version_label}
