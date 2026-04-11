from app.api.routes.documents import router as documents_router
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    return app


app = create_app()
