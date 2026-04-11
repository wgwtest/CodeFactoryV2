from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


def parse_docx(file_path: str) -> list[str]:
    converter = _build_docling_converter()
    if converter is not None:
        lines = _parse_docx_with_docling(file_path, converter)
        if lines:
            return lines

    return _parse_docx_with_python_docx(file_path)


@lru_cache(maxsize=1)
def _build_docling_converter():
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return None

    return DocumentConverter()


def _parse_docx_with_docling(file_path: str, converter) -> list[str]:
    try:
        result = converter.convert(file_path)
    except Exception:
        return []

    markdown = result.document.export_to_markdown()
    return [line.rstrip() for line in markdown.splitlines() if line.strip()]


def _parse_docx_with_python_docx(file_path: str) -> list[str]:
    document = Document(file_path)
    lines: list[str] = []

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                lines.append(text)
            continue

        lines.extend(_table_to_lines(block))

    return lines


def _table_to_lines(table: Table) -> list[str]:
    lines: list[str] = []
    for row in table.rows:
        cells = [_cell_to_text(cell) for cell in row.cells]
        if any(cells):
            lines.append(f"| {' | '.join(cells)} |")
    return lines


def _cell_to_text(cell: _Cell) -> str:
    parts: list[str] = []
    for block in _iter_block_items(cell):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                parts.append(text)
            continue

        parts.extend(_table_to_lines(block))
    return ' '.join(parts).strip()


def _iter_block_items(parent: DocxDocument | _Cell) -> Iterator[Paragraph | Table]:
    if isinstance(parent, DocxDocument):
        parent_element = parent.element.body
    else:
        parent_element = parent._tc

    for child in parent_element.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)
