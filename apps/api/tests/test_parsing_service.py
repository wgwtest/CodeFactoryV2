from pathlib import Path

from openpyxl import Workbook

from app.documents.service import DocumentService
from app.documents.storage import LocalStorage
from app.parsing.service import ParsingService


def test_parser_creates_ordered_segments_with_evidence() -> None:
    source = Path("tests/fixtures/reference_scenarios/minimal_policy.txt")
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


def test_parser_supports_spreadsheet_documents(db_session, temp_storage_dir, tmp_path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "运行节点"
    sheet.append(["节点代号", "节点名称", "职责"])
    sheet.append(["ATCT", "机场塔台管制", "地面和起飞管制"])
    sheet.append(["TRACON", "终端雷达进近管制", "终端进近管制"])

    spreadsheet_path = tmp_path / "nodes.xlsx"
    workbook.save(spreadsheet_path)

    storage = LocalStorage(str(temp_storage_dir))
    document_service = DocumentService(db_session, storage)
    parsing_service = ParsingService(db_session, storage)

    document, version = document_service.upload(
        title="运行节点清单",
        source_name="fixture",
        document_key="operational-nodes",
        file_name="nodes.xlsx",
        content=spreadsheet_path.read_bytes(),
    )

    parse_run = parsing_service.parse_document_version(version.id)
    detail = document_service.get_document_detail(document.id)

    assert parse_run.status == "succeeded"
    assert detail["latest_version"]["status"] == "parsed"
    assert detail["latest_version"]["latest_parse_run"]["parser_name"] == "spreadsheet_openpyxl"
    assert detail["latest_version"]["latest_parse_run"]["segment_count"] >= 2
    assert detail["versions"][0]["segments_preview"][0]["anchor"]["sheet"] == "运行节点"
    assert "机场塔台管制" in detail["versions"][0]["segments_preview"][0]["content"]
