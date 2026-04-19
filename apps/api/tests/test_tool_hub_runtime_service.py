from __future__ import annotations

from pathlib import Path

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.models import (
    EvolutionFindingDecisionRequest,
    FrontendComponentBuildRequest,
    ToolDefinitionWrite,
    ToolDemandReviewDecisionRequest,
)
from app.tool_hub.runtime_repository import RuntimeRepository
from app.tool_hub.runtime_service import ToolHubRuntimeService
from app.tool_hub.runtime_worker import ToolHubRuntimeWorker
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
  "entities": [
    {
      "id": "entity-nas",
      "name": "国家空域系统",
      "category": "system_or_service",
      "aliases": ["NAS"],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "NAS excerpt"}
      ]
    }
  ],
  "events": [],
  "processes": [
    {
      "id": "process-collaboration",
      "name": "协同处置流程",
      "category": "domain_process",
      "aliases": [],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Collaboration excerpt"}
      ]
    }
  ],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def _build_service(
    tmp_path: Path,
    *,
    seed_demo_data: bool = False,
    enable_background_executor: bool = False,
) -> ToolHubService:
    archive_root = tmp_path / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    _write_archive(archive_root / "20161116-nas-knowledge.json")
    return ToolHubService(
        root=tmp_path / "tool-hub",
        archive_service=ArchiveKnowledgeService(archive_root),
        seed_demo_data=seed_demo_data,
        enable_background_executor=enable_background_executor,
    )


def test_runtime_coordinator_processes_manufacture_jobs(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    detail = service.create_mock_blue_force_demand_sheet()
    target_item = next(item for item in detail.items if item.recommendation_type == "manufacture_candidate")

    service.review_demand_item(
        target_item.item_id,
        ToolDemandReviewDecisionRequest(
            decision="approve_manufacture",
            reviewed_by="tester",
            review_comment="enqueue manufacture",
            importance_score=85,
            urgency_score=70,
            rationality_verdict="approved",
        ),
    )

    runtime_repository = RuntimeRepository(service.root)
    queued_jobs = runtime_repository.list_jobs(status="queued")
    assert any(job.queue_name == "p4-manufacture" and job.aggregate_id == target_item.item_id for job in queued_jobs)

    runtime = ToolHubRuntimeService(service)
    runtime.run_once()

    progress = service.get_demand_item_progress(target_item.item_id)
    assert progress is not None
    assert progress.status in {"manufacturing_in_progress", "ready_for_fetch"}


def test_runtime_coordinator_processes_evolution_jobs(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    tool = service.create_tool(
        ToolDefinitionWrite.model_validate(
            {
                "name": "案例标签修复器",
                "slug": "case-tag-fixer",
                "status": "active",
                "summary": "修复案例工具的标签与摘要问题",
                "problem_statement": "",
                "primary_domain_id": "case_management",
                "tool_form_id": "skill",
                "runtime_platform_ids": ["agent_runtime"],
                "tags": [
                    "domain:case_management",
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
                "usage_notes": "用于演示自演进自动修复",
                "keywords": ["案例", "修复"],
                "verification": {
                    "status": "unverified",
                    "last_verified_result": "",
                    "sample_case_ids": [],
                },
            }
        )
    )
    run = service.run_evolution(actor_id="tester", trigger_type="manual")
    finding = next(item for item in run.findings if item.kind == "missing_description")

    service.decide_evolution_finding(
        finding.finding_id,
        EvolutionFindingDecisionRequest(
            actor_id="tester",
            decision="accept",
            note="enqueue auto apply",
        ),
    )

    runtime_repository = RuntimeRepository(service.root)
    queued_jobs = runtime_repository.list_jobs(status="queued")
    assert any(job.queue_name == "p4-evolution" and job.aggregate_id.startswith("evolution-task-") for job in queued_jobs)

    runtime = ToolHubRuntimeService(service)
    runtime.run_once()

    task = service.list_evolution_tasks().data.items[0]
    assert task.task_status == "completed"

    updated_tool = service.get_tool(tool.tool_id)
    assert updated_tool is not None
    assert updated_tool.problem_statement


def test_standalone_runtime_worker_can_process_jobs_from_shared_root(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    detail = service.create_mock_demand_sheet("navigation_planning")
    target_item = next(item for item in detail.items if item.recommendation_type == "manufacture_candidate")

    service.review_demand_item(
        target_item.item_id,
        ToolDemandReviewDecisionRequest(
            decision="approve_manufacture",
            reviewed_by="worker-tester",
            review_comment="enqueue manufacture for standalone worker",
            importance_score=90,
            urgency_score=80,
            rationality_verdict="approved",
        ),
    )

    runtime_repository = RuntimeRepository(service.root)
    assert any(job.aggregate_id == target_item.item_id for job in runtime_repository.list_jobs(status="queued"))

    worker = ToolHubRuntimeWorker(
        root=service.root,
        archive_service=service.archive_service,
        seed_demo_data=False,
        worker_id="p4-worker-test",
    )
    result = worker.run_once()

    assert result.processed_job_count >= 1
    progress = service.get_demand_item_progress(target_item.item_id)
    assert progress is not None
    assert progress.status in {"manufacturing_in_progress", "ready_for_fetch"}


def test_runtime_coordinator_processes_frontend_component_build_jobs(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    build_run = service.delivery_service.create_frontend_component_build_request(
        FrontendComponentBuildRequest(
            requested_by="p3-sim",
            component_name="QueryTableWidget",
            scenario_id="frontend-query-table-widget",
            tool_definition=ToolDefinitionWrite.model_validate(
                {
                    "name": "查询表格元组件",
                    "slug": "query-table-widget",
                    "status": "draft",
                    "summary": "可嵌入宿主的查询表格组件",
                    "problem_statement": "复用表格和筛选骨架",
                    "primary_domain_id": "cross_domain_shared",
                    "tool_form_id": "frontend_component",
                    "tool_granularity": "atomic",
                    "packaging_type": "source_package",
                    "integration_mode": "import_component",
                    "dependency_policy": "peer",
                    "runtime_dependencies": ["react@18", "antd@5"],
                    "runtime_platform_ids": ["web_frontend"],
                    "lifecycle_stage_ids": ["solution_design"],
                    "input_types": ["query_params", "column_schema"],
                    "output_types": ["tsx_component", "delivery_manifest"],
                    "supported_sources": ["manual_input"],
                    "tags": [],
                }
            ),
        )
    )

    runtime_repository = RuntimeRepository(service.root)
    queued_jobs = runtime_repository.list_jobs(status="queued")
    assert any(job.queue_name == "p4-build" and job.aggregate_id == build_run.build_run_id for job in queued_jobs)

    runtime = ToolHubRuntimeService(service)
    runtime.run_once()

    refreshed = service.delivery_service.get_build_run(build_run.build_run_id)
    assert refreshed is not None
    assert refreshed.status == "completed"

    manifest = service.delivery_service.get_delivery_manifest(refreshed.tool_id)
    assert manifest is not None
    assert manifest.import_specifier == "@p4-tools/query-table-widget"
