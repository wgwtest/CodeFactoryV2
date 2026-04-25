from __future__ import annotations

from pathlib import Path

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.models import ToolDefinition, ToolDefinitionWrite
from app.tool_hub.projection_repository import ToolHubProjectionRepository
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


def test_query_service_persists_core_projections_and_requires_refresh_for_out_of_band_changes(
    tmp_path: Path,
) -> None:
    service = _build_service(tmp_path)
    service.refresh_query_projections()

    projection_repository = ToolHubProjectionRepository(service.root)
    stored_overview = projection_repository.get_overview_projection()
    stored_tool_list = projection_repository.get_tool_list_projection()
    stored_workspace = projection_repository.get_evolution_workspace_projection()

    assert stored_overview is not None
    assert stored_tool_list is not None
    assert stored_workspace is not None

    initial_snapshot_id = stored_overview.snapshot_id
    assert stored_tool_list.snapshot_id == initial_snapshot_id
    assert stored_workspace.snapshot_id == initial_snapshot_id
    assert stored_overview.metric_total_tools == 0

    payload = ToolDefinitionWrite.model_validate(
        {
            "name": "外部写入的航迹拼接器",
            "slug": "out-of-band-route-assembler",
            "status": "active",
            "summary": "通过仓储外部写入，模拟未触发刷新链路的工具变更",
            "problem_statement": "验证查询侧默认读取持久化投影，而不是直接扫描事实对象",
            "primary_domain_id": "navigation_planning",
            "tool_form_id": "skill",
            "runtime_platform_ids": ["agent_runtime"],
            "tags": [
                "domain:navigation_planning",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "input:manual_text",
                "output:structured_json",
            ],
            "lifecycle_stage_ids": ["solution_design"],
            "input_types": ["manual_text"],
            "output_types": ["structured_json"],
            "supported_sources": ["manual_input"],
            "usage_notes": "仅用于测试查询投影刷新。",
            "keywords": ["航迹", "拼接"],
            "verification": {
                "status": "verified",
                "last_verified_result": "projection test",
                "sample_case_ids": ["projection-sample-1"],
            },
        }
    )
    service.repository.save_tool(
        ToolDefinition(
            tool_id="tool-out-of-band-001",
            **payload.model_dump(mode="json"),
        )
    )

    stale_overview = service.query_service.get_overview_projection()
    assert stale_overview.snapshot_id == initial_snapshot_id
    assert stale_overview.metric_total_tools == 0

    refreshed = service.refresh_query_projections()
    fresh_overview = service.query_service.get_overview_projection()
    fresh_tool_list = service.query_service.get_tool_list_projection()

    assert refreshed.snapshot_id != initial_snapshot_id
    assert fresh_overview.snapshot_id == refreshed.snapshot_id
    assert fresh_tool_list.snapshot_id == refreshed.snapshot_id
    assert fresh_overview.metric_total_tools == 1
    assert len(fresh_tool_list.items) == 1
