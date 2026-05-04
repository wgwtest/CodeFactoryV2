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
        patch_sections = [
            str(patch.get("section") or "").strip()
            for patch in model_output.get("document_patch", [])
            if isinstance(patch, dict)
        ]
        for section in patch_sections:
            matched = self.spec_tree_service.find_spec_node_by_target_section(spec_tree, section)
            if matched and matched.get("node_id"):
                projection_id = str(matched["node_id"])
                return SpecProjectionResult(
                    projection_spec_node_id=projection_id,
                    projection_spec_node=self.spec_tree_service.active_spec_node_context(spec_tree, projection_id),
                    affected_spec_nodes=self.affected_spec_nodes(spec_tree=spec_tree, node_ids=[projection_id]),
                    fallback_used=False,
                    reason=f"模型候选 patch 章节匹配完成度树节点：{section}。",
                )
        return SpecProjectionResult(
            projection_spec_node_id=fallback_node_id,
            projection_spec_node=self.spec_tree_service.active_spec_node_context(spec_tree, fallback_node_id),
            affected_spec_nodes=self.affected_spec_nodes(spec_tree=spec_tree, node_ids=[fallback_node_id]),
            fallback_used=True,
            reason="模型候选章节未匹配完成度树，回退到当前活动节点。",
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
