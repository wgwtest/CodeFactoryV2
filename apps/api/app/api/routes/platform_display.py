from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.p6.display_service import PlatformDisplayService
from app.p6.models import (
    DisplayExperimentCreateRequest,
    DisplayExperimentList,
    DisplayExperimentRecord,
    DisplayPromotionCandidateList,
    DisplayWorkbenchBootstrap,
)

router = APIRouter(prefix="/platform-display", tags=["platform-display"])


def get_platform_display_service() -> PlatformDisplayService:
    return PlatformDisplayService()


@router.get("/workbench", response_model=DisplayWorkbenchBootstrap)
def get_platform_display_workbench(service: PlatformDisplayService = Depends(get_platform_display_service)):
    return service.get_workbench()


@router.get("/experiments", response_model=DisplayExperimentList)
def list_platform_display_experiments(service: PlatformDisplayService = Depends(get_platform_display_service)):
    return service.list_experiments()


@router.post("/experiments", response_model=DisplayExperimentRecord, status_code=status.HTTP_201_CREATED)
def create_platform_display_experiment(
    request: DisplayExperimentCreateRequest,
    service: PlatformDisplayService = Depends(get_platform_display_service),
):
    return service.create_experiment(request)


@router.get("/promotion-candidates", response_model=DisplayPromotionCandidateList)
def list_platform_display_promotion_candidates(
    service: PlatformDisplayService = Depends(get_platform_display_service),
):
    return service.list_promotion_candidates()
