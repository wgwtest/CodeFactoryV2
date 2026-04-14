from app.extraction.chunking import build_document_chunks
from app.parsing.models import ParsedSegment


def test_build_document_chunks_keeps_heading_groups_and_table_rows_separate() -> None:
    segments = [
        ParsedSegment(
            heading="1 总体",
            content="A" * 1200,
            anchor={"page": 1, "section": "1 总体", "line_start": 1, "line_end": 12},
            block_type="paragraph",
        ),
        ParsedSegment(
            heading="1 总体",
            content="B" * 1200,
            anchor={"page": 1, "section": "1 总体", "line_start": 13, "line_end": 24},
            block_type="paragraph",
        ),
        ParsedSegment(
            heading="交换表",
            content="| A | B |",
            anchor={"page": 2, "section": "交换表", "line_start": 1, "line_end": 1},
            block_type="table_row",
        ),
    ]

    chunks = build_document_chunks(segments, max_chars=1800)

    assert len(chunks) == 3
    assert chunks[0].heading == "1 总体"
    assert chunks[0].char_count == 1200
    assert chunks[1].heading == "1 总体"
    assert chunks[2].heading == "交换表"
    assert chunks[2].block_types == ["table_row"]


def test_build_document_chunks_groups_body_segments_under_last_semantic_heading() -> None:
    segments = [
        ParsedSegment(
            heading="Chapter 1 Mission Overview",
            content="Chapter 1 Mission Overview",
            anchor={"page": 1, "section": "Chapter 1", "line_start": 1, "line_end": 1},
            block_type="paragraph",
        ),
        ParsedSegment(
            heading="FM 6-02 describes the Signal Regiment support to the Army mission and commander decisions",
            content="FM 6-02 describes the Signal Regiment support to the Army mission and commander decisions." * 8,
            anchor={"page": 1, "section": "Chapter 1", "line_start": 2, "line_end": 6},
            block_type="paragraph",
        ),
        ParsedSegment(
            heading="The signal regiment maintains a redundant secure network across the force",
            content="The signal regiment maintains a redundant secure network across the force." * 8,
            anchor={"page": 1, "section": "Chapter 1", "line_start": 7, "line_end": 11},
            block_type="paragraph",
        ),
    ]

    chunks = build_document_chunks(segments, max_chars=4000)

    assert len(chunks) == 1
    assert chunks[0].heading == "Chapter 1 Mission Overview"
    assert len(chunks[0].segments) == 3
