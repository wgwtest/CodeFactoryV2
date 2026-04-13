from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.requirements import get_archive_knowledge_service as get_requirements_archive_knowledge_service
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app


def _write_archive(path: Path) -> None:
    path.write_text(
        """
{
  "summary": {
    "document_count": 1,
    "entity_count": 2,
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
    },
    {
      "id": "entity-controller",
      "name": "运行协调员",
      "category": "organization",
      "aliases": [],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Controller excerpt"}
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


def test_requirement_spec_crud_and_formal_elements(tmp_path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    app = create_app()
    app.dependency_overrides[get_requirements_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    formal_elements = client.get("/api/requirements/formal-elements?item_type=entity")
    assert formal_elements.status_code == 200
    assert formal_elements.json() == [
        {
            "id": "entity-nas",
            "name": "国家空域系统",
            "item_type": "entity",
            "category": "system_or_service",
            "aliases": ["NAS"],
            "document_count": 1,
            "summary": "国家空域系统 是系统/服务类实体。",
            "source_archive_id": "20161116-nas",
        },
        {
            "id": "entity-controller",
            "name": "运行协调员",
            "item_type": "entity",
            "category": "organization",
            "aliases": [],
            "document_count": 1,
            "summary": "运行协调员 是组织类实体。",
            "source_archive_id": "20161116-nas",
        },
    ]

    create_payload = {
        "archive_id": "20161116-nas",
        "status": "draft",
        "payload": {
            "application": {
                "name": "空域协同平台",
                "domain": "国家空域管理",
                "summary": "围绕核心业务对象建立协同处置应用。",
                "target_users": ["运行协调员", "体系架构师"],
            },
            "objects": [
                {
                    "id": "object-nas",
                    "name": "国家空域系统",
                    "object_kind": "business",
                    "source_kind": "formal",
                    "category": "system_or_service",
                    "aliases": ["NAS"],
                    "summary": "国家空域系统 是系统/服务类实体。",
                    "description": "核心业务对象",
                    "source_archive_id": "20161116-nas",
                    "source_item_type": "entity",
                    "source_item_id": "entity-nas",
                }
            ],
            "processes": [],
            "rules": [],
            "metrics": [],
            "non_functional_constraints": [],
        },
    }

    created = client.post("/api/requirements/specs", json=create_payload)
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["application_name"] == "空域协同平台"
    assert created_body["domain_name"] == "国家空域管理"
    assert created_body["object_count"] == 1
    assert created_body["formal_object_count"] == 1
    assert created_body["temporary_object_count"] == 0
    assert created_body["payload"]["application"]["target_users"] == ["运行协调员", "体系架构师"]

    spec_id = created_body["id"]

    listed = client.get("/api/requirements/specs")
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": spec_id,
            "application_name": "空域协同平台",
            "domain_name": "国家空域管理",
            "status": "draft",
            "archive_id": "20161116-nas",
            "object_count": 1,
            "formal_object_count": 1,
            "temporary_object_count": 0,
            "process_count": 0,
            "updated_at": created_body["updated_at"],
        }
    ]

    detail = client.get(f"/api/requirements/specs/{spec_id}")
    assert detail.status_code == 200
    assert detail.json()["payload"]["objects"][0]["source_item_id"] == "entity-nas"

    update_payload = {
        "archive_id": "20161116-nas",
        "status": "draft",
        "payload": {
            "application": {
                "name": "空域协同平台",
                "domain": "国家空域管理",
                "summary": "围绕核心业务对象建立协同处置应用。",
                "target_users": ["运行协调员", "体系架构师"],
            },
            "objects": [
                {
                    "id": "object-nas",
                    "name": "国家空域系统",
                    "object_kind": "business",
                    "source_kind": "formal",
                    "category": "system_or_service",
                    "aliases": ["NAS"],
                    "summary": "国家空域系统 是系统/服务类实体。",
                    "description": "核心业务对象",
                    "source_archive_id": "20161116-nas",
                    "source_item_type": "entity",
                    "source_item_id": "entity-nas",
                },
                {
                    "id": "temporary-alert",
                    "name": "协同告警单",
                    "object_kind": "supporting",
                    "source_kind": "temporary",
                    "category": "domain_concept",
                    "aliases": [],
                    "summary": "建模现场新增的支撑对象。",
                    "description": "待后续回流治理",
                    "source_archive_id": None,
                    "source_item_type": None,
                    "source_item_id": None,
                },
            ],
            "processes": [],
            "rules": [],
            "metrics": [],
            "non_functional_constraints": [
                {
                    "id": "constraint-1",
                    "name": "响应时效",
                    "category": "performance",
                    "description": "关键告警 2 分钟内给出处置反馈。",
                }
            ],
        },
    }

    updated = client.put(f"/api/requirements/specs/{spec_id}", json=update_payload)
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["object_count"] == 2
    assert updated_body["formal_object_count"] == 1
    assert updated_body["temporary_object_count"] == 1
    assert updated_body["payload"]["non_functional_constraints"] == [
        {
            "id": "constraint-1",
            "name": "响应时效",
            "category": "performance",
            "description": "关键告警 2 分钟内给出处置反馈。",
        }
    ]

    final_list = client.get("/api/requirements/specs")
    assert final_list.status_code == 200
    assert final_list.json()[0]["temporary_object_count"] == 1
