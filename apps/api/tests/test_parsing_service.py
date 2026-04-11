from pathlib import Path

from app.parsing.service import ParsingService


def test_parser_creates_ordered_segments_with_evidence() -> None:
    source = Path("fixtures/reference_scenarios/minimal_policy.txt")
    document_text = source.read_text()

    service = ParsingService()
    segments = service.parse_text("minimal_policy.txt", document_text)

    assert len(segments) == 3
    assert segments[0].heading == "Section 1"
    assert segments[0].anchor == {"page": 1, "section": "Section 1", "line_start": 1, "line_end": 2}
    assert "incident report" in segments[1].content.lower()
