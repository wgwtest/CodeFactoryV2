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
    "entity_count": 3,
    "event_count": 1,
    "process_count": 1
  },
  "documents": [
    {
      "id": "doc-1",
      "title": "NAS AV-1",
      "path": "archive/NAS AV-1.pdf",
      "file_type": "pdf",
      "source_archive": "20161116╠σ╧╡╜ß╣╣╬─╧╫╖¡╥δ╗π╫▄",
      "character_count": 1200
    },
    {
      "id": "doc-2",
      "title": "NAS Roadmap",
      "path": "archive/NAS Roadmap.docx",
      "file_type": "docx",
      "source_archive": "20161116-nas",
      "character_count": 840
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
      "id": "entity-ov1",
      "name": "OV-1",
      "category": "architecture_artifact",
      "aliases": ["远期顶层运行概念图"],
      "document_ids": ["doc-1", "doc-2"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "OV-1 excerpt"},
        {"document_id": "doc-2", "excerpt": "Roadmap OV-1 excerpt"}
      ]
    },
    {
      "id": "entity-ov1-duplicate",
      "name": "OV-1 运行概念图",
      "category": "architecture_artifact",
      "aliases": ["运行概念图"],
      "document_ids": ["doc-2"],
      "evidence": [
        {"document_id": "doc-2", "excerpt": "Duplicate OV-1 excerpt"}
      ]
    }
  ],
  "events": [
    {
      "id": "event-far-term",
      "name": "远期目标（Far Term）",
      "category": "timeline_event",
      "aliases": [],
      "document_ids": ["doc-1", "doc-2"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Far Term excerpt"},
        {"document_id": "doc-2", "excerpt": "Roadmap Far Term excerpt"}
      ]
    }
  ],
  "processes": [
    {
      "id": "process-service-interoperability",
      "name": "服务互操作流程",
      "category": "domain_process",
      "aliases": [],
      "document_ids": ["doc-1"],
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Service interoperability excerpt"}
      ]
    }
  ],
  "relations": [
    {"type": "document_mentions", "from": "doc-1", "to": "entity-nas"},
    {"type": "document_mentions", "from": "doc-1", "to": "entity-ov1"},
    {"type": "process_scoped_by", "from": "process-service-interoperability", "to": "event-far-term"},
    {"type": "supports", "from": "entity-nas", "to": "entity-ov1"},
    {"type": "supports", "from": "entity-ov1", "to": "process-service-interoperability"},
    {"type": "supports", "from": "entity-ov1-duplicate", "to": "process-service-interoperability"}
  ]
}
        """.strip(),
        encoding="utf-8",
    )


def test_archive_routes_return_summary_graph_processes_and_search(tmp_path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    app = create_app()
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    summary = client.get("/api/knowledge/archive/20161116-nas/summary")
    graph = client.get("/api/knowledge/archive/20161116-nas/graph")
    processes = client.get("/api/knowledge/archive/20161116-nas/processes")
    search = client.get("/api/knowledge/archive/20161116-nas/search?query=NAS")
    entities = client.get("/api/knowledge/archive/20161116-nas/entities")
    item_detail = client.get("/api/knowledge/archive/20161116-nas/items/entity-ov1")
    document_detail = client.get("/api/knowledge/archive/20161116-nas/documents/doc-1")
    missing_document_detail = client.get("/api/knowledge/archive/20161116-nas/documents/missing")
    documents = client.get("/api/knowledge/archive/20161116-nas/documents")
    review_candidates = client.get("/api/knowledge/archive/20161116-nas/review-candidates")

    assert summary.status_code == 200
    assert summary.json()["document_count"] == 2
    assert summary.json()["entity_count"] == 3

    assert graph.status_code == 200
    assert any(node["label"] == "国家空域系统" for node in graph.json()["nodes"])
    assert any(edge["label"] == "process_scoped_by" for edge in graph.json()["edges"])

    assert processes.status_code == 200
    assert processes.json()[0]["name"] == "服务互操作流程"

    assert search.status_code == 200
    assert search.json()[0]["name"] == "国家空域系统"

    assert entities.status_code == 200
    assert entities.json()[0] == {
        "id": "entity-ov1",
        "name": "OV-1",
        "category": "architecture_artifact",
        "aliases": ["远期顶层运行概念图"],
        "document_count": 2,
        "interpretation": {
            "kind_label": "架构工件",
            "family_code": "OV",
            "family_label": "运行视图",
            "display_name": "高层运行概念图",
            "standard_name": "High-Level Operational Concept Graphic",
            "summary": "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
            "producer_hint": "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
        },
    }
    assert entities.json()[1] == {
        "id": "entity-ov1-duplicate",
        "name": "OV-1 运行概念图",
        "category": "architecture_artifact",
        "aliases": ["运行概念图"],
        "document_count": 1,
        "interpretation": {
            "kind_label": "架构工件",
            "family_code": "OV",
            "family_label": "运行视图",
            "display_name": None,
            "standard_name": None,
            "summary": "OV-1 运行概念图 是架构工件，用于描述业务运行概念、活动和信息交换需求。",
            "producer_hint": "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
        },
    }
    assert entities.json()[2] == {
        "id": "entity-nas",
        "name": "国家空域系统",
        "category": "system_or_service",
        "aliases": ["NAS"],
        "document_count": 1,
        "interpretation": {
            "kind_label": "系统/服务",
            "family_code": None,
            "family_label": None,
            "display_name": None,
            "standard_name": None,
            "summary": "国家空域系统 是系统/服务类实体。",
            "producer_hint": None,
        },
    }

    assert item_detail.status_code == 200
    assert item_detail.json() == {
        "id": "entity-ov1",
        "name": "OV-1",
        "item_type": "entity",
        "category": "architecture_artifact",
        "aliases": ["远期顶层运行概念图"],
        "document_count": 2,
        "review_status": "pending",
        "interpretation": {
            "kind_label": "架构工件",
            "family_code": "OV",
            "family_label": "运行视图",
            "display_name": "高层运行概念图",
            "standard_name": "High-Level Operational Concept Graphic",
            "summary": "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
            "producer_hint": "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
        },
        "documents": [
            {"id": "doc-1", "title": "NAS AV-1", "file_type": "pdf", "source_archive": "20161116体系结构文献翻译汇总"},
            {"id": "doc-2", "title": "NAS Roadmap", "file_type": "docx", "source_archive": "20161116-nas"},
        ],
        "evidence": [
            {"document_id": "doc-1", "document_title": "NAS AV-1", "excerpt": "OV-1 excerpt"},
            {"document_id": "doc-2", "document_title": "NAS Roadmap", "excerpt": "Roadmap OV-1 excerpt"},
        ],
        "related_items": [
            {"id": "entity-nas", "name": "国家空域系统", "item_type": "entity", "relation_type": "supports"},
            {
                "id": "process-service-interoperability",
                "name": "服务互操作流程",
                "item_type": "process",
                "relation_type": "supports",
            },
        ],
    }

    assert document_detail.status_code == 200
    assert document_detail.json()["document"] == {
        "id": "doc-1",
        "title": "NAS AV-1",
        "file_type": "pdf",
        "source_archive": "20161116体系结构文献翻译汇总",
        "character_count": 1200,
        "entity_count": 2,
        "event_count": 1,
        "process_count": 1,
        "knowledge_item_count": 4,
    }
    assert [item["id"] for item in document_detail.json()["knowledge_items"]] == [
        "entity-nas",
        "entity-ov1",
        "event-far-term",
        "process-service-interoperability",
    ]
    ov1_detail = next(item for item in document_detail.json()["knowledge_items"] if item["id"] == "entity-ov1")
    assert ov1_detail["interpretation"]["display_name"] == "高层运行概念图"
    assert ov1_detail["evidence"] == [
        {"document_id": "doc-1", "document_title": "NAS AV-1", "excerpt": "OV-1 excerpt"},
    ]

    assert missing_document_detail.status_code == 404
    assert missing_document_detail.json() == {"detail": "Archive document not found"}

    assert documents.status_code == 200
    assert documents.json()[0] == {
        "id": "doc-1",
        "title": "NAS AV-1",
        "file_type": "pdf",
        "source_archive": "20161116体系结构文献翻译汇总",
        "character_count": 1200,
        "entity_count": 2,
        "event_count": 1,
        "process_count": 1,
        "knowledge_item_count": 4,
    }

    assert review_candidates.status_code == 200
    assert review_candidates.json()[0] == {
        "id": "entity-ov1",
        "item_type": "entity",
        "canonical_name": "OV-1",
        "category": "architecture_artifact",
        "document_count": 2,
        "confidence": 0.9,
        "review_status": "pending",
        "evidence_excerpt": "OV-1 excerpt",
        "evidence_document_title": "NAS AV-1",
    }


def test_archive_review_mutations_create_curated_knowledge_and_update_public_views(tmp_path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    app = create_app()
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    updated = client.patch(
        "/api/knowledge/archive/20161116-nas/items/entity-ov1",
        json={
            "name": "OV-1 修正版",
            "category": "architecture_concept",
            "aliases": ["运行概念图", "OV-1"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "OV-1 修正版"
    assert updated.json()["category"] == "architecture_concept"
    assert updated.json()["aliases"] == ["运行概念图", "OV-1"]
    assert updated.json()["review_status"] == "pending"

    curated_file = tmp_path / "20161116-nas-knowledge-curated.json"
    assert curated_file.exists()

    approved = client.post(
        "/api/knowledge/archive/20161116-nas/reviews/batch-approve",
        json={"item_ids": ["entity-ov1", "event-far-term"]},
    )
    assert approved.status_code == 200
    assert approved.json() == {"updated_count": 2}

    approved_candidates = client.get("/api/knowledge/archive/20161116-nas/review-candidates?review_status=approved")
    assert approved_candidates.status_code == 200
    assert {item["id"] for item in approved_candidates.json()} == {"entity-ov1", "event-far-term"}

    rejected = client.post(
        "/api/knowledge/archive/20161116-nas/items/entity-nas/review",
        json={"review_status": "rejected"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["id"] == "entity-nas"
    assert rejected.json()["review_status"] == "rejected"

    graph = client.get("/api/knowledge/archive/20161116-nas/graph")
    assert graph.status_code == 200
    assert all(node["id"] != "entity-nas" for node in graph.json()["nodes"])

    document_detail = client.get("/api/knowledge/archive/20161116-nas/documents/doc-1")
    assert document_detail.status_code == 200
    assert [item["id"] for item in document_detail.json()["knowledge_items"]] == [
        "entity-ov1",
        "event-far-term",
        "process-service-interoperability",
    ]

    search = client.get("/api/knowledge/archive/20161116-nas/search?query=国家空域系统")
    assert search.status_code == 200
    assert search.json() == []

    rejected_candidates = client.get("/api/knowledge/archive/20161116-nas/review-candidates?review_status=rejected")
    assert rejected_candidates.status_code == 200
    assert rejected_candidates.json()[0]["id"] == "entity-nas"

    merged = client.post(
        "/api/knowledge/archive/20161116-nas/items/merge",
        json={"primary_item_id": "entity-ov1", "secondary_item_id": "entity-ov1-duplicate"},
    )
    assert merged.status_code == 200
    assert merged.json()["id"] == "entity-ov1"
    assert merged.json()["name"] == "OV-1 修正版"
    assert merged.json()["aliases"] == ["运行概念图", "OV-1", "OV-1 运行概念图"]

    summary = client.get("/api/knowledge/archive/20161116-nas/summary")
    assert summary.status_code == 200
    assert summary.json() == {
        "archive_id": "20161116-nas",
        "document_count": 2,
        "entity_count": 1,
        "event_count": 1,
        "process_count": 1,
    }

    graph_after_merge = client.get("/api/knowledge/archive/20161116-nas/graph")
    assert graph_after_merge.status_code == 200
    assert any(node["id"] == "entity-ov1" and node["label"] == "OV-1 修正版" for node in graph_after_merge.json()["nodes"])
    assert all(node["id"] != "entity-ov1-duplicate" for node in graph_after_merge.json()["nodes"])
    assert graph_after_merge.json()["edges"].count(
        {"source": "entity-ov1", "target": "process-service-interoperability", "label": "supports"}
    ) == 1

    document_detail_after_merge = client.get("/api/knowledge/archive/20161116-nas/documents/doc-2")
    assert document_detail_after_merge.status_code == 200
    assert [item["id"] for item in document_detail_after_merge.json()["knowledge_items"]] == [
        "entity-ov1",
        "event-far-term",
    ]
    ov1_detail = next(item for item in document_detail_after_merge.json()["knowledge_items"] if item["id"] == "entity-ov1")
    assert ov1_detail["aliases"] == ["运行概念图", "OV-1", "OV-1 运行概念图"]
    assert ov1_detail["evidence"] == [
        {"document_id": "doc-2", "document_title": "NAS Roadmap", "excerpt": "Roadmap OV-1 excerpt"},
        {"document_id": "doc-2", "document_title": "NAS Roadmap", "excerpt": "Duplicate OV-1 excerpt"},
    ]


def test_archive_publish_creates_versioned_snapshot_and_publication_overview(tmp_path) -> None:
    archive_file = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(archive_file)

    app = create_app()
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    publication_before = client.get("/api/knowledge/archive/20161116-nas/publication")
    assert publication_before.status_code == 200
    assert publication_before.json()["current_version"] is None

    approved = client.post(
        "/api/knowledge/archive/20161116-nas/reviews/batch-approve",
        json={
            "item_ids": [
                "entity-nas",
                "entity-ov1",
                "entity-ov1-duplicate",
                "event-far-term",
                "process-service-interoperability",
            ]
        },
    )
    assert approved.status_code == 200
    assert approved.json() == {"updated_count": 5}

    published = client.post(
        "/api/knowledge/archive/20161116-nas/publish",
        json={"version_label": "v1", "publisher": "architect"},
    )
    assert published.status_code == 200
    assert published.json()["version_label"] == "v1"
    assert published.json()["publisher"] == "architect"
    assert published.json()["summary"] == {
        "document_count": 2,
        "entity_count": 3,
        "event_count": 1,
        "process_count": 1,
    }

    publication_after = client.get("/api/knowledge/archive/20161116-nas/publication")
    assert publication_after.status_code == 200
    assert publication_after.json()["current_version"] == {
        "version_label": "v1",
        "publisher": "architect",
        "published_at": published.json()["published_at"],
        "summary": {
            "document_count": 2,
            "entity_count": 3,
            "event_count": 1,
            "process_count": 1,
        },
    }
    assert publication_after.json()["versions"][0]["version_label"] == "v1"

    graph = client.get("/api/knowledge/archive/20161116-nas/graph")
    assert graph.status_code == 200
    assert graph.json()["publication"]["version_label"] == "v1"
    assert graph.json()["publication"]["publisher"] == "architect"

    assert (tmp_path / "20161116-nas-published-v1.json").exists()
