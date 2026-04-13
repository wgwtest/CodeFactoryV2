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
