from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import delete, func, select

from app.db.models.document import DocumentSegment, DocumentVersion, ParseRun
from app.parsing.models import ParsedDocument, ParsedSegment
from app.parsing.parsers.doc_converter import convert_doc_to_docx
from app.parsing.parsers.docx_parser import parse_docx_segments
from app.parsing.parsers.pdf_parser import parse_pdf_segments
from app.parsing.parsers.spreadsheet_parser import parse_spreadsheet_segments


class ParsingService:
    def __init__(self, session=None, storage=None) -> None:
        self.session = session
        self.storage = storage

    def parse_text(self, file_name: str, content: str) -> list[ParsedSegment]:
        del file_name
        blocks = [block.strip() for block in content.strip().split("\n\n") if block.strip()]
        segments: list[ParsedSegment] = []
        for index, block in enumerate(blocks, start=1):
            lines = block.splitlines()
            heading = lines[0]
            body = " ".join(lines[1:])
            segments.append(
                ParsedSegment(
                    heading=heading,
                    content=body,
                    anchor={"page": 1, "section": heading, "line_start": index * 2 - 1, "line_end": index * 2},
                )
            )
        return segments

    def parse_document_version(self, document_version_id: str) -> ParseRun:
        if self.session is None or self.storage is None:
            raise RuntimeError("ParsingService requires session and storage for persisted parsing")

        version = self.session.get(DocumentVersion, document_version_id)
        if version is None:
            raise ValueError(f"Document version not found: {document_version_id}")

        parse_run = ParseRun(
            document_version_id=version.id,
            status="running",
            parser_name="dispatching",
            parser_version="v3",
        )
        self.session.add(parse_run)
        self.session.flush()

        try:
            parsed_document = self.parse_file(self.storage.resolve(version.storage_key), version.file_name)
            parse_run.parser_name = parsed_document.parser_name
            parse_run.parser_version = parsed_document.parser_version
            self.session.execute(delete(DocumentSegment).where(DocumentSegment.parse_run_id == parse_run.id))
            for index, segment in enumerate(parsed_document.segments, start=1):
                self.session.add(
                    DocumentSegment(
                        parse_run_id=parse_run.id,
                        segment_order=index,
                        block_type=segment.block_type,
                        heading=segment.heading,
                        content=segment.content,
                        anchor=segment.anchor,
                    )
                )

            parse_run.status = "succeeded"
            parse_run.failure_reason = None
            version.status = "parsed"
        except Exception as exc:
            parse_run.status = "failed"
            parse_run.failure_reason = str(exc)
            version.status = "parse_failed"

        self.session.commit()
        return parse_run

    def parse_file(self, file_path: Path, file_name: str | None = None) -> ParsedDocument:
        resolved_name = file_name or file_path.name
        adapter = self._resolve_adapter(resolved_name)
        if adapter is None:
            raise ValueError(f"Unsupported document type: {Path(resolved_name).suffix.lower() or '<none>'}")

        return adapter["parse"](file_path)

    def _resolve_adapter(self, file_name: str):
        suffix = Path(file_name).suffix.lower()
        adapters = {
            ".txt": {"name": "plain_text", "parse": self._parse_plain_text},
            ".md": {"name": "plain_text", "parse": self._parse_plain_text},
            ".docx": {"name": "docx", "parse": self._parse_docx},
            ".pdf": {"name": "pdf", "parse": self._parse_pdf},
            ".doc": {"name": "doc", "parse": self._parse_doc},
            ".xlsx": {"name": "spreadsheet", "parse": self._parse_spreadsheet},
            ".xls": {"name": "spreadsheet", "parse": self._parse_spreadsheet},
        }
        return adapters.get(suffix)

    def _parse_plain_text(self, file_path: Path) -> ParsedDocument:
        return ParsedDocument(
            parser_name="plain_text",
            parser_version="v3",
            segments=self.parse_text(file_path.name, file_path.read_text(encoding="utf-8", errors="ignore")),
        )

    def _parse_docx(self, file_path: Path) -> ParsedDocument:
        return parse_docx_segments(str(file_path))

    def _parse_doc(self, file_path: Path) -> ParsedDocument:
        with TemporaryDirectory() as output_dir:
            converted_path = Path(convert_doc_to_docx(str(file_path), output_dir))
            return self._parse_docx(converted_path)

    def _parse_pdf(self, file_path: Path) -> ParsedDocument:
        return parse_pdf_segments(str(file_path))

    def _parse_spreadsheet(self, file_path: Path) -> ParsedDocument:
        return parse_spreadsheet_segments(str(file_path))

    def _segments_from_lines(self, lines: list[str]) -> list[ParsedSegment]:
        segments: list[ParsedSegment] = []
        for index, line in enumerate(lines, start=1):
            heading = line[:255]
            segments.append(
                ParsedSegment(
                    heading=heading,
                    content=line,
                    anchor={"page": 1, "section": heading, "line_start": index, "line_end": index},
                    block_type="paragraph",
                )
            )
        return segments
