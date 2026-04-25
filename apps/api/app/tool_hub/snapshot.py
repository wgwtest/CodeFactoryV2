from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from app.tool_hub.fixtures import DOMAIN_CATALOG, TOOL_FORM_CATALOG
from app.tool_hub.models import (
    CoverageMatrix,
    CoverageMatrixCell,
    CoverageMatrixRow,
    EvolutionFinding,
    EvolutionInspectionConfig,
    EvolutionRuntimeState,
    EvolutionTask,
    EvolutionRun,
    EvolutionRunEnvelope,
    EvolutionRunSummary,
    OverviewMetrics,
    PendingSuggestionItem,
    RecentRunSummary,
    RiskSummaryItem,
    ToolDefinition,
    ToolDemandSheet,
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

STATE_VERSION = "p4-tool-hub-state-v2"
SOURCE_CONTRACT_VERSION = "p4-tool-hub-read-v2"
VIRTUAL_EVOLUTION_RUN_ID = "evolution-virtual"


def build_tool_hub_snapshot(
    *,
    catalogs: ToolHubCatalogs,
    tools: list[ToolDefinition],
    demand_sheets: list[ToolDemandSheet],
    match_runs: list[ToolMatchRun],
    evolution_config: EvolutionInspectionConfig,
    evolution_runs: list[EvolutionRun],
    evolution_tasks: list[EvolutionTask],
    runtime_state: EvolutionRuntimeState,
) -> ToolHubStateSnapshot:
    raw = ToolHubRawState(
        catalogs=catalogs,
        tools=tools,
        demand_sheets=demand_sheets,
        match_runs=match_runs,
        evolution_config=evolution_config,
        evolution_runs=evolution_runs,
        evolution_tasks=evolution_tasks,
        runtime_state=runtime_state,
    )
    current_evolution = evolution_runs[0] if evolution_runs else build_virtual_evolution_run(
        tools,
        overlap_threshold=evolution_config.overlap_threshold,
        include_draft_tools=evolution_config.include_draft_tools,
    )
    pending_suggestions = build_pending_suggestions(evolution_runs, current_evolution)
    derived = ToolHubDerivedState(
        metrics=build_overview_metrics(
            tools=tools,
            demand_sheets=demand_sheets,
            match_runs=match_runs,
            evolution_runs=evolution_runs,
            evolution_tasks=evolution_tasks,
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
        recent_demand_sheets=snapshot.raw.demand_sheets[:5],
        recent_match_runs=[summarize_match_run(run) for run in snapshot.raw.match_runs[:5]],
        recent_evolution_runs=[summarize_evolution_run(run) for run in snapshot.raw.evolution_runs[:5]],
        catalogs=snapshot.raw.catalogs,
    )


def project_tool_list(snapshot: ToolHubStateSnapshot) -> ToolListEnvelope:
    return ToolListEnvelope(items=snapshot.raw.tools)


def project_evolution_runs(snapshot: ToolHubStateSnapshot) -> EvolutionRunEnvelope:
    return EvolutionRunEnvelope(items=snapshot.raw.evolution_runs)


def build_evolution_run(
    tools: list[ToolDefinition],
    *,
    overlap_threshold: int = 3,
    include_draft_tools: bool = True,
    trigger_type: str = "manual",
    triggered_by: str = "p4-system",
    snapshot_id: str | None = None,
) -> EvolutionRun:
    run_id = f"evolution-run-{uuid4().hex[:12]}"
    summary, findings = _analyze_evolution(
        tools,
        deterministic=False,
        overlap_threshold=overlap_threshold,
        include_draft_tools=include_draft_tools,
    )
    timestamp = now_iso()
    return EvolutionRun(
        run_id=run_id,
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        snapshot_id=snapshot_id,
        started_at=timestamp,
        completed_at=timestamp,
        updated_at=timestamp,
        summary=summary,
        findings=[finding.model_copy(update={"run_id": run_id, "updated_at": timestamp}) for finding in findings],
    )


def build_virtual_evolution_run(
    tools: list[ToolDefinition],
    *,
    overlap_threshold: int = 3,
    include_draft_tools: bool = True,
) -> EvolutionRun:
    summary, findings = _analyze_evolution(
        tools,
        deterministic=True,
        overlap_threshold=overlap_threshold,
        include_draft_tools=include_draft_tools,
    )
    timestamp = _latest_or_default_timestamp(tools)
    return EvolutionRun(
        run_id=VIRTUAL_EVOLUTION_RUN_ID,
        created_at=timestamp,
        updated_at=timestamp,
        started_at=timestamp,
        completed_at=timestamp,
        summary=summary,
        findings=[
            finding.model_copy(update={"run_id": VIRTUAL_EVOLUTION_RUN_ID, "updated_at": timestamp})
            for finding in findings
        ],
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
    demand_sheets: list[ToolDemandSheet],
    match_runs: list[ToolMatchRun],
    evolution_runs: list[EvolutionRun],
    evolution_tasks: list[EvolutionTask],
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
        active_chain_count=len(
            [
                sheet
                for sheet in demand_sheets
                if sheet.lifecycle_status not in {"rejected", "withdrawn", "closed"}
                and not (sheet.review_status == "reviewed" and sheet.delivery_status == "delivered")
            ]
        ),
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
    for domain in catalogs.domains:
        domain_tools = [tool for tool in tools if tool.primary_domain_id == domain.id and tool.status == "active"]
        rows.append(
            CoverageMatrixRow(
                row_id=domain.id,
                row_label=domain.label,
                cells=[
                    CoverageMatrixCell(
                        column_id=tool_form.id,
                        value=len([tool for tool in domain_tools if tool.tool_form_id == tool_form.id]),
                    )
                    for tool_form in catalogs.tool_forms
                ],
            )
        )
    return CoverageMatrix(
        title="业务域 × 工具形态",
        x_axis_label="工具形态",
        y_axis_label="业务能力域",
        columns=catalogs.tool_forms,
        rows=rows,
    )


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


def build_pending_suggestions(
    evolution_runs: list[EvolutionRun],
    current_run: EvolutionRun,
) -> list[PendingSuggestionItem]:
    pending_findings = [
        finding
        for run in evolution_runs
        for finding in run.findings
        if finding.decision_status == "pending"
    ]
    source_findings = pending_findings or current_run.findings
    return [
        PendingSuggestionItem(
            finding_id=finding.finding_id,
            source_run_id=finding.run_id or current_run.run_id,
            kind=finding.kind,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            tool_ids=finding.tool_ids,
        )
        for finding in source_findings
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
    overlap_threshold: int = 3,
    include_draft_tools: bool = True,
) -> tuple[EvolutionRunSummary, list[EvolutionFinding]]:
    findings: list[EvolutionFinding] = []
    known_domains = {item.id for item in DOMAIN_CATALOG}
    known_tool_forms = {item.id for item in TOOL_FORM_CATALOG}
    required_tag_namespaces = ("domain:", "form:", "runtime:", "lifecycle:", "input:", "output:")

    analyzable_tools = [tool for tool in tools if tool.status == "active" or (include_draft_tools and tool.status == "draft")]

    for tool in analyzable_tools:
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
        if (
            tool.primary_domain_id not in known_domains
            or tool.tool_form_id not in known_tool_forms
            or len(tool.runtime_platform_ids) == 0
            or len(tool.lifecycle_stage_ids) == 0
            or not all(
            any(tag.startswith(prefix) for tag in tool.tags) for prefix in required_tag_namespaces
            )
        ):
            findings.append(
                _build_finding(
                    deterministic=deterministic,
                    kind="taxonomy_issue",
                    title=f"{tool.name} 域模型或标签不规范",
                    description="当前工具缺少标准业务域、工具形态、运行平台或关键命名空间标签。",
                    severity="warning",
                    tool_ids=[tool.tool_id],
                )
            )

    active_tools = [tool for tool in tools if tool.status == "active"]
    for index, current in enumerate(active_tools):
        current_domains = {current.primary_domain_id}
        current_stages = set(current.lifecycle_stage_ids)
        current_inputs = set(current.input_types)
        for other in active_tools[index + 1 :]:
            overlap_score = 0
            if current_domains.intersection({other.primary_domain_id}):
                overlap_score += 1
            if current.tool_form_id == other.tool_form_id:
                overlap_score += 1
            if current_stages.intersection(other.lifecycle_stage_ids):
                overlap_score += 1
            if current_inputs.intersection(other.input_types):
                overlap_score += 1
            if set(current.runtime_platform_ids).intersection(other.runtime_platform_ids):
                overlap_score += 1
            if overlap_score >= overlap_threshold:
                findings.append(
                    _build_finding(
                        deterministic=deterministic,
                        kind="overlap_risk",
                        title=f"{current.name} 与 {other.name} 疑似重叠",
                        description="两者在业务域、形态、生命周期或输入侧存在高相似度，建议人工评估是否整合。",
                        severity="critical" if overlap_score >= max(overlap_threshold + 1, 4) else "warning",
                        tool_ids=[current.tool_id, other.tool_id],
                    )
                )

    for domain in DOMAIN_CATALOG:
        if domain.id == "cross_domain_shared":
            continue
        if not any(domain.id == tool.primary_domain_id for tool in active_tools):
            findings.append(
                _build_finding(
                    deterministic=deterministic,
                    kind="coverage_gap",
                    title=f"{domain.label} 域覆盖不足",
                    description="当前没有激活工具覆盖该业务域，工具仓矩阵存在明显空白。",
                    severity="info",
                    tool_ids=[],
                )
            )

    summary = EvolutionRunSummary(
        tool_count=len(analyzable_tools),
        finding_count=len(findings),
        missing_description_count=len([item for item in findings if item.kind == "missing_description"]),
        taxonomy_issue_count=len([item for item in findings if item.kind == "taxonomy_issue"]),
        overlap_risk_count=len([item for item in findings if item.kind == "overlap_risk"]),
        coverage_gap_count=len([item for item in findings if item.kind == "coverage_gap"]),
        accepted_count=len([item for item in findings if item.decision_status == "accepted_to_task"]),
        ignored_count=len([item for item in findings if item.decision_status == "ignored"]),
        generated_task_count=len([item for item in findings if item.linked_task_id]),
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
        raw.evolution_config.updated_at,
        raw.runtime_state.updated_at,
        *[item.updated_at for item in raw.evolution_tasks],
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
