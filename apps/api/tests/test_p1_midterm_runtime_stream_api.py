from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.archives import get_archive_runtime_service
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.runtime_service import ArchiveDocumentRuntimeService
from app.main import create_app


def _midterm_contribution(document_id: str = "midterm-doc-1") -> dict:
    return {
        "document": {
            "id": document_id,
            "path": "Mid Term/SV-2.docx",
            "title": "Mid Term SV-2",
            "file_type": "docx",
            "source_archive": "midterm",
            "character_count": 2400,
            "parser_name": "docling.docx",
            "segment_count": 8,
            "source_file_path": "E:/sample/Mid Term/SV-2.docx",
            "source_digest": "sha256:midterm-demo",
        },
        "entities": [
            {
                "id": "midterm-entity-1",
                "name": "National Airspace System",
                "category": "domain_concept",
                "aliases": ["NAS"],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": "National Airspace System overview."}],
            }
        ],
        "events": [],
        "processes": [
            {
                "id": "midterm-process-1",
                "name": "Mission Orchestration",
                "category": "domain_process",
                "aliases": [],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": "Mission orchestration depends on evidence packs."}],
            }
        ],
        "relations": [
            {
                "type": "part_of",
                "source_name": "National Airspace System",
                "target_name": "Mission Orchestration",
                "confidence": 0.92,
                "evidence": "The NAS contains mission orchestration flows.",
            }
        ],
        "extraction": {
            "strategy": "formal",
            "schema_version": "v1",
            "candidate_count": 2,
            "relation_count": 1,
            "chunking_used": True,
        },
    }


def test_p1_midterm_runtime_polling_contract_contains_w3_fields(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("midterm-archive", _midterm_contribution(), included_in_archive=True)

    app = create_app()
    app.dependency_overrides[get_archive_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/archives/midterm-archive/runtime",
        params={
            "document_id": "midterm-doc-1",
            "document_set_id": "midterm-document-set",
            "policy_package_version_id": "policy-package-v7",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["document_set_id"] == "midterm-document-set"
    assert payload["policy_package_version_id"] == "policy-package-v7"
    assert payload["runtime_snapshot_id"] == "midterm-archive:midterm-doc-1:policy-package-v7:runtime"
    assert payload["stream_status"] == "polling"
    assert payload["current_document_id"] == "midterm-doc-1"
    assert payload["current_stage_or_rule_id"]
    assert payload["runtime_events"]
    assert payload["graph_projection"]["nodes"]
    assert any(candidate["candidate_type"] == "relation" for candidate in payload["generated_candidates"])


def test_p1_midterm_runtime_stream_contract_matches_polling_shape(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("midterm-archive", _midterm_contribution(), included_in_archive=True)

    app = create_app()
    app.dependency_overrides[get_archive_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/archives/midterm-archive/runtime/stream",
        params={
            "document_id": "midterm-doc-1",
            "document_set_id": "midterm-document-set",
            "policy_package_version_id": "policy-package-v7",
            "interval_ms": 1000,
            "heartbeat_ms": 1000,
            "max_events": 1,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    first_event = response.text.split("\n\n", 1)[0]
    assert "event: runtime" in first_event
    data_line = next(line for line in first_event.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))

    assert payload["document_set_id"] == "midterm-document-set"
    assert payload["policy_package_version_id"] == "policy-package-v7"
    assert payload["stream_status"] == "streaming"
    assert payload["runtime_events"]
    assert payload["graph_projection"]["nodes"]
    assert payload["generated_candidates"]
