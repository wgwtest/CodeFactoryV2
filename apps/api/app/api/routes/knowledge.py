from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.session import get_session
from app.query.service import QueryService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_query_service(session=Depends(get_session)) -> QueryService:
    return QueryService(session)


@router.get("/graph")
def get_graph(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_graph(version_label)


@router.get("/processes")
def get_processes(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_processes(version_label)


@router.get("/search")
def search_knowledge(version_label: str, query: str, service: QueryService = Depends(get_query_service)):
    return service.search(version_label, query)
