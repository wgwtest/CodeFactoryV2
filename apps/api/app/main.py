from app.api.routes.archives import router as archives_router
from app.api.routes.documents import router as documents_router
from app.api.routes.governance import router as governance_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.modeling import router as modeling_router
from app.api.routes.requirements import router as requirements_router
from app.api.routes.software_design import router as software_design_router
from app.api.routes.tool_hub import router as tool_hub_router
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import settings
from app.db.base import Base
from app.db.session import engine


def create_app() -> FastAPI:
    Base.metadata.create_all(engine)
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(archives_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(governance_router, prefix=settings.api_prefix)
    app.include_router(knowledge_router, prefix=settings.api_prefix)
    app.include_router(modeling_router, prefix=settings.api_prefix)
    app.include_router(requirements_router, prefix=settings.api_prefix)
    app.include_router(tool_hub_router, prefix=settings.api_prefix)
    app.include_router(software_design_router, prefix=settings.api_prefix)
    return app


app = create_app()
