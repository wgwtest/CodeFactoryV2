from __future__ import annotations


class ChapterConfigurationContextBuilder:
    def build(
        self,
        *,
        template_id: str,
        spec_tree: list[dict],
        working_document: dict | None = None,
        template_revision_policy: str = "configuration_only",
    ) -> dict:
        sections: list[dict] = []
        clauses: list[dict] = []
        canonical_clause_map: dict[str, dict] = {}
        root = spec_tree[0] if spec_tree else {}
        for section in list(root.get("children", [])):
            if not isinstance(section, dict):
                continue
            section_id = self._section_id(section)
            section_title = str(section.get("title") or section.get("target_section") or section_id).strip()
            sections.append(
                {
                    "template_section_id": section_id,
                    "title": section_title,
                    "node_id": str(section.get("node_id") or ""),
                    "target_section": str(section.get("target_section") or section_title),
                }
            )
            for clause in list(section.get("children", [])):
                if not isinstance(clause, dict):
                    continue
                clause_id = self._clause_id(clause)
                if not clause_id:
                    continue
                clause_title = self._clause_title(clause)
                heading = self._canonical_heading(clause_id=clause_id, clause_title=clause_title)
                clause_payload = {
                    "template_clause_id": clause_id,
                    "section_id": section_id,
                    "node_id": str(clause.get("node_id") or ""),
                    "title": clause_title,
                    "heading": heading,
                    "display_heading": heading,
                    "target_section": str(clause.get("target_section") or ""),
                    "anchor_path": clause_id,
                    "allowed_anchor_actions": [
                        "append_existing_clause",
                        "revise_existing_anchor",
                        "create_subtopic_under_clause",
                    ],
                }
                clauses.append(clause_payload)
                canonical_clause_map[clause_id] = dict(clause_payload)

        return {
            "object_type": "ChapterConfigurationContext",
            "template_id": template_id,
            "template_sections": sections,
            "template_clauses": clauses,
            "canonical_clause_map": canonical_clause_map,
            "allowed_extension_profiles": {
                clause["template_clause_id"]: {
                    "allow_subtopic": True,
                    "allowed_subtopic_actions": ["none", "create", "reuse_existing"],
                }
                for clause in clauses
            },
            "existing_subtopics": self._existing_subtopics(working_document or {}),
            "numbering_policy": {
                "anchor_identity": "template_clause_id",
                "display_heading_source": "target_anchor_plan.display_heading",
                "subtopic_key_source": "target_anchor_plan.subtopic_key",
            },
            "forbidden_actions": [
                "invent_new_template_clause",
                "invent_new_section_number",
                "rebind_patch_by_python_guess",
            ],
            "template_shape_policy": {
                "allowed_shape_types": [
                    "fine_grained_fixed",
                    "fine_grained_extensible",
                    "coarse_grained_extensible",
                    "coarse_grained_fixed",
                    "editable_template",
                ],
                "default_shape_type": "coarse_grained_extensible",
            },
            "template_revision_policy": template_revision_policy,
        }

    @staticmethod
    def _section_id(section: dict) -> str:
        node_id = str(section.get("node_id") or "")
        if node_id.startswith("SPEC-SEC-"):
            return node_id.removeprefix("SPEC-SEC-")
        title = str(section.get("title") or "")
        first = title.split(" ", 1)[0].strip()
        return first or node_id

    @staticmethod
    def _clause_id(clause: dict) -> str:
        node_id = str(clause.get("node_id") or "")
        if node_id.startswith("SPEC-"):
            return node_id.removeprefix("SPEC-")
        title = str(clause.get("title") or "")
        return title.split(" ", 1)[0].strip()

    @staticmethod
    def _clause_title(clause: dict) -> str:
        target_section = str(clause.get("target_section") or "").strip()
        if "/" in target_section:
            return target_section.split("/")[-1].strip()
        title = str(clause.get("title") or "").strip()
        parts = title.split(" ", 1)
        return parts[1].strip() if len(parts) > 1 else title

    @staticmethod
    def _canonical_heading(*, clause_id: str, clause_title: str) -> str:
        number = clause_id.removeprefix("REQ-")
        return f"{number} {clause_title}".strip()

    @staticmethod
    def _existing_subtopics(working_document: dict) -> dict[str, list[dict]]:
        subtopics: dict[str, list[dict]] = {}
        for block in list(working_document.get("blocks", [])):
            if not isinstance(block, dict):
                continue
            plan_ref = str(block.get("plan_ref") or "").strip()
            anchor_path = str(block.get("anchor_path") or "").strip()
            if "::" not in anchor_path:
                continue
            clause_id, subtopic_key = anchor_path.split("::", 1)
            subtopics.setdefault(clause_id, []).append(
                {
                    "subtopic_key": subtopic_key,
                    "display_heading": str(block.get("display_heading") or subtopic_key),
                    "anchor_path": anchor_path,
                    "source_plan_ref": plan_ref,
                }
            )
        return subtopics
