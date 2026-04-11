from app.extraction.service import ExtractionService
from app.parsing.service import ParsedSegment


def test_extractor_emits_entity_event_process_and_rule_candidates() -> None:
    segments = [
        ParsedSegment(
            heading="Section 2",
            content="Every incident report must be submitted within 2 hours by the duty officer.",
            anchor={"page": 1, "section": "Section 2", "line_start": 4, "line_end": 5},
        ),
        ParsedSegment(
            heading="Section 3",
            content="The review board approves closure after evidence verification.",
            anchor={"page": 1, "section": "Section 3", "line_start": 7, "line_end": 8},
        ),
    ]

    candidates = ExtractionService().extract(segments)

    assert {item.item_type for item in candidates} >= {"entity", "event", "process", "rule"}
    assert any(item.canonical_name == "Duty Officer" for item in candidates)
    assert any(item.payload["evidence"]["section"] == "Section 2" for item in candidates)
