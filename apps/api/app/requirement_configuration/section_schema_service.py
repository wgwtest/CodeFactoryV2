from __future__ import annotations


class SectionSchemaService:
    def validate(self, sections: list[dict]) -> list[dict]:
        errors: list[dict] = []
        seen_section_ids: set[str] = set()
        seen_clause_ids: set[str] = set()
        for section in sections:
            section_id = str(section.get("section_id") or "").strip()
            if not section_id:
                errors.append({"field": "sections.section_id", "message": "section_id is required"})
            elif section_id in seen_section_ids:
                errors.append({"field": "sections.section_id", "message": f"duplicate section_id: {section_id}"})
            seen_section_ids.add(section_id)
            for clause in section.get("clauses", []):
                clause_id = str(clause.get("clause_id") or "").strip()
                if not clause_id:
                    errors.append({"field": "sections.clauses.clause_id", "message": "clause_id is required"})
                elif clause_id in seen_clause_ids:
                    errors.append({"field": "sections.clauses.clause_id", "message": f"duplicate clause_id: {clause_id}"})
                seen_clause_ids.add(clause_id)
        return errors

