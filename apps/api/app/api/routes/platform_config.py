from __future__ import annotations

from fastapi import APIRouter, Depends

from app.p6.config_service import PlatformConfigService
from app.p6.models import PlatformDisplayBaselinePackage, PlatformLegend, PlatformRoutes

router = APIRouter(prefix="/platform-config", tags=["platform-config"])


def get_platform_config_service() -> PlatformConfigService:
    return PlatformConfigService()


@router.get("/display-baseline", response_model=PlatformDisplayBaselinePackage)
def get_platform_display_baseline(service: PlatformConfigService = Depends(get_platform_config_service)):
    return service.get_display_baseline()


@router.get("/routes", response_model=PlatformRoutes)
def get_platform_routes(service: PlatformConfigService = Depends(get_platform_config_service)):
    return service.get_routes()


@router.get("/legend", response_model=PlatformLegend)
def get_platform_legend(service: PlatformConfigService = Depends(get_platform_config_service)):
    return service.get_legend()
