from __future__ import annotations

from dataclasses import dataclass

from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService


@dataclass(frozen=True)
class SpecProjectionResult:
    projection_spec_node_id: str
    projection_spec_node: dict
    affected_spec_nodes: list[dict]
    fallback_used: bool
    reason: str


class SpecProjectionService:
    def __init__(self, *, spec_tree_service: RequirementSpecTreeService) -> None:
        self.spec_tree_service = spec_tree_service

    def project(self, *, spec_tree: list[dict], model_output: dict, fallback_node_id: str) -> SpecProjectionResult:
        plan_by_id = {
            str(plan.get("plan_id") or "").strip(): dict(plan)
            for plan in list(model_output.get("target_anchor_plan") or [])
            if isinstance(plan, dict) and str(plan.get("plan_id") or "").strip()
        }
        plan_refs = [
            str(patch.get("plan_ref") or "").strip()
            for patch in model_output.get("document_patch", [])
            if isinstance(patch, dict)
        ]
        projection_ids: list[str] = []
        for plan_ref in plan_refs:
            plan = plan_by_id.get(plan_ref)
            if not plan:
                continue
            clause_id = str(plan.get("template_clause_id") or "").strip()
            node_id = f"SPEC-{clause_id}" if clause_id else ""
            matched = self.spec_tree_service.find_spec_node(spec_tree, node_id)
            if matched and matched.get("node_id") and node_id not in projection_ids:
                projection_ids.append(node_id)
        if projection_ids:
            projection_id = projection_ids[0]
            return SpecProjectionResult(
                projection_spec_node_id=projection_id,
                projection_spec_node=self.spec_tree_service.active_spec_node_context(spec_tree, projection_id),
                affected_spec_nodes=self.affected_spec_nodes(spec_tree=spec_tree, node_ids=projection_ids),
                fallback_used=False,
                reason=f"模型目标锚点规划匹配完成度树节点：{', '.join(projection_ids)}。",
            )
        return SpecProjectionResult(
            projection_spec_node_id=fallback_node_id,
            projection_spec_node=self.spec_tree_service.active_spec_node_context(spec_tree, fallback_node_id),
            affected_spec_nodes=self.affected_spec_nodes(spec_tree=spec_tree, node_ids=[fallback_node_id]),
            fallback_used=True,
            reason="模型目标锚点规划未匹配完成度树，回退到当前活动节点。",
        )

    def affected_spec_nodes(self, *, spec_tree: list[dict], node_ids: list[str]) -> list[dict]:
        affected: list[dict] = []
        for node_id in node_ids:
            node = self.spec_tree_service.find_spec_node(spec_tree, node_id)
            affected.append(
                {
                    "node_id": node_id or None,
                    "title": node.get("title") if node else node_id,
                    "target_section": node.get("target_section") if node else "未绑定模板章节",
                    "effect": "update",
                    "reason": "用户本轮输入形成了该章节的可写入材料。",
                }
            )
        return affected
