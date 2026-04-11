from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedSegment:
    heading: str
    content: str
    anchor: dict[str, int | str]


class ParsingService:
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
