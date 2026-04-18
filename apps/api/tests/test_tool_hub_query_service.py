from __future__ import annotations

from pathlib import Path

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.query_service import ToolHubQueryService
from app.tool_hub.service import ToolHubService


def _write_archive(path: Path) -> None:
    path.write_text(
        """
{
  "summary": {
    "document_count": 1,
    "entity_count": 1,
    "event_count": 0,
    "process_count": 1
  },
  "documents": [
    {
      "id": "doc-1",
      "title": "NAS AV-1",
      "path": "archive/NAS AV-1.pdf",
      "file_type": "pdf",
      "source_archive": "20161116体系结构文献翻译汇总",
      "character_count": 1200
    }
  ],
  "entities": [],
  "events": [],
  "processes": [],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def _build_service(tmp_path: Path) -> ToolHubService:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")
    return ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=False,
        enable_background_executor=False,
    )


def test_query_service_builds_projection_for_overview_and_evolution(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    query_service = ToolHubQueryService(service.repository)

    overview = query_service.get_overview_projection()
    evolution = query_service.get_evolution_workspace_projection()

    assert overview.metric_total_tools >= 0
    assert overview.meta.snapshot_id == evolution.meta.snapshot_id
    assert evolution.config.config_id == "default"
