from __future__ import annotations

import fitz

from app.config import settings
from app.parsing.models import ParsedDocument, ParsedSegment


def parse_pdf(file_path: str) -> list[tuple[int, str]]:
    document = fitz.open(file_path)
    return [(page.number + 1, page.get_text("text")) for page in document]


def parse_pdf_segments(file_path: str) -> ParsedDocument:
    if settings.docling_pdf_enabled:
        parsed = _parse_pdf_with_docling(file_path)
        if parsed.segments:
            return parsed

    parsed = _parse_pdf_with_unstructured(file_path)
    if parsed.segments:
        return parsed

    segments: list[ParsedSegment] = []
    for page_number, page_text in parse_pdf(file_path):
        blocks = [block.strip() for block in page_text.split("\n\n") if block.strip()]
        for index, block in enumerate(blocks, start=1):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            heading = lines[0][:255]
            content = " ".join(lines)
            segments.append(
                ParsedSegment(
                    block_id=f"pdf-fallback-{page_number}-{index}",
                    heading=heading,
                    content=content,
                    anchor={"page": page_number, "section": heading, "line_start": index, "line_end": index},
                    block_type="paragraph",
                )
            )
    return ParsedDocument(parser_name="pymupdf", parser_version="v3", segments=segments)


def _parse_pdf_with_docling(file_path: str) -> ParsedDocument:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

    try:
        result = DocumentConverter().convert(file_path)
    except Exception:
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

    markdown = result.document.export_to_markdown()
    blocks = [block.strip() for block in markdown.split("\n\n") if block.strip()]
    segments = [
        ParsedSegment(
            block_id=f"docling-pdf-{index}",
            heading=block.splitlines()[0][:255],
            content=" ".join(line.strip() for line in block.splitlines() if line.strip()),
            anchor={"page": 1, "section": block.splitlines()[0][:255], "line_start": index, "line_end": index},
            block_type="paragraph",
        )
        for index, block in enumerate(blocks, start=1)
        if block.splitlines()
    ]
    return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=segments)


def _parse_pdf_with_unstructured(file_path: str) -> ParsedDocument:
    try:
        from unstructured.partition.pdf import partition_pdf
    except ImportError:
        return ParsedDocument(parser_name="unstructured_pdf", parser_version="v3", segments=[])

    try:
        elements = partition_pdf(filename=file_path, strategy="fast")
    except Exception:
        return ParsedDocument(parser_name="unstructured_pdf", parser_version="v3", segments=[])

    segments: list[ParsedSegment] = []
    for index, element in enumerate(elements, start=1):
        text = getattr(element, "text", "").strip()
        if not text:
            continue
        metadata = getattr(element, "metadata", None)
        page_number = getattr(metadata, "page_number", None) if metadata else None
        heading = text.splitlines()[0][:255]
        anchor: dict[str, str | int] = {"section": heading, "line_start": index, "line_end": index}
        if page_number is not None:
            anchor["page"] = int(page_number)
        segments.append(
            ParsedSegment(
                block_id=f"pdf-unstructured-{index}",
                heading=heading,
                content=text,
                anchor=anchor,
                block_type=getattr(element, "category", element.__class__.__name__).lower(),
            )
        )
    return ParsedDocument(parser_name="unstructured_pdf", parser_version="v3", segments=segments)
