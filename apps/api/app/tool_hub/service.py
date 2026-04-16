from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.fixtures import (
    CATEGORY_CATALOG,
    INPUT_TYPE_CATALOG,
    OUTPUT_TYPE_CATALOG,
    STAGE_CATALOG,
    SUPPORTED_SOURCE_CATALOG,
    TAG_NAMESPACE_CATALOG,
    VERIFICATION_STATUS_CATALOG,
    demo_tools,
)
from app.tool_hub.models import (
    EvolutionRun,
    EvolutionRunReadEnvelope,
    ToolDefinition,
    ToolDefinitionWrite,
    ToolHubCatalogs,
    ToolHubOverviewReadEnvelope,
    ToolHubStateSnapshot,
    ToolListReadEnvelope,
    ToolMatchCandidate,
    ToolMatchRequest,
    ToolMatchRun,
    now_iso,
)
from app.tool_hub.repository import ToolHubRepository
from app.tool_hub.snapshot import (
    build_evolution_run,
    build_tool_hub_snapshot,
    project_evolution_runs,
    project_tool_hub_overview,
    project_tool_list,
)


class ToolHubService:
    def __init__(
        self,
        root: str | Path,
        archive_service: ArchiveKnowledgeService,
        seed_demo_data: bool = True,
    ) -> None:
        self.repository = ToolHubRepository(root)
        self.archive_service = archive_service
        self.seed_demo_data = seed_demo_data
        self._ensure_demo_data()

    def get_snapshot(self) -> ToolHubStateSnapshot:
        self._ensure_demo_data()
        return build_tool_hub_snapshot(
            catalogs=self.get_catalogs(),
            tools=self.repository.list_tools(),
            match_runs=self.repository.list_match_runs(),
            evolution_runs=self.repository.list_evolution_runs(),
        )

    def get_overview(self) -> ToolHubOverviewReadEnvelope:
        snapshot = self.get_snapshot()
        return ToolHubOverviewReadEnvelope(
            meta=snapshot.meta,
            data=project_tool_hub_overview(snapshot),
        )

    def get_catalogs(self) -> ToolHubCatalogs:
        return ToolHubCatalogs(
            categories=CATEGORY_CATALOG,
            stages=STAGE_CATALOG,
            input_types=INPUT_TYPE_CATALOG,
            output_types=OUTPUT_TYPE_CATALOG,
            supported_sources=SUPPORTED_SOURCE_CATALOG,
            verification_statuses=VERIFICATION_STATUS_CATALOG,
            tag_namespaces=TAG_NAMESPACE_CATALOG,
        )

    def list_tools(self) -> ToolListReadEnvelope:
        snapshot = self.get_snapshot()
        return ToolListReadEnvelope(
            meta=snapshot.meta,
            data=project_tool_list(snapshot),
        )

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        self._ensure_demo_data()
        return self.repository.get_tool(tool_id)

    def create_tool(self, payload: ToolDefinitionWrite) -> ToolDefinition:
        self._ensure_demo_data()
        self._ensure_slug_unique(payload.slug)
        tool = ToolDefinition(
            tool_id=f"tool-{uuid4().hex[:12]}",
            **payload.model_dump(mode="json"),
        )
        return self.repository.save_tool(tool)

    def update_tool(self, tool_id: str, payload: ToolDefinitionWrite) -> ToolDefinition | None:
        existing = self.repository.get_tool(tool_id)
        if existing is None:
            return None
        self._ensure_slug_unique(payload.slug, ignore_tool_id=tool_id)
        updated = ToolDefinition.model_validate(
            {
                **existing.model_dump(mode="json"),
                **payload.model_dump(mode="json"),
                "tool_id": tool_id,
                "created_at": existing.created_at,
                "updated_at": now_iso(),
            }
        )
        return self.repository.save_tool(updated)

    def run_match(self, request: ToolMatchRequest) -> ToolMatchRun:
        self._ensure_demo_data()
        candidates = [
            self._score_tool(tool, request)
            for tool in self.repository.list_tools()
            if tool.status == "active"
        ]
        sorted_candidates = sorted(
            candidates,
            key=lambda item: (item.match_score, item.verification_status == "verified"),
            reverse=True,
        )
        run = ToolMatchRun(
            run_id=f"match-{uuid4().hex[:12]}",
            request=request,
            candidates=sorted_candidates,
            context_summary=self._build_context_summary(request),
        )
        return self.repository.save_match_run(run)

    def list_evolution_runs(self) -> EvolutionRunReadEnvelope:
        snapshot = self.get_snapshot()
        return EvolutionRunReadEnvelope(
            meta=snapshot.meta,
            data=project_evolution_runs(snapshot),
        )

    def run_evolution(self) -> EvolutionRun:
        self._ensure_demo_data()
        run = build_evolution_run(self.repository.list_tools())
        return self.repository.save_evolution_run(run)

    def _build_context_summary(self, request: ToolMatchRequest) -> str:
        archive_id = request.knowledge_context.archive_id
        if not archive_id:
            return "未关联知识库上下文，按人工输入进行匹配。"
        summary = self.archive_service.get_summary(archive_id)
        return (
            f"关联知识库 {archive_id}，当前发布态包含 "
            f"{summary['entity_count']} 个实体、{summary['process_count']} 个流程。"
        )

    def _score_tool(self, tool: ToolDefinition, request: ToolMatchRequest) -> ToolMatchCandidate:
        score = 0
        matched_dimensions: list[str] = []
        reasons: list[str] = []
        gaps: list[str] = []

        if request.target_stage:
            if request.target_stage in tool.applicable_stages:
                score += 30
                matched_dimensions.append("stage")
                reasons.append(f"覆盖目标阶段：{request.target_stage}")
            else:
                gaps.append(f"未覆盖目标阶段：{request.target_stage}")

        input_hits = sorted(set(request.required_input_types).intersection(tool.input_types))
        if request.required_input_types:
            if input_hits:
                score += round(25 * len(input_hits) / len(request.required_input_types))
                matched_dimensions.append("input_type")
                reasons.append(f"命中输入类型：{', '.join(input_hits)}")
            else:
                gaps.append("未命中输入类型要求")

        output_hits = sorted(set(request.expected_output_types).intersection(tool.output_types))
        if request.expected_output_types:
            if output_hits:
                score += round(20 * len(output_hits) / len(request.expected_output_types))
                matched_dimensions.append("output_type")
                reasons.append(f"命中输出类型：{', '.join(output_hits)}")
            else:
                gaps.append("未命中输出类型要求")

        tag_hits = sorted(set(request.preferred_tags).intersection(tool.tags))
        if request.preferred_tags:
            if tag_hits:
                score += round(15 * len(tag_hits) / len(request.preferred_tags))
                matched_dimensions.append("tags")
                reasons.append(f"命中偏好标签：{', '.join(tag_hits)}")
            else:
                gaps.append("未命中偏好标签")

        keyword_hits = [keyword for keyword in tool.keywords if keyword and keyword in request.scenario_text]
        if request.scenario_text:
            if keyword_hits:
                score += min(10, len(keyword_hits) * 5)
                matched_dimensions.append("keywords")
                reasons.append(f"命中场景关键词：{', '.join(keyword_hits)}")
            else:
                gaps.append("场景文本未命中工具关键词")

        if tool.verification.status == "verified":
            reasons.append("工具已完成基线验证")
        elif tool.verification.status == "warning":
            gaps.append("工具仍需人工复核")
        elif tool.verification.status == "failed":
            gaps.append("工具最近一次验证失败")

        return ToolMatchCandidate(
            tool_id=tool.tool_id,
            name=tool.name,
            match_score=min(score, 100),
            matched_dimensions=matched_dimensions,
            reasons=reasons,
            gaps=gaps,
            verification_status=tool.verification.status,
        )

    def _ensure_demo_data(self) -> None:
        if not self.seed_demo_data:
            return
        if self.repository.list_tools():
            return
        for tool in demo_tools():
            self.repository.save_tool(tool)

    def _ensure_slug_unique(self, slug: str, ignore_tool_id: str | None = None) -> None:
        for tool in self.repository.list_tools():
            if tool.slug == slug and tool.tool_id != ignore_tool_id:
                raise ValueError("Tool slug already exists")
