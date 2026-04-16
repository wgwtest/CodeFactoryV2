from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from app.tool_hub.fixtures import CATEGORY_CATALOG, STAGE_CATALOG
from app.tool_hub.models import (
    CoverageMatrix,
    CoverageMatrixCell,
    CoverageMatrixRow,
    EvolutionFinding,
    EvolutionRun,
    EvolutionRunEnvelope,
    EvolutionRunSummary,
    OverviewMetrics,
    PendingSuggestionItem,
    RecentRunSummary,
    RiskSummaryItem,
    ToolDefinition,
    ToolHubCatalogs,
    ToolHubDerivedState,
    ToolHubOverview,
    ToolHubRawState,
    ToolHubRunMonitor,
    ToolHubSnapshotMeta,
    ToolHubStateSnapshot,
    ToolListEnvelope,
    ToolMatchRun,
    now_iso,
)

STATE_VERSION = "p4-tool-hub-state-v1"
SOURCE_CONTRACT_VERSION = "p4-tool-hub-read-v1"
VIRTUAL_EVOLUTION_RUN_ID = "evolution-virtual"


def build_tool_hub_snapshot(
    *,
    catalogs: ToolHubCatalogs,
    tools: list[ToolDefinition],
    match_runs: list[ToolMatchRun],
    evolution_runs: list[EvolutionRun],
) -> ToolHubStateSnapshot:
    raw = ToolHubRawState(
        catalogs=catalogs,
        tools=tools,
        match_runs=match_runs,
        evolution_runs=evolution_runs,
    )
    current_evolution = evolution_runs[0] if evolution_runs else build_virtual_evolution_run(tools)
    pending_suggestions = build_pending_suggestions(current_evolution)
    derived = ToolHubDerivedState(
        metrics=build_overview_metrics(
            tools=tools,
            match_runs=match_runs,
            evolution_runs=evolution_runs,
            current_evolution=current_evolution,
            pending_suggestions=pending_suggestions,
        ),
        run_monitor=build_run_monitor(match_runs, evolution_runs),
        risk_summary=build_risk_summary(current_evolution),
        coverage_matrix=build_coverage_matrix(catalogs, tools),
        pending_suggestions=pending_suggestions,
    )
    return ToolHubStateSnapshot(
        meta=build_snapshot_meta(raw),
        raw=raw,
        derived=derived,
    )


def project_tool_hub_overview(snapshot: ToolHubStateSnapshot) -> ToolHubOverview:
    return ToolHubOverview(
        metrics=snapshot.derived.metrics,
        run_monitor=snapshot.derived.run_monitor,
        coverage_matrix=snapshot.derived.coverage_matrix,
        risk_summary=snapshot.derived.risk_summary,
        pending_suggestions=snapshot.derived.pending_suggestions,
        recent_match_runs=[summarize_match_run(run) for run in snapshot.raw.match_runs[:5]],
        recent_evolution_runs=[summarize_evolution_run(run) for run in snapshot.raw.evolution_runs[:5]],
        catalogs=snapshot.raw.catalogs,
    )


def project_tool_list(snapshot: ToolHubStateSnapshot) -> ToolListEnvelope:
    return ToolListEnvelope(items=snapshot.raw.tools)


def project_evolution_runs(snapshot: ToolHubStateSnapshot) -> EvolutionRunEnvelope:
    return EvolutionRunEnvelope(items=snapshot.raw.evolution_runs)


def build_evolution_run(tools: list[ToolDefinition]) -> EvolutionRun:
    summary, findings = _analyze_evolution(tools, deterministic=False)
    return EvolutionRun(
        run_id=f"evolution-{uuid4().hex[:12]}",
        summary=summary,
        findings=findings,
    )


def build_virtual_evolution_run(tools: list[ToolDefinition]) -> EvolutionRun:
    summary, findings = _analyze_evolution(tools, deterministic=True)
    return EvolutionRun(
        run_id=VIRTUAL_EVOLUTION_RUN_ID,
        created_at=_latest_or_default_timestamp(tools),
        summary=summary,
        findings=findings,
    )


def build_snapshot_meta(raw: ToolHubRawState) -> ToolHubSnapshotMeta:
    canonical_payload = json.dumps(
        raw.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    snapshot_id = hashlib.sha1(canonical_payload.encode("utf-8")).hexdigest()[:16]
    return ToolHubSnapshotMeta(
        snapshot_id=snapshot_id,
        generated_at=_collect_generated_at(raw),
        state_version=STATE_VERSION,
        source_contract_version=SOURCE_CONTRACT_VERSION,
    )


def build_overview_metrics(
    *,
    tools: list[ToolDefinition],
    match_runs: list[ToolMatchRun],
    evolution_runs: list[EvolutionRun],
    current_evolution: EvolutionRun,
    pending_suggestions: list[PendingSuggestionItem],
) -> OverviewMetrics:
    successful_match_runs = len([run for run in match_runs if run.status == "completed"])
    recent_success_rate = round((successful_match_runs / len(match_runs)) * 100, 1) if match_runs else 0
    return OverviewMetrics(
        tool_count=len(tools),
        verified_tool_count=len([tool for tool in tools if tool.verification.status == "verified"]),
        active_tool_count=len([tool for tool in tools if tool.status == "active"]),
        draft_tool_count=len([tool for tool in tools if tool.status == "draft"]),
        archived_tool_count=len([tool for tool in tools if tool.status == "archived"]),
        match_run_count=len(match_runs),
        evolution_run_count=len(evolution_runs),
        active_chain_count=len(match_runs),
        overlap_candidate_count=current_evolution.summary.overlap_risk_count,
        pending_suggestion_count=len(pending_suggestions),
        recent_success_rate=recent_success_rate,
    )


def build_run_monitor(
    match_runs: list[ToolMatchRun],
    evolution_runs: list[EvolutionRun],
) -> ToolHubRunMonitor:
    return ToolHubRunMonitor(
        active_match_run_count=len([run for run in match_runs if run.status != "completed"]),
        active_evolution_run_count=len([run for run in evolution_runs if run.status != "completed"]),
        latest_match_run=summarize_match_run(match_runs[0]) if match_runs else None,
        latest_evolution_run=summarize_evolution_run(evolution_runs[0]) if evolution_runs else None,
        failing_run_count=0,
        stale_run_count=0,
    )


def build_coverage_matrix(catalogs: ToolHubCatalogs, tools: list[ToolDefinition]) -> CoverageMatrix:
    rows: list[CoverageMatrixRow] = []
    for category in catalogs.categories:
        category_tools = [tool for tool in tools if tool.primary_category_id == category.id and tool.status == "active"]
        rows.append(
            CoverageMatrixRow(
                category_id=category.id,
                category_label=category.label,
                cells=[
                    CoverageMatrixCell(
                        stage_id=stage.id,
                        value=len([tool for tool in category_tools if stage.id in tool.applicable_stages]),
                    )
                    for stage in catalogs.stages
                ],
            )
        )
    return CoverageMatrix(stages=catalogs.stages, rows=rows)


def build_risk_summary(run: EvolutionRun) -> list[RiskSummaryItem]:
    return [
        RiskSummaryItem(
            kind=finding.kind,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
        )
        for finding in run.findings[:6]
    ]


def build_pending_suggestions(run: EvolutionRun) -> list[PendingSuggestionItem]:
    return [
        PendingSuggestionItem(
            finding_id=finding.finding_id,
            source_run_id=run.run_id,
            kind=finding.kind,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            tool_ids=finding.tool_ids,
        )
        for finding in run.findings
    ]


def summarize_match_run(run: ToolMatchRun) -> RecentRunSummary:
    return RecentRunSummary(
        run_id=run.run_id,
        run_type="match",
        title=(run.request.scenario_text or "未命名匹配任务")[:24],
        status=run.status,
        created_at=run.created_at,
        summary=f"{len(run.candidates)} 个候选工具",
    )


def summarize_evolution_run(run: EvolutionRun) -> RecentRunSummary:
    return RecentRunSummary(
        run_id=run.run_id,
        run_type="evolution",
        title="工具池巡检",
        status=run.status,
        created_at=run.created_at,
        summary=f"{run.summary.finding_count} 项发现",
    )


def _analyze_evolution(
    tools: list[ToolDefinition],
    *,
    deterministic: bool,
) -> tuple[EvolutionRunSummary, list[EvolutionFinding]]:
    findings: list[EvolutionFinding] = []
    known_categories = {item.id for item in CATEGORY_CATALOG}
    required_tag_namespaces = ("stage:", "capability:", "input:", "output:")

    for tool in tools:
        if not tool.summary.strip() or not tool.problem_statement.strip():
            findings.append(
                _build_finding(
                    deterministic=deterministic,
                    kind="missing_description",
                    title=f"{tool.name} 描述缺失",
                    description="工具摘要或问题定义为空，影响匹配和验证解释。",
                    severity="warning",
                    tool_ids=[tool.tool_id],
                )
            )
        if tool.primary_category_id not in known_categories or not all(
            any(tag.startswith(prefix) for tag in tool.tags) for prefix in required_tag_namespaces
        ):
            findings.append(
                _build_finding(
                    deterministic=deterministic,
                    kind="taxonomy_issue",
                    title=f"{tool.name} 分类或标签不规范",
                    description="当前工具缺少标准分类或缺失关键命名空间标签。",
                    severity="warning",
                    tool_ids=[tool.tool_id],
                )
            )

    active_tools = [tool for tool in tools if tool.status == "active"]
    for index, current in enumerate(active_tools):
        current_capabilities = {tag for tag in current.tags if tag.startswith("capability:")}
        current_stages = set(current.applicable_stages)
        current_inputs = set(current.input_types)
        for other in active_tools[index + 1 :]:
            overlap_score = 0
            if current_stages.intersection(other.applicable_stages):
                overlap_score += 1
            if current_inputs.intersection(other.input_types):
                overlap_score += 1
            other_capabilities = {tag for tag in other.tags if tag.startswith("capability:")}
            if current_capabilities.intersection(other_capabilities):
                overlap_score += 1
            if overlap_score >= 2:
                findings.append(
                    _build_finding(
                        deterministic=deterministic,
                        kind="overlap_risk",
                        title=f"{current.name} 与 {other.name} 疑似重叠",
                        description="两者在阶段、输入或能力标签上存在高相似度，建议人工评估是否整合。",
                        severity="critical" if overlap_score >= 3 else "warning",
                        tool_ids=[current.tool_id, other.tool_id],
                    )
                )

    for stage in STAGE_CATALOG:
        if not any(stage.id in tool.applicable_stages for tool in active_tools):
            findings.append(
                _build_finding(
                    deterministic=deterministic,
                    kind="coverage_gap",
                    title=f"{stage.label} 阶段覆盖不足",
                    description="当前没有激活工具覆盖该阶段，驾驶舱矩阵存在明显空白。",
                    severity="info",
                    tool_ids=[],
                )
            )

    summary = EvolutionRunSummary(
        tool_count=len(tools),
        finding_count=len(findings),
        missing_description_count=len([item for item in findings if item.kind == "missing_description"]),
        taxonomy_issue_count=len([item for item in findings if item.kind == "taxonomy_issue"]),
        overlap_risk_count=len([item for item in findings if item.kind == "overlap_risk"]),
        coverage_gap_count=len([item for item in findings if item.kind == "coverage_gap"]),
    )
    return summary, findings


def _build_finding(
    *,
    deterministic: bool,
    kind: str,
    title: str,
    description: str,
    severity: str,
    tool_ids: list[str],
) -> EvolutionFinding:
    if deterministic:
        identity_source = "|".join([kind, title, description, severity, *sorted(tool_ids)])
        finding_id = f"finding-{hashlib.sha1(identity_source.encode('utf-8')).hexdigest()[:10]}"
    else:
        finding_id = f"finding-{uuid4().hex[:10]}"
    return EvolutionFinding(
        finding_id=finding_id,
        kind=kind,
        title=title,
        description=description,
        severity=severity,
        tool_ids=tool_ids,
    )


def _collect_generated_at(raw: ToolHubRawState) -> str:
    timestamps = [
        *[item.updated_at for item in raw.tools],
        *[item.created_at for item in raw.match_runs],
        *[item.created_at for item in raw.evolution_runs],
    ]
    if not timestamps:
        return now_iso()
    return max(timestamps, key=_parse_iso_timestamp)


def _latest_or_default_timestamp(tools: list[ToolDefinition]) -> str:
    if not tools:
        return now_iso()
    return max([tool.updated_at for tool in tools], key=_parse_iso_timestamp)


def _parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
