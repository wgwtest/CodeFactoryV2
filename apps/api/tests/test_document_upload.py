from app.documents.service import DocumentService
from app.documents.storage import LocalStorage
from app.parsing.service import ParsingService


def test_upload_creates_document_and_version(db_session, temp_storage_dir) -> None:
    service = DocumentService(db_session, LocalStorage(str(temp_storage_dir)))
    document, version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"Incident must be reported within 2 hours.",
    )

    assert document.title == "Incident Policy"
    assert version.version_number == 1
    assert version.status == "uploaded"


def test_uploading_same_document_key_creates_new_version(db_session, temp_storage_dir) -> None:
    service = DocumentService(db_session, LocalStorage(str(temp_storage_dir)))

    first_document, first_version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"version one",
    )
    second_document, second_version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"version two",
    )

    assert first_document.id == second_document.id
    assert first_version.version_number == 1
    assert second_version.version_number == 2


def test_uploaded_document_detail_reports_parse_runs_and_segment_preview(db_session, temp_storage_dir) -> None:
    storage = LocalStorage(str(temp_storage_dir))
    document_service = DocumentService(db_session, storage)
    parsing_service = ParsingService(db_session, storage)

    document, version = document_service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=(
            b"Section 1\n"
            b"Policy overview.\n\n"
            b"Section 2\n"
            b"Every incident report must be submitted within 2 hours.\n"
        ),
    )

    parse_run = parsing_service.parse_document_version(version.id)
    detail = document_service.get_document_detail(document.id)

    assert parse_run.status == "succeeded"
    assert detail["latest_version"]["status"] == "parsed"
    assert detail["latest_version"]["latest_parse_run"]["parser_name"] == "plain_text"
    assert detail["latest_version"]["latest_parse_run"]["segment_count"] == 2
    assert detail["versions"][0]["segments_preview"][0]["heading"] == "Section 1"
    assert "submitted within 2 hours" in detail["versions"][0]["segments_preview"][1]["content"]
