from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedSegment:
    heading: str
    content: str
    anchor: dict[str, int | str]
    block_type: str = "section"
    block_id: str | None = None


@dataclass(slots=True)
class ParsedDocument:
    parser_name: str
    parser_version: str
    segments: list[ParsedSegment]
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)
