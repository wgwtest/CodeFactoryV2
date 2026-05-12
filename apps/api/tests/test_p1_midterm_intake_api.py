from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.p1_refactor import get_archive_registry_service, get_p1_intake_service
from app.archive_knowledge.p1_modules.intake import P1IntakeService
from app.archive_knowledge.registry import ArchiveRegistryService
from app.main import create_app


MIDTERM_DOCX_NAMES = [
    "10002581_NAS-EA-AV-1-Mid-Term-v3.0-022814.docx",
    "10002584_NAS-EA-OV-1-Mid-Term-v3.0-022814-OV-1.docx",
    "10002585_NAS-EA-OV-2-Mid-Term-v3.0-022814-OV-2.docx",
    "10002589_NAS-EA-OV-7-Mid-Term-v3.0-022814.docx",
    "10002660_NAS-EA-OV-5-Mid-Term-v3.0-022814.docx",
    "SV-1翻译.docx",
    "SV-2翻译.docx",
    "SV-4翻译.docx",
]


def test_p1_midterm_intake_scans_source_dir_without_faking_parse_success(tmp_path: Path) -> None:
    source_dir = tmp_path / "Mid Term"
    source_dir.mkdir()
    for file_name in MIDTERM_DOCX_NAMES:
        (source_dir / file_name).write_bytes(f"fixture:{file_name}".encode("utf-8"))

    output_root = tmp_path / "knowledge-output"
    registry_service = ArchiveRegistryService(
        output_root,
        default_archive_id="default-kb",
        default_archive_name="Default KB",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "extract" / "default-kb",
        extract_root_parent=tmp_path / "extract",
    )
    registry_service.create_archive(
        archive_id="midterm-kb",
        name="Mid Term 知识库",
        source_dir=source_dir,
    )

    app = create_app()
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_p1_intake_service] = lambda: P1IntakeService(output_root)
    client = TestClient(app)

    response = client.get("/api/p1/archives/midterm-kb/intake")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "p1.intake.r1"
    assert body["source_kind"] == "live"
    snapshot = body["data"]
    assert snapshot["document_set_id"] == "midterm-kb:document-set"
    assert snapshot["summary"]["document_count"] == 8
    assert snapshot["summary"]["pending_count"] == 8
    assert snapshot["summary"]["can_enter_runtime_count"] == 0
    assert {document["file_name"] for document in snapshot["documents"]} == set(MIDTERM_DOCX_NAMES)
    assert {document["file_type"] for document in snapshot["documents"]} == {"docx"}
    assert {document["parse_status"] for document in snapshot["documents"]} == {"pending"}
    assert all(document["parse_error"] for document in snapshot["documents"])
    assert all(document["can_enter_runtime"] is False for document in snapshot["documents"])
    assert any("尚未完成解析" in issue for issue in snapshot["preflight_issues"])
