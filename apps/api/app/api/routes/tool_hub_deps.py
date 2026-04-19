from __future__ import annotations

from fastapi import Depends

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.tool_hub.service import ToolHubService


def get_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


def get_tool_hub_service(
    archive_service: ArchiveKnowledgeService = Depends(get_archive_knowledge_service),
) -> ToolHubService:
    return ToolHubService(
        root=settings.tool_hub_root,
        archive_service=archive_service,
    )
