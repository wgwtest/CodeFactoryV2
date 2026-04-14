from pathlib import Path

from app.config import settings
from app.parsing.models import ParsedDocument, ParsedSegment
from app.parsing.parsers import pdf_parser


def _set_setting(name: str, value) -> None:
    object.__setattr__(settings, name, value)


def test_parse_pdf_skips_docling_when_pdf_docling_is_disabled(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4\n")

    calls: dict[str, int] = {"docling": 0}

    def fake_docling(file_path: str) -> ParsedDocument:
        del file_path
        calls["docling"] += 1
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

    def fake_unstructured(file_path: str) -> ParsedDocument:
        del file_path
        return ParsedDocument(
            parser_name="unstructured_pdf",
            parser_version="v3",
            segments=[
                ParsedSegment(
                    block_id="pdf-unstructured-1",
                    heading="OV-2",
                    content="运行节点关联关系图",
                    anchor={"page": 1, "section": "OV-2", "line_start": 1, "line_end": 1},
                    block_type="paragraph",
                )
            ],
        )

    _set_setting("docling_pdf_enabled", False)
    monkeypatch.setattr(pdf_parser, "_parse_pdf_with_docling", fake_docling)
    monkeypatch.setattr(pdf_parser, "_parse_pdf_with_unstructured", fake_unstructured)

    parsed = pdf_parser.parse_pdf_segments(str(path))

    assert calls["docling"] == 0
    assert parsed.parser_name == "unstructured_pdf"
    assert parsed.segments[0].content == "运行节点关联关系图"


def test_parse_pdf_uses_docling_parse_backend_when_converter_returns_no_segments(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4\n")

    def fake_converter(file_path: str) -> ParsedDocument:
        del file_path
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

    def fake_backend(file_path: str) -> ParsedDocument:
        del file_path
        return ParsedDocument(
            parser_name="docling_pdf",
            parser_version="v3",
            segments=[
                ParsedSegment(
                    block_id="docling-pdf-3-1",
                    heading="国家空域体系",
                    content="国家空域体系 由多个运行节点和协同流程构成",
                    anchor={"page": 3, "section": "国家空域体系", "line_start": 1, "line_end": 1},
                    block_type="paragraph",
                )
            ],
        )

    monkeypatch.setattr(pdf_parser, "_parse_pdf_with_docling_converter", fake_converter, raising=False)
    monkeypatch.setattr(pdf_parser, "_parse_pdf_with_docling_backend", fake_backend, raising=False)

    parsed = pdf_parser._parse_pdf_with_docling(str(path))

    assert parsed.parser_name == "docling_pdf"
    assert len(parsed.segments) == 1
    assert parsed.segments[0].anchor["page"] == 3
    assert parsed.segments[0].content == "国家空域体系 由多个运行节点和协同流程构成"
