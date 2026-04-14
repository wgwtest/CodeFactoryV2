from __future__ import annotations

from dataclasses import dataclass
import re

from app.parsing.models import ParsedSegment


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    chunk_index: int
    heading: str
    segments: list[ParsedSegment]
    segment_ids: list[str]
    char_count: int
    block_types: list[str]
    anchors: list[dict[str, int | str]]


def build_document_chunks(segments: list[ParsedSegment], *, max_chars: int) -> list[DocumentChunk]:
    if not segments:
        return []

    prepared_segments = _prepare_segments(segments, max_chars=max_chars)
    chunks: list[DocumentChunk] = []
    current_heading = ""
    current_items: list[tuple[str, ParsedSegment]] = []
    current_char_count = 0
    soft_boundary_chars = max(1500, max_chars // 3)

    def flush() -> None:
        nonlocal current_heading, current_items, current_char_count
        if not current_items:
            return
        chunk_index = len(chunks)
        block_types = list(dict.fromkeys(segment.block_type for _, segment in current_items))
        chunks.append(
            DocumentChunk(
                chunk_id=f"chunk-{chunk_index + 1:03d}",
                chunk_index=chunk_index,
                heading=current_heading,
                segments=[segment for _, segment in current_items],
                segment_ids=[segment_id for segment_id, _ in current_items],
                char_count=current_char_count,
                block_types=block_types,
                anchors=[segment.anchor for _, segment in current_items],
            )
        )
        current_heading = ""
        current_items = []
        current_char_count = 0

    for segment_id, segment in prepared_segments:
        heading = _resolve_chunk_heading(segment, current_heading=current_heading)
        segment_chars = len(segment.content)
        is_table_segment = segment.block_type == "table_row"
        is_semantic_heading = _is_semantic_heading(segment)

        if is_table_segment:
            flush()
            current_heading = heading
            current_items = [(segment_id, segment)]
            current_char_count = segment_chars
            flush()
            continue

        if not current_items:
            current_heading = heading
            current_items = [(segment_id, segment)]
            current_char_count = segment_chars
            continue

        reached_soft_boundary = current_char_count >= soft_boundary_chars
        if ((is_semantic_heading and heading != current_heading and reached_soft_boundary) or current_char_count + segment_chars > max_chars):
            flush()
            current_heading = heading
            current_items = [(segment_id, segment)]
            current_char_count = segment_chars
            continue

        current_items.append((segment_id, segment))
        current_char_count += segment_chars

    flush()
    return chunks


def _prepare_segments(segments: list[ParsedSegment], *, max_chars: int) -> list[tuple[str, ParsedSegment]]:
    prepared: list[tuple[str, ParsedSegment]] = []

    for index, segment in enumerate(segments, start=1):
        if len(segment.content) <= max_chars:
            prepared.append((_segment_id(index=index), segment))
            continue

        for fragment_index, content_fragment in enumerate(_split_text(segment.content, max_chars=max_chars), start=1):
            prepared.append(
                (
                    _segment_id(index=index, fragment_index=fragment_index),
                    ParsedSegment(
                        heading=segment.heading,
                        content=content_fragment,
                        anchor=dict(segment.anchor),
                        block_type=segment.block_type,
                        block_id=segment.block_id,
                    ),
                )
            )

    return prepared


def _split_text(content: str, *, max_chars: int) -> list[str]:
    fragments: list[str] = []
    remaining = content.strip()
    while remaining:
        if len(remaining) <= max_chars:
            fragments.append(remaining)
            break
        fragments.append(remaining[:max_chars].strip())
        remaining = remaining[max_chars:].strip()
    return fragments


def _segment_id(*, index: int, fragment_index: int | None = None) -> str:
    if fragment_index is None:
        return f"segment-{index:04d}"
    return f"segment-{index:04d}-{fragment_index:02d}"


def _resolve_chunk_heading(segment: ParsedSegment, *, current_heading: str) -> str:
    raw_heading = segment.heading.strip()
    if segment.block_type == "table_row":
        return raw_heading or current_heading or "未命名分段"
    if _is_semantic_heading(segment):
        return raw_heading or current_heading or "未命名分段"
    return current_heading or raw_heading or "未命名分段"


def _is_semantic_heading(segment: ParsedSegment) -> bool:
    heading = segment.heading.strip()
    if not heading:
        return False
    if segment.block_type == "table_row":
        return False

    normalized_heading = heading.lower()
    if normalized_heading in {"contents", "figures", "tables", "preface", "appendix", "glossary"}:
        return True
    if re.match(r"^(chapter|appendix|section|part)\b", normalized_heading):
        return True
    if re.match(r"^(figure|table)\s+\d", normalized_heading):
        return True
    if re.match(r"^\d+-\d+\.", heading):
        return False
    if normalized_heading.startswith("note."):
        return False
    if len(heading) > 90:
        return False
    if heading.count(".") >= 6:
        return False
    if any(token in heading for token in {",", ";", "?", "!"}):
        return False

    words = re.findall(r"[A-Za-z]+", heading)
    if words:
        lower_words = sum(word.islower() for word in words)
        if len(words) > 9 and lower_words >= len(words) // 2:
            return False

    if re.match(r"^[A-Z0-9][A-Z0-9 /&().:-]{3,}$", heading) and len(re.findall(r"[A-Z]", heading)) >= 4:
        return True
    if re.match(r"^[A-Z][a-z0-9]+(?: [A-Z][a-z0-9]+){0,6}$", heading):
        return True

    return len(heading.split()) <= 6 and not heading.endswith(".")
