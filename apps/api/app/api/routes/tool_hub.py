from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.tool_hub_deps import get_archive_knowledge_service, get_tool_hub_service
from app.api.routes.tool_hub_operator import router as operator_router
from app.api.routes.tool_hub_p3_input import router as p3_input_router
from app.api.routes.tool_hub_p5_query import router as p5_query_router
from app.api.routes.tool_hub_runtime import router as runtime_router

router = APIRouter(prefix="/tool-hub")
router.include_router(operator_router)
router.include_router(p3_input_router)
router.include_router(p5_query_router)
router.include_router(runtime_router)

__all__ = [
    "get_archive_knowledge_service",
    "get_tool_hub_service",
    "router",
]
