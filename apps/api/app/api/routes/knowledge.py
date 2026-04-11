from __future__ import annotations

from collections.abc import Generator

from fastapi import APIRouter, Depends

from app.db.session import SessionLocal
from app.query.service import QueryService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_query_service() -> Generator[QueryService, None, None]:
    session = SessionLocal()
    try:
        yield QueryService(session)
    finally:
        session.close()


@router.get("/graph")
def get_graph(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_graph(version_label)


@router.get("/processes")
def get_processes(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_processes(version_label)
