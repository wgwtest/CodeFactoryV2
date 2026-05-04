from __future__ import annotations


class ClauseSchemaService:
    def clause_ids(self, sections: list[dict]) -> set[str]:
        return {
            str(clause.get("clause_id"))
            for section in sections
            for clause in section.get("clauses", [])
            if clause.get("clause_id")
        }

