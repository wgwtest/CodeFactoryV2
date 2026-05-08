from __future__ import annotations

import re


class MarkdownTemplateParser:
    """Parse Lab Markdown template instances into runtime section and clause structure."""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    NUMBERED_HEADING_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+?)\s*$")

    def parse(self, content: str) -> dict:
        sections: list[dict] = []
        diagnostics: list[dict] = []
        current_section: dict | None = None
        seen_clause_ids: set[str] = set()

        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            match = self.HEADING_PATTERN.match(raw_line.strip())
            if match is None:
                continue
            level = len(match.group(1))
            heading = match.group(2).strip()
            if level == 1:
                continue
            numbered = self.NUMBERED_HEADING_PATTERN.match(heading)
            if numbered is None:
                if level > 1:
                    diagnostics.append(
                        {
                            "severity": "info",
                            "code": "unnumbered_heading_ignored",
                            "line": line_number,
                            "heading": heading,
                        }
                    )
                continue
            number = numbered.group(1).strip()
            title = numbered.group(2).strip()

            if level == 2 or "." not in number:
                section = {
                    "section_id": number.split(".", 1)[0],
                    "title": f"{number} {title}",
                    "heading": f"{number} {title}",
                    "heading_level": level,
                    "source_heading": raw_line.strip(),
                    "clauses": [],
                }
                sections.append(section)
                current_section = section
                continue

            if current_section is None:
                section_id = number.split(".", 1)[0]
                current_section = {
                    "section_id": section_id,
                    "title": section_id,
                    "heading": section_id,
                    "heading_level": 2,
                    "source_heading": "",
                    "clauses": [],
                }
                sections.append(current_section)
                diagnostics.append(
                    {
                        "severity": "warning",
                        "code": "clause_without_section",
                        "line": line_number,
                        "heading": heading,
                    }
                )

            clause_id = f"REQ-{number}"
            if clause_id in seen_clause_ids:
                diagnostics.append(
                    {
                        "severity": "error",
                        "code": "duplicate_clause_id",
                        "line": line_number,
                        "clause_id": clause_id,
                        "heading": heading,
                    }
                )
                continue
            seen_clause_ids.add(clause_id)
            current_section["clauses"].append(
                {
                    "clause_id": clause_id,
                    "title": title,
                    "heading": f"{number} {title}",
                    "heading_level": level,
                    "source_heading": raw_line.strip(),
                }
            )

        for section in sections:
            if section["clauses"]:
                continue
            section_id = str(section["section_id"])
            clause_id = f"REQ-{section_id}"
            section["clauses"].append(
                {
                    "clause_id": clause_id,
                    "title": str(section["title"]).split(" ", 1)[-1],
                    "heading": str(section["title"]),
                    "heading_level": int(section.get("heading_level") or 2),
                    "source_heading": str(section.get("source_heading") or ""),
                    "synthetic": True,
                }
            )
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "section_as_clause",
                    "section_id": section_id,
                }
            )

        if not sections or not any(section.get("clauses") for section in sections):
            diagnostics.append(
                {
                    "severity": "error",
                    "code": "no_parseable_template_structure",
                    "message": "模板 Markdown 未解析出有效章节或条款。",
                }
            )

        return {"sections": sections, "parse_diagnostics": diagnostics}
