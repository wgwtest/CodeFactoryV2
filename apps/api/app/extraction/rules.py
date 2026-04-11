from __future__ import annotations

from dataclasses import dataclass

from app.parsing.service import ParsedSegment


@dataclass
class ExtractedCandidate:
    item_type: str
    canonical_name: str
    status: str
    confidence: float
    payload: dict


def extract_candidates(segments: list[ParsedSegment]) -> list[ExtractedCandidate]:
    candidates: list[ExtractedCandidate] = []

    for segment in segments:
        content = segment.content.lower()

        if "incident report" in content:
            candidates.append(
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Incident Report",
                    status="extracted",
                    confidence=0.92,
                    payload={"evidence": segment.anchor},
                )
            )

        if "duty officer" in content:
            candidates.append(
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Duty Officer",
                    status="extracted",
                    confidence=0.88,
                    payload={"evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="event",
                    canonical_name="Submit Incident Report",
                    status="extracted",
                    confidence=0.91,
                    payload={"trigger": "report submission", "evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="rule",
                    canonical_name="Submission Within Two Hours",
                    status="extracted",
                    confidence=0.86,
                    payload={"expression": "submit <= 2h", "evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="process",
                    canonical_name="Incident Closure Review",
                    status="extracted",
                    confidence=0.75,
                    payload={"steps": ["submit", "verify evidence", "approve closure"], "evidence": segment.anchor},
                )
            )

    return candidates
