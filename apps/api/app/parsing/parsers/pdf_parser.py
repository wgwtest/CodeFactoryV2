from __future__ import annotations

import re
from pathlib import Path

import fitz

from app.config import settings
from app.parsing.models import ParsedDocument, ParsedSegment


def parse_pdf(file_path: str) -> list[tuple[int, str]]:
    document = fitz.open(file_path)
    return [(page.number + 1, page.get_text("text")) for page in document]


def parse_pdf_segments(file_path: str, *, formal_extraction_mode: bool = False) -> ParsedDocument:
    if formal_extraction_mode or settings.docling_pdf_enabled:
        parsed = _parse_pdf_with_docling(file_path)
        if parsed.segments:
            return parsed
        if formal_extraction_mode:
            raise ValueError(f"正式知识库抽取要求 PDF 使用 Docling 解析，但当前文件未能通过 Docling 成功解析：{file_path}")

    parsed = _parse_pdf_with_unstructured(file_path)
    if parsed.segments:
        return parsed
    if formal_extraction_mode:
        raise ValueError(f"正式知识库抽取禁止 PDF 解析降级到非 Docling 解析器：{file_path}")

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
    for parser in (_parse_pdf_with_docling_backend, _parse_pdf_with_docling_converter):
        parsed = parser(file_path)
        if parsed.segments:
            return parsed
    return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])


def _parse_pdf_with_docling_converter(file_path: str) -> ParsedDocument:
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


def _parse_pdf_with_docling_backend(file_path: str) -> ParsedDocument:
    try:
        from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.document import InputDocument
        from docling.datamodel.settings import DocumentLimits
    except ImportError:
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

    backend = None
    try:
        input_document = InputDocument(
            path_or_stream=Path(file_path),
            format=InputFormat.PDF,
            backend=DoclingParseDocumentBackend,
            limits=DocumentLimits(),
        )
        if not input_document.valid:
            return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])

        backend = input_document._backend
        segments: list[ParsedSegment] = []
        for page_index in range(input_document.page_count):
            page_backend = backend.load_page(page_index)
            try:
                lines = _build_docling_page_lines(page_backend)
            finally:
                page_backend.unload()
            if not lines:
                continue
            segments.extend(_build_docling_segments_from_lines(lines, page_number=page_index + 1))

        return ParsedDocument(
            parser_name="docling_pdf",
            parser_version="v3",
            segments=segments,
            metadata={"docling_mode": "parse_backend", "page_count": input_document.page_count},
        )
    except Exception:
        return ParsedDocument(parser_name="docling_pdf", parser_version="v3", segments=[])
    finally:
        if backend is not None:
            backend.unload()


def _build_docling_page_lines(page_backend) -> list[dict[str, float | int | str]]:
    cells: list[dict[str, float | str]] = []
    for cell in page_backend.get_text_cells():
        text = _normalize_docling_text(getattr(cell, "text", ""))
        if not text:
            continue
        rect = getattr(cell, "rect", None)
        xs = [getattr(rect, attr, 0.0) for attr in ("r_x0", "r_x1", "r_x2", "r_x3")]
        ys = [getattr(rect, attr, 0.0) for attr in ("r_y0", "r_y1", "r_y2", "r_y3")]
        cells.append(
            {
                "text": text,
                "left": min(xs),
                "top": min(ys),
                "bottom": max(ys),
                "height": max(max(ys) - min(ys), 1.0),
            }
        )

    cells.sort(key=lambda item: (round(float(item["top"]), 1), float(item["left"])))

    lines: list[dict[str, float | int | str]] = []
    current_cells: list[dict[str, float | str]] = []

    def flush_line() -> None:
        if not current_cells:
            return
        ordered = sorted(current_cells, key=lambda item: float(item["left"]))
        line_text = _merge_docling_line_fragments([str(item["text"]) for item in ordered])
        if not line_text:
            current_cells.clear()
            return
        lines.append(
            {
                "text": line_text,
                "top": min(float(item["top"]) for item in ordered),
                "bottom": max(float(item["bottom"]) for item in ordered),
                "height": max(float(item["height"]) for item in ordered),
            }
        )
        current_cells.clear()

    for cell in cells:
        if not current_cells:
            current_cells.append(cell)
            continue
        current_top = float(current_cells[0]["top"])
        if abs(float(cell["top"]) - current_top) <= 2.5:
            current_cells.append(cell)
            continue
        flush_line()
        current_cells.append(cell)

    flush_line()
    return lines


def _build_docling_segments_from_lines(
    lines: list[dict[str, float | int | str]], *, page_number: int, max_chars: int = 1200
) -> list[ParsedSegment]:
    segments: list[ParsedSegment] = []
    current_lines: list[dict[str, float | int | str]] = []
    current_chars = 0
    previous_bottom: float | None = None

    def flush_segment() -> None:
        nonlocal current_chars
        if not current_lines:
            return
        start_line = len(segments) + 1
        heading = str(current_lines[0]["text"])[:255]
        content = "\n".join(str(line["text"]) for line in current_lines)
        segments.append(
            ParsedSegment(
                block_id=f"docling-pdf-{page_number}-{start_line}",
                heading=heading,
                content=content,
                anchor={
                    "page": page_number,
                    "section": heading,
                    "line_start": start_line,
                    "line_end": start_line + len(current_lines) - 1,
                },
                block_type="paragraph",
            )
        )
        current_lines.clear()
        current_chars = 0

    for line in lines:
        text = str(line["text"])
        line_top = float(line["top"])
        line_bottom = float(line["bottom"])
        line_height = max(float(line["height"]), 1.0)
        gap = line_top - previous_bottom if previous_bottom is not None else 0.0
        should_flush = bool(current_lines) and (
            current_chars + len(text) > max_chars
            or gap > max(12.0, line_height * 1.5)
            or (_looks_like_heading(text) and current_chars >= 400)
        )
        if should_flush:
            flush_segment()
        current_lines.append(line)
        current_chars += len(text) + 1
        previous_bottom = line_bottom

    flush_segment()
    return segments


def _looks_like_heading(text: str) -> bool:
    normalized = text.strip()
    if not normalized or len(normalized) > 96:
        return False
    alnum_count = sum(1 for char in normalized if char.isalnum())
    uppercase_count = sum(1 for char in normalized if char.isupper())
    if normalized.endswith(":"):
        return True
    return alnum_count > 0 and uppercase_count >= max(4, int(alnum_count * 0.6))


def _merge_docling_line_fragments(parts: list[str]) -> str:
    text = " ".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([(\[{])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]}])", r"\1", text)
    return _collapse_spaced_letters(text)


def _normalize_docling_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()


def _collapse_spaced_letters(text: str) -> str:
    return re.sub(
        r"(?:\b[A-Za-z]\b(?:\s+|$)){4,}",
        lambda match: "".join(match.group(0).split()),
        text,
    )


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
