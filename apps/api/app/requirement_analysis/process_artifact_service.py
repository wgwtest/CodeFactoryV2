from __future__ import annotations

from app.orchestrators.orchestrator_id_mapper import local_package_id_for_orchestrator
from app.orchestrators.package_loader import get_orchestrator_registry


class ProcessArtifactService:
    def fact_for_node(self, orchestrator_id: str, node: dict | None, semantic: str) -> str:
        return self._render_rule_template(orchestrator_id, node, semantic, template_key="fact_template")

    def patch_for_node(self, orchestrator_id: str, node: dict | None, semantic: str) -> str:
        return self._render_rule_template(orchestrator_id, node, semantic, template_key="patch_template")

    def quick_options_for_node(self, orchestrator_id: str, node: dict | None) -> list[dict]:
        rule = self._rule_for_node(orchestrator_id, node)
        options = rule.get("quick_options") if isinstance(rule, dict) else []
        if not isinstance(options, list):
            return []
        normalized = []
        for option in options:
            if not isinstance(option, dict):
                continue
            key = str(option.get("key") or "").strip()
            label = str(option.get("label") or "").strip()
            if key and label:
                normalized.append({"key": key, "label": label, "recommended": bool(option.get("recommended"))})
        return normalized

    @staticmethod
    def clause_id_from_node(node: dict | None) -> str:
        if not node:
            return ""
        node_id = str(node.get("node_id") or "")
        return node_id.removeprefix("SPEC-")

    def _render_rule_template(self, orchestrator_id: str, node: dict | None, semantic: str, *, template_key: str) -> str:
        rule = self._rule_for_node(orchestrator_id, node)
        template = str(rule.get(template_key) or "{semantic}") if isinstance(rule, dict) else "{semantic}"
        return template.replace("{semantic}", semantic)

    def _rule_for_node(self, orchestrator_id: str, node: dict | None) -> dict:
        loaded = get_orchestrator_registry().require_loaded(local_package_id_for_orchestrator(orchestrator_id))
        rules = dict(loaded.artifact_rules or {})
        clauses = rules.get("clauses") if isinstance(rules.get("clauses"), dict) else {}
        defaults = rules.get("defaults") if isinstance(rules.get("defaults"), dict) else {}
        clause_id = self.clause_id_from_node(node)
        rule = clauses.get(clause_id) if isinstance(clauses, dict) else None
        return dict(rule or defaults or {})
