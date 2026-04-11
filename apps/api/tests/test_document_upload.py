from app.documents.service import DocumentService
from app.documents.storage import LocalStorage


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
