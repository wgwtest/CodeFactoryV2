from pathlib import Path

from app.documents.service import DocumentService
from app.documents.storage import LocalStorage
from app.parsing.service import ParsingService


def test_parser_creates_ordered_segments_with_evidence() -> None:
    source = Path("fixtures/reference_scenarios/minimal_policy.txt")
    document_text = source.read_text()

    service = ParsingService()
    segments = service.parse_text("minimal_policy.txt", document_text)

    assert len(segments) == 3
    assert segments[0].heading == "Section 1"
    assert segments[0].anchor == {"page": 1, "section": "Section 1", "line_start": 1, "line_end": 2}
    assert "incident report" in segments[1].content.lower()


def test_parser_records_failed_run_for_unsupported_document_type(db_session, temp_storage_dir) -> None:
    storage = LocalStorage(str(temp_storage_dir))
    document_service = DocumentService(db_session, storage)
    parsing_service = ParsingService(db_session, storage)

    document, version = document_service.upload(
        title="Unsupported Source",
        source_name="fixture",
        document_key="unsupported-source",
        file_name="unsupported.bin",
        content=b"binary-content",
    )

    parse_run = parsing_service.parse_document_version(version.id)
    detail = document_service.get_document_detail(document.id)

    assert parse_run.status == "failed"
    assert detail["latest_version"]["status"] == "parse_failed"
    assert detail["latest_version"]["latest_parse_run"]["failure_reason"] == "Unsupported document type: .bin"
    assert detail["versions"][0]["segments_preview"] == []
