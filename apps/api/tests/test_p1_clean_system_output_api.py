from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.p1_refactor import get_p1_archive_knowledge_service
from app.api.routes.knowledge import get_archive_knowledge_service
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
    "process_count": 0
  },
  "documents": [
    {
      "id": "doc-1",
      "title": "Formal source",
      "path": "archive/source.pdf",
      "file_type": "pdf",
      "source_archive": "system-output-test",
      "character_count": 1200
    }
  ],
  "entities": [
    {
      "id": "entity-approved",
      "name": "Approved formal entity",
      "category": "system_or_service",
      "aliases": [],
      "document_ids": ["doc-1"],
      "review_status": "approved",
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Approved evidence"}
      ]
    },
    {
      "id": "entity-pending",
      "name": "Pending candidate entity",
      "category": "system_or_service",
      "aliases": [],
      "document_ids": ["doc-1"],
      "review_status": "pending",
      "evidence": [
        {"document_id": "doc-1", "excerpt": "Pending evidence"}
      ]
    }
  ],
  "events": [],
  "processes": [],
  "relations": []
}
        """.strip(),
        encoding="utf-8",
    )


def test_p1_clean_system_output_requires_governed_publication_snapshot(tmp_path: Path) -> None:
    _write_archive(tmp_path / "kb-knowledge.json")

    app = create_app()
    service_factory = lambda: ArchiveKnowledgeService(tmp_path)
    app.dependency_overrides[get_archive_knowledge_service] = service_factory
    app.dependency_overrides[get_p1_archive_knowledge_service] = service_factory
    client = TestClient(app)

    before_publish = client.get("/api/p1/archives/kb/system-output?publication_snapshot_id=kb:latest-publication")
    assert before_publish.status_code == 200
    before_body = before_publish.json()
    assert before_body["contract_version"] == "p1.system_output.preview.r1"
    assert before_body["data"]["contract_version"] == "P1CleanSystemOutputContract.v1"
    assert before_body["data"]["supply_available"] is False
    assert before_body["data"]["is_formalized"] is False
    assert "No governed publication snapshot" in before_body["data"]["unavailable_reason"]
    assert before_body["data"]["formal_interfaces"] == []
    assert before_body["data"]["api_exposure_scope"]["exposure_mode"] == "not_available"

    published = client.post(
        "/api/knowledge/archive/kb/publish",
        json={"version_label": "v1", "publisher": "governance-confirmation"},
    )
    assert published.status_code == 200

    response = client.get("/api/p1/archives/kb/system-output?publication_snapshot_id=kb:latest-publication")
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["contract_version"] == "p1.system_output.preview.r1"
    body = envelope["data"]
    assert body["contract_version"] == "P1CleanSystemOutputContract.v1"
    assert body["archive_id"] == "kb"
    assert body["publication_snapshot_id"] == "kb:latest-publication"
    assert body["canonical_publication_snapshot_id"] == "kb:v1"
    assert body["formal_version"] == "v1"
    assert body["formal_version_id"] == "kb:v1"
    assert body["supply_available"] is True
    assert body["is_formalized"] is True
    assert body["source_kind"] == "governed_publication_snapshot"
    assert body["source_summary"]["entity_count"] == 1
    assert {item["path"] for item in body["formal_interfaces"]} >= {
        "/api/knowledge/archive/kb/summary",
        "/api/knowledge/archive/kb/graph",
        "/api/knowledge/archive/kb/publication",
    }
    assert body["version_selection_rules"][0]["governance_boundary"] == "post_publication_confirmation"
    assert "runtime_temporary_nodes" in body["adapter_contract"]["forbidden_sources"]
    assert "publication_candidate_snapshot" in body["adapter_contract"]["forbidden_sources"]
    assert body["api_exposure_scope"]["exposure_mode"] == "formal_only"
    assert body["api_exposure_scope"]["candidate_api_paths"] == []
    assert body["readable_objects"][0]["object_id"] == "entity-approved"
    assert body["readable_evidence"][0]["excerpt"] == "Approved evidence"
    assert {consumer["consumer"] for consumer in body["downstream_consumers"]} == {"P2", "P3"}

    graph = client.get("/api/knowledge/archive/kb/graph")
    assert graph.status_code == 200
    assert {node["id"] for node in graph.json()["nodes"]} == {"entity-approved"}

    mismatch = client.get("/api/p1/archives/kb/system-output?publication_snapshot_id=kb:not-current")
    assert mismatch.status_code == 200
    mismatch_body = mismatch.json()["data"]
    assert mismatch_body["supply_available"] is False
    assert "does not match" in mismatch_body["unavailable_reason"]
