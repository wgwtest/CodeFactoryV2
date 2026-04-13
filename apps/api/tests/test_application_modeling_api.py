from importlib import import_module
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.knowledge import get_archive_knowledge_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app


def _write_archive(path: Path) -> None:
    path.write_text(
        """
{
  "summary": {
    "document_count": 2,
    "entity_count": 2,
    "event_count": 1,
    "process_count": 2
  },
  "documents": [
    {
      "id": "doc-1",
      "title": "审批流程说明",
      "path": "archive/approval-process.pdf",
      "file_type": "pdf",
      "source_archive": "20161116体系结构文献翻译汇总",
      "character_count": 1800
    },
    {
      "id": "doc-2",
      "title": "协同办理路线图",
      "path": "archive/collaboration-roadmap.docx",
      "file_type": "docx",
      "source_archive": "20161116体系结构文献翻译汇总",
      "character_count": 2200
    }
  ],
  "entities": [
    {
      "id": "entity-request",
      "name": "申请单",
      "category": "domain_concept",
      "aliases": ["办理单据"],
      "document_ids": ["doc-1", "doc-2"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "申请单是办理流程的核心业务对象。"}
      ]
    },
    {
      "id": "entity-approval-center",
      "name": "审批中心",
      "category": "system_or_service",
      "aliases": ["审批工作台"],
      "document_ids": ["doc-2"],
      "evidence": [
        {"document_id": "doc-2", "excerpt": "审批中心承载待办处理和过程追踪。"}
      ]
    }
  ],
  "events": [
    {
      "id": "event-submit",
      "name": "提交申请",
      "category": "timeline_event",
      "aliases": [],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "提交申请会触发后续审批流转。"}
      ]
    }
  ],
  "processes": [
    {
      "id": "process-approval",
      "name": "申请审批流程",
      "category": "domain_process",
      "aliases": ["审批流转"],
      "document_ids": ["doc-1", "doc-2"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "申请审批流程覆盖发起、审核、办结。"}
      ]
    },
    {
      "id": "process-collaboration",
      "name": "协同办理流程",
      "category": "domain_process",
      "aliases": ["协同处置"],
      "document_ids": ["doc-2"],
      "evidence": [
        {"document_id": "doc-2", "excerpt": "协同办理流程适用于多角色共同处理的场景。"}
      ]
    }
  ],
  "relations": [
    {"type": "describes", "from": "process-approval", "to": "entity-request"},
    {"type": "owned_by", "from": "entity-approval-center", "to": "process-approval"},
    {"type": "process_scoped_by", "from": "process-collaboration", "to": "event-submit"}
  ]
}
        """.strip(),
        encoding="utf-8",
    )


def test_create_requirement_draft_returns_business_recommendations(tmp_path: Path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    modeling_routes = import_module("app.api.routes.modeling")
    modeling_service_module = import_module("app.application_modeling.service")

    app = create_app()
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    app.dependency_overrides[modeling_routes.get_application_modeling_service] = lambda: modeling_service_module.ApplicationModelingService(
        draft_root=tmp_path / "modeling",
        archive_service=ArchiveKnowledgeService(tmp_path),
    )
    client = TestClient(app)

    response = client.post("/api/modeling/requirement-drafts", json={"archive_id": "20161116-nas"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["draft"]["status"] == "draft"
    assert payload["draft"]["current_step"] == "goal"
    assert payload["draft"]["application_name"] == ""
    assert payload["recommendations"]["goal"]
    assert payload["recommendations"]["flow"]
    assert any(item["source"] == "recommended_domain" for item in payload["recommendations"]["flow"])


def test_update_complete_and_export_requirement_draft(tmp_path: Path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    modeling_routes = import_module("app.api.routes.modeling")
    modeling_service_module = import_module("app.application_modeling.service")

    app = create_app()
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    app.dependency_overrides[modeling_routes.get_application_modeling_service] = lambda: modeling_service_module.ApplicationModelingService(
        draft_root=tmp_path / "modeling",
        archive_service=ArchiveKnowledgeService(tmp_path),
    )
    client = TestClient(app)

    create_response = client.post("/api/modeling/requirement-drafts", json={"archive_id": "20161116-nas"})
    draft_id = create_response.json()["draft"]["draft_id"]

    update_response = client.put(
        f"/api/modeling/requirement-drafts/{draft_id}",
        json={
            "current_step": "structure",
            "application_name": "审批协同应用",
            "application_goal": {
                "problem_statement": "当前审批流转慢，协同办理不透明。",
                "target_outcome": "缩短办理周期并提升过程透明度。",
                "success_criteria": ["审批时长下降", "待办处理更清晰"],
            },
            "audiences": [
                {"id": "aud-1", "name": "业务办理人员", "description": "负责发起与跟踪申请。"},
                {"id": "aud-2", "name": "审批人员", "description": "负责审核与处理待办。"},
            ],
            "roles": [
                {"id": "role-1", "name": "发起方", "audience_id": "aud-1", "responsibility_summary": "提交申请并查看进度。"},
                {"id": "role-2", "name": "审核方", "audience_id": "aud-2", "responsibility_summary": "处理审批任务。"},
            ],
            "business_flows": [
                {"id": "flow-1", "name": "申请审批流程", "scope": "core", "priority": "high", "participants": ["role-1", "role-2"]},
            ],
            "business_objects": [
                {"id": "object-1", "name": "申请单", "description": "申请办理的核心单据。"},
            ],
            "key_events": [
                {"id": "event-1", "name": "提交申请", "description": "提交后进入审批流转。"},
            ],
            "application_structure": {
                "workspaces": [{"id": "ws-1", "name": "审批工作台"}],
                "pages": [{"id": "page-1", "name": "审批处理页", "page_type": "task_form"}],
                "permission_intents": [{"role_id": "role-2", "access_scope": "pending_only"}],
            },
            "knowledge_references": [
                {"source_type": "domain", "source_id": "process-approval", "source_name": "申请审批流程"},
            ],
            "manual_additions": [
                {"target_type": "page", "name": "办理进度页"},
            ],
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["draft"]["application_name"] == "审批协同应用"
    assert updated["draft"]["current_step"] == "structure"
    assert updated["draft"]["application_structure"]["pages"][0]["name"] == "审批处理页"

    complete_response = client.post(f"/api/modeling/requirement-drafts/{draft_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["draft"]["status"] == "completed"

    export_response = client.get(f"/api/modeling/requirement-drafts/{draft_id}/export")
    assert export_response.status_code == 200
    exported = export_response.json()
    assert exported["draft_id"] == draft_id
    assert exported["model"]["application_name"] == "审批协同应用"
    assert "\"application_name\": \"审批协同应用\"" in exported["json_text"]
    assert "application_name: 审批协同应用" in exported["yaml_text"]
    assert exported["markdown"].startswith("# 应用需求模型")
    assert "## 核心流程范围" in exported["markdown"]
