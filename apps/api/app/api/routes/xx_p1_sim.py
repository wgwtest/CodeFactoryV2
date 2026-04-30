from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.xx_p1_sim.models import (
    P1DomainKnowledgeArchive,
    P1DomainKnowledgeCatalog,
    P1KnowledgeProviderRegistration,
    P1SimCallLogEnvelope,
    P1SimResetResult,
)
from app.xx_p1_sim.service import XXP1SimService

router = APIRouter(prefix="/xx-p1-sim", tags=["xx-p1-sim"])


def get_xx_p1_sim_service() -> XXP1SimService:
    return XXP1SimService()


@router.post("/register", response_model=P1KnowledgeProviderRegistration)
def register_xx_p1_sim(service: XXP1SimService = Depends(get_xx_p1_sim_service)):
    return service.register()


@router.get("/domains", response_model=P1DomainKnowledgeCatalog)
def list_xx_p1_sim_domains(service: XXP1SimService = Depends(get_xx_p1_sim_service)):
    return service.list_domains()


@router.get("/domains/{domain_id}/knowledge", response_model=P1DomainKnowledgeArchive)
def get_xx_p1_sim_domain_knowledge(
    domain_id: str,
    service: XXP1SimService = Depends(get_xx_p1_sim_service),
):
    archive = service.get_knowledge_archive(domain_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="P1 domain knowledge archive not found")
    return archive


@router.post("/reset", response_model=P1SimResetResult)
def reset_xx_p1_sim(service: XXP1SimService = Depends(get_xx_p1_sim_service)):
    return service.reset()


@router.get("/logs", response_model=P1SimCallLogEnvelope)
def list_xx_p1_sim_logs(service: XXP1SimService = Depends(get_xx_p1_sim_service)):
    return service.list_logs()
