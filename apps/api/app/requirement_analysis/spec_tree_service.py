from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import get_orchestrator_registry
from app.db.models.requirements import RequirementAuthoringTemplate
from app.requirement_authoring.models import default_template_payload


@dataclass(frozen=True)
class SpecTreeUpdateResult:
    spec_tree: list[dict]
    closed_node_ids: list[str]
    active_spec_node_id: str | None
    next_spec_node: dict

    def to_dict(self) -> dict:
        return {
            "spec_tree": self.spec_tree,
            "closed_node_ids": self.closed_node_ids,
            "active_spec_node_id": self.active_spec_node_id,
            "next_spec_node": self.next_spec_node,
        }


class RequirementSpecTreeService:
    def __init__(self, session) -> None:
        self.session = session

    def new_spec_tree(self, template_id: str = "81433号", *, orchestrator_id: str) -> list[dict]:
        template_payload = self.resolve_template_payload(template_id)
        template_code = self.template_code_from_id(template_id)
        spec_strategy = self.spec_strategy(orchestrator_id)
        root = {
            "node_id": "SPEC-ROOT",
            "title": f"需求规格说明完成度树（{template_code}号）",
            "target_section": f"{template_code}号 需求规格说明",
            "node_type": "template",
            "question": str(spec_strategy.get("root_question") or "按需求规格模板补齐可写入正文的目标节点。"),
            "status": "open",
            "answer_summary": "",
            "completion_reason": "",
            "children": [],
        }
        for section in template_payload.get("sections", []):
            section_id = str(section.get("section_id") or "").strip()
            section_title = str(section.get("title") or section_id).strip()
            section_node = {
                "node_id": f"SPEC-SEC-{section_id}",
                "title": section_title,
                "target_section": section_title,
                "node_type": "section",
                "question": self.section_question(spec_strategy, section_title=section_title),
                "status": "open",
                "answer_summary": "",
                "completion_reason": "",
                "children": [],
            }
            for clause in section.get("clauses", []):
                clause_id = str(clause.get("clause_id") or "").strip()
                clause_title = str(clause.get("title") or clause_id).strip()
                if not clause_id:
                    continue
                section_node["children"].append(
                    {
                        "node_id": f"SPEC-{clause_id}",
                        "title": f"{clause_id} {clause_title}",
                        "target_section": f"{section_title} / {clause_title}",
                        "node_type": "clause",
                        "question": self.clause_question(
                            spec_strategy,
                            clause_id=clause_id,
                            clause_title=clause_title,
                        ),
                        "status": "open",
                        "answer_summary": "",
                        "completion_reason": "",
                        "children": [],
                    }
                )
            root["children"].append(section_node)
        self.refresh_parent_statuses([root])
        return [root]

    def resolve_template_payload(self, template_id: str) -> dict:
        template = self.session.get(RequirementAuthoringTemplate, template_id)
        if template is not None:
            return dict(template.payload or default_template_payload(template.template_code))
        template_code = self.template_code_from_id(template_id)
        return default_template_payload(template_code)

    @staticmethod
    def template_code_from_id(template_id: str) -> str:
        digits = "".join(char for char in template_id if char.isdigit())
        if digits.startswith("82259"):
            return "82259"
        return "81433"

    @staticmethod
    def spec_strategy(orchestrator_id: str) -> dict:
        loaded = get_orchestrator_registry().require_loaded(orchestrator_id)
        return dict(loaded.spec_strategy or {})

    @staticmethod
    def section_question(spec_strategy: dict, *, section_title: str) -> str:
        template = str(spec_strategy.get("section_question_template") or "补齐{section_title}下的需求规格信息。")
        return template.replace("{section_title}", section_title)

    @staticmethod
    def clause_question(spec_strategy: dict, *, clause_id: str, clause_title: str) -> str:
        clauses = spec_strategy.get("clauses") if isinstance(spec_strategy.get("clauses"), dict) else {}
        defaults = spec_strategy.get("defaults") if isinstance(spec_strategy.get("defaults"), dict) else {}
        clause_rule = clauses.get(clause_id) if isinstance(clauses, dict) else None
        if isinstance(clause_rule, dict) and str(clause_rule.get("question") or "").strip():
            return str(clause_rule["question"])
        template = str(defaults.get("leaf_question_template") or "请补齐{clause_title}。")
        return template.replace("{clause_title}", clause_title)

    def active_spec_node_context(self, spec_tree: list[dict], node_id: str | None) -> dict:
        node = self.find_spec_node(spec_tree, node_id or "") if node_id else None
        if node is None:
            return {
                "node_id": None,
                "title": "已完成",
                "target_section": "整体复核",
                "node_type": "completion",
                "question": "当前需求规格完成度树暂无待确认节点。",
                "path": [],
                "status": "closed",
            }
        return {
            "node_id": node.get("node_id"),
            "title": node.get("title"),
            "target_section": node.get("target_section"),
            "node_type": node.get("node_type") or "clause",
            "question": node.get("question") or node.get("title"),
            "path": self.spec_node_path(spec_tree, str(node.get("node_id"))),
            "status": node.get("status"),
        }

    def spec_node_path(self, nodes: list[dict], node_id: str, current: list[str] | None = None) -> list[str]:
        current = current or []
        for node in nodes:
            next_path = [*current, str(node.get("title") or node.get("node_id"))]
            if node.get("node_id") == node_id:
                return next_path
            child_path = self.spec_node_path(list(node.get("children", [])), node_id, next_path)
            if child_path:
                return child_path
        return []

    def update_spec_tree(self, *, spec_tree: list[dict], active_node_id: str, answer_summary: str, turn_id: str) -> SpecTreeUpdateResult:
        closed_node_ids: list[str] = []
        node = self.find_spec_node(spec_tree, active_node_id)
        if node is not None:
            node["status"] = "closed"
            node["answer_summary"] = answer_summary
            node["completion_reason"] = f"{turn_id} 用户已确认"
            closed_node_ids.append(active_node_id)
        self.refresh_parent_statuses(spec_tree)
        active_spec_node_id = self.first_open_spec_node_id(spec_tree)
        return SpecTreeUpdateResult(
            spec_tree=spec_tree,
            active_spec_node_id=active_spec_node_id,
            closed_node_ids=closed_node_ids,
            next_spec_node=self.active_spec_node_context(spec_tree, active_spec_node_id),
        )

    def find_spec_node(self, nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            child = self.find_spec_node(list(node.get("children", [])), node_id)
            if child is not None:
                return child
        return None

    def find_spec_node_by_target_section(self, nodes: list[dict], target_section: str) -> dict | None:
        for node in nodes:
            if node.get("target_section") == target_section:
                return node
            child = self.find_spec_node_by_target_section(list(node.get("children", [])), target_section)
            if child is not None:
                return child
        return None

    def first_open_spec_node_id(self, nodes: list[dict]) -> str | None:
        for node in nodes:
            children = list(node.get("children", []))
            if children:
                child_id = self.first_open_spec_node_id(children)
                if child_id:
                    return child_id
                continue
            if node.get("status") == "open":
                return str(node.get("node_id"))
        return None

    def refresh_parent_statuses(self, nodes: list[dict]) -> None:
        for node in nodes:
            children = list(node.get("children", []))
            if not children:
                continue
            self.refresh_parent_statuses(children)
            child_statuses = {child.get("status") for child in children}
            if child_statuses == {"closed"}:
                node["status"] = "closed"
            elif "closed" in child_statuses or "partial" in child_statuses:
                node["status"] = "partial"
            else:
                node["status"] = "open"
