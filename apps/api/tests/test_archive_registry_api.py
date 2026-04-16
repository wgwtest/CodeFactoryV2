import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.archives import (
    get_archive_extraction_coordinator,
    get_archive_extraction_service,
    get_archive_registry_service,
)
from app.archive_knowledge.coordination import ArchiveExtractionCoordinator
from app.api.routes.knowledge import get_archive_knowledge_service
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.archive_knowledge.registry import ArchiveRegistryService
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.main import create_app


def _write_archive(
    path: Path,
    *,
    document_title: str,
    entity_name: str,
    entity_count: int,
) -> None:
    payload = {
        "summary": {
            "document_count": 1,
            "entity_count": entity_count,
            "event_count": 0,
            "process_count": 0,
        },
        "documents": [
            {
                "id": "doc-1",
                "title": document_title,
                "path": f"archive/{document_title}.docx",
                "file_type": "docx",
                "source_archive": "测试档案",
                "character_count": 1200,
            }
        ],
        "entities": [
            {
                "id": f"entity-{index + 1}",
                "name": entity_name if index == 0 else f"{entity_name}-{index + 1}",
                "category": "domain_concept",
                "aliases": [],
                "document_ids": ["doc-1"],
                "evidence": [{"document_id": "doc-1", "excerpt": f"{entity_name} excerpt"}],
            }
            for index in range(entity_count)
        ],
        "events": [],
        "processes": [],
        "relations": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_archive_registry_and_extraction_keep_existing_archive_intact(tmp_path, monkeypatch) -> None:
    legacy_source_dir = tmp_path / "legacy-source"
    legacy_source_dir.mkdir()
    new_source_dir = tmp_path / "domain-b-source"
    new_source_dir.mkdir()

    legacy_archive_path = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(
        legacy_archive_path,
        document_title="Legacy NAS",
        entity_name="国家空域系统",
        entity_count=1,
    )
    legacy_original = legacy_archive_path.read_text(encoding="utf-8")

    app = create_app()
    registry_service = ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=legacy_source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )
    extraction_service = ArchiveExtractionService(tmp_path)

    def fake_build_archive(self, archive_id: str, *, source_dir: Path, extract_root: Path, archive_name: str):
        assert archive_id == "domain-b"
        assert source_dir == new_source_dir
        assert extract_root == tmp_path / ".extract" / "domain-b"
        assert archive_name == "领域 B 知识库"
        archive_path = tmp_path / "domain-b-knowledge.json"
        markdown_path = tmp_path / "domain-b-knowledge.md"
        _write_archive(
            archive_path,
            document_title="Domain B Guide",
            entity_name="领域 B 对象",
            entity_count=2,
        )
        markdown_path.write_text("# Domain B Guide\n", encoding="utf-8")
        return {
            "archive_id": archive_id,
            "source_dir": str(source_dir),
            "extract_root": str(extract_root),
            "json_path": str(archive_path),
            "markdown_path": str(markdown_path),
            "summary": {
                "document_count": 1,
                "entity_count": 2,
                "event_count": 0,
                "process_count": 0,
            },
        }

    monkeypatch.setattr(ArchiveExtractionService, "build_archive", fake_build_archive)

    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: extraction_service
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    listed = client.get("/api/archives")
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "archive_id": "20161116-nas",
            "name": "默认 NAS 知识库",
            "source_dir": str(legacy_source_dir),
            "extract_root": str(tmp_path / "legacy-extract"),
            "is_active": True,
            "status": "ready",
            "last_built_at": None,
            "last_error": None,
            "summary": {
                "document_count": 1,
                "entity_count": 1,
                "event_count": 0,
                "process_count": 0,
            },
            "build_state": None,
            "artifacts": {
                "base_exists": True,
                "curated_exists": False,
                "publication_exists": False,
            },
        }
    ]

    created = client.post(
        "/api/archives",
        json={
            "archive_id": "domain-b",
            "name": "领域 B 知识库",
            "source_dir": str(new_source_dir),
        },
    )
    assert created.status_code == 200
    assert created.json()["archive_id"] == "domain-b"
    assert created.json()["status"] == "empty"
    assert created.json()["summary"] is None
    assert created.json()["build_state"] is None

    extracted = client.post("/api/archives/domain-b/extract")
    assert extracted.status_code == 200
    assert extracted.json()["archive_id"] == "domain-b"
    assert extracted.json()["status"] == "ready"
    assert extracted.json()["summary"]["entity_count"] == 2
    assert (tmp_path / "domain-b-knowledge.json").exists()
    assert legacy_archive_path.read_text(encoding="utf-8") == legacy_original

    activated = client.post("/api/archives/domain-b/activate")
    assert activated.status_code == 200
    assert activated.json()["archive_id"] == "domain-b"
    assert activated.json()["is_active"] is True

    domain_summary = client.get("/api/knowledge/archive/domain-b/summary")
    assert domain_summary.status_code == 200
    assert domain_summary.json() == {
        "archive_id": "domain-b",
        "document_count": 1,
        "entity_count": 2,
        "event_count": 0,
        "process_count": 0,
    }

    listed_after = client.get("/api/archives")
    assert listed_after.status_code == 200
    assert [item["archive_id"] for item in listed_after.json()] == ["20161116-nas", "domain-b"]
    assert listed_after.json()[0]["is_active"] is False
    assert listed_after.json()[1]["is_active"] is True


def test_archive_registry_exposes_current_chunk_progress_in_build_state(tmp_path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    archive_path = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(
        archive_path,
        document_title="Legacy NAS",
        entity_name="国家空域系统",
        entity_count=1,
    )
    build_state_path = tmp_path / "20161116-nas-document-build-state.json"
    build_state_path.write_text(
        json.dumps(
            {
                "archive_id": "20161116-nas",
                "archive_name": "默认 NAS 知识库",
                "mode": "formal",
                "status": "running",
                "started_at": "2026-04-16T10:00:00+00:00",
                "updated_at": "2026-04-16T10:05:00+00:00",
                "expected_document_count": 3,
                "completed_document_ids": ["doc-1"],
                "pending_document_ids": ["doc-3"],
                "failed_document_id": None,
                "failed_message": None,
                "current_document_id": "doc-2",
                "current_document_title": "FM 6-0",
                "current_document_path": "runtime/FM_6-0.pdf",
                "current_chunk": {
                    "chunk_id": "chunk-007",
                    "position": 7,
                    "total": 19,
                    "heading": "Command and staff relationships",
                    "char_count": 4321,
                    "segment_count": 8,
                    "retry_depth": 1,
                },
                "documents": [
                    {
                        "document_id": "doc-1",
                        "path": "runtime/ADRP.pdf",
                        "title": "ADRP",
                        "file_type": "pdf",
                        "source_archive": "kb",
                        "state": "completed",
                    },
                    {
                        "document_id": "doc-2",
                        "path": "runtime/FM_6-0.pdf",
                        "title": "FM 6-0",
                        "file_type": "pdf",
                        "source_archive": "kb",
                        "state": "running",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    app = create_app()
    registry_service = ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: ArchiveExtractionService(tmp_path)
    app.dependency_overrides[get_archive_knowledge_service] = lambda: ArchiveKnowledgeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/archives")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["build_state"]["current_chunk"] == {
        "chunk_id": "chunk-007",
        "position": 7,
        "total": 19,
        "heading": "Command and staff relationships",
        "char_count": 4321,
        "segment_count": 8,
        "retry_depth": 1,
    }


def test_archive_extract_rejects_parallel_requests(tmp_path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    archive_path = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(
        archive_path,
        document_title="Legacy NAS",
        entity_name="国家空域系统",
        entity_count=1,
    )

    app = create_app()
    registry_service = ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )

    class BusyCoordinator:
        current_archive_id = "another-kb"

        def try_start(self, archive_id: str) -> bool:
            return False

        def finish(self, archive_id: str) -> None:
            return None

    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: ArchiveExtractionService(tmp_path)
    app.dependency_overrides[get_archive_extraction_coordinator] = lambda: BusyCoordinator()
    client = TestClient(app)

    response = client.post("/api/archives/20161116-nas/extract")

    assert response.status_code == 409
    assert response.json() == {"detail": "当前已有知识库正在抽取中：another-kb，请等待完成后再试"}


def test_archive_document_formalize_route_returns_incremental_result(tmp_path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    expected_source_dir = source_dir

    archive_path = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(
        archive_path,
        document_title="Legacy NAS",
        entity_name="国家空域系统",
        entity_count=1,
    )

    app = create_app()
    registry_service = ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )

    class StubExtractionService(ArchiveExtractionService):
        def formalize_document(
            self,
            archive_id: str,
            *,
            document_id: str,
            source_dir: Path,
            extract_root: Path,
            archive_name: str | None = None,
        ) -> dict:
            assert archive_id == "20161116-nas"
            assert document_id == "doc-1"
            assert source_dir == expected_source_dir
            assert extract_root == tmp_path / "legacy-extract"
            assert archive_name == "默认 NAS 知识库"
            return {
                "archive_id": archive_id,
                "document_id": document_id,
                "mode": "incremental_merge",
                "summary": {
                    "document_count": 1,
                    "entity_count": 2,
                    "event_count": 0,
                    "process_count": 0,
                },
                "document": {
                    "id": document_id,
                    "title": "Legacy NAS",
                    "file_type": "docx",
                    "source_archive": "测试档案",
                    "character_count": 1200,
                    "entity_count": 2,
                    "event_count": 0,
                    "process_count": 0,
                    "knowledge_item_count": 2,
                },
            }

    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: StubExtractionService(tmp_path)
    app.dependency_overrides[get_archive_extraction_coordinator] = lambda: ArchiveExtractionCoordinator()
    client = TestClient(app)

    response = client.post("/api/archives/20161116-nas/documents/doc-1/formalize")

    assert response.status_code == 200
    assert response.json()["archive_id"] == "20161116-nas"
    assert response.json()["document_id"] == "doc-1"
    assert response.json()["mode"] == "incremental_merge"
    assert response.json()["summary"]["entity_count"] == 2


def test_archive_document_remove_route_returns_incremental_result(tmp_path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    expected_source_dir = source_dir

    archive_path = tmp_path / "20161116-nas-knowledge.json"
    _write_archive(
        archive_path,
        document_title="Legacy NAS",
        entity_name="国家空域系统",
        entity_count=1,
    )

    app = create_app()
    registry_service = ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )

    class StubExtractionService(ArchiveExtractionService):
        def remove_document(
            self,
            archive_id: str,
            *,
            document_id: str,
            source_dir: Path,
            extract_root: Path,
            archive_name: str | None = None,
        ) -> dict:
            assert archive_id == "20161116-nas"
            assert document_id == "doc-1"
            assert source_dir == expected_source_dir
            assert extract_root == tmp_path / "legacy-extract"
            assert archive_name == "默认 NAS 知识库"
            return {
                "archive_id": archive_id,
                "document_id": document_id,
                "action": "remove",
                "mode": "incremental_remove",
                "document_included": False,
                "summary": {
                    "document_count": 0,
                    "entity_count": 0,
                    "event_count": 0,
                    "process_count": 0,
                },
                "document": {
                    "id": document_id,
                    "title": "Legacy NAS",
                    "file_type": "docx",
                    "source_archive": "测试档案",
                    "character_count": 1200,
                    "entity_count": 1,
                    "event_count": 0,
                    "process_count": 0,
                    "knowledge_item_count": 1,
                    "included_in_archive": False,
                },
            }

    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: StubExtractionService(tmp_path)
    app.dependency_overrides[get_archive_extraction_coordinator] = lambda: ArchiveExtractionCoordinator()
    client = TestClient(app)

    response = client.post("/api/archives/20161116-nas/documents/doc-1/remove")

    assert response.status_code == 200
    assert response.json()["archive_id"] == "20161116-nas"
    assert response.json()["document_id"] == "doc-1"
    assert response.json()["action"] == "remove"
    assert response.json()["mode"] == "incremental_remove"
    assert response.json()["document_included"] is False
