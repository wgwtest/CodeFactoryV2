from __future__ import annotations

from collections.abc import Iterable
from statistics import mean
from typing import Any, Literal

from app.archive_knowledge.contracts import (
    ArchiveKnowledgeResolutionSnapshot,
    ArtifactRef,
    DocumentRuntimeSnapshot,
    EvaluationRunReport,
    GraphQualityReport,
    KnowledgeQualityReport,
    MetricHitExplanation,
    QualityFindingReport,
    QualityGateDecision,
    QualityMetric,
    RuleExecutionRecord,
    RuleHitExplanation,
    RuntimeGraphEdge,
    RuntimeGraphProjection,
)
from app.archive_knowledge.quality.object_findings import build_object_level_quality_findings

MetricDirection = Literal["gte", "lte"]
MetricStatus = Literal["pass", "warning", "fail"]


def build_evaluation_run_report(
    runtime_snapshot: DocumentRuntimeSnapshot,
    resolution_snapshot: ArchiveKnowledgeResolutionSnapshot | None,
    generated_at: str,
) -> EvaluationRunReport:
    knowledge_quality = _build_knowledge_quality_report(runtime_snapshot, resolution_snapshot)
    graph_quality = _build_graph_quality_report(runtime_snapshot)
    all_metrics = [*knowledge_quality.metrics, *graph_quality.metrics]
    rule_hits = _build_rule_hits(runtime_snapshot.rule_execution_records, all_metrics)
    metric_hits = [_metric_hit(metric) for metric in all_metrics]
    quality_finding_report = build_object_level_quality_findings(
        archive_id=runtime_snapshot.archive_id,
        generated_at=generated_at,
        resolution_snapshot=resolution_snapshot,
    )
    gate_decision = _build_gate_decision(
        all_metrics,
        rule_hits,
        metric_hits,
        generated_at,
        quality_finding_report=quality_finding_report,
    )
    knowledge_quality.gate_decision = gate_decision

    return EvaluationRunReport(
        evaluation_id=f"EVAL-{runtime_snapshot.run_id}",
        archive_id=runtime_snapshot.archive_id,
        run_id=runtime_snapshot.run_id,
        generated_at=generated_at,
        knowledge_quality=knowledge_quality,
        graph_quality=graph_quality,
        gate_decision=gate_decision,
        rule_hits=rule_hits,
        metric_hits=metric_hits,
        quality_finding_report=quality_finding_report,
        data_lineage=_build_data_lineage(runtime_snapshot, resolution_snapshot),
    )


def _build_knowledge_quality_report(
    runtime_snapshot: DocumentRuntimeSnapshot,
    resolution_snapshot: ArchiveKnowledgeResolutionSnapshot | None,
) -> KnowledgeQualityReport:
    records = runtime_snapshot.rule_execution_records
    concept_precision = _metric_from_records(records, "concept_precision", default=0.0)
    evidence_coverage = _metric_from_records(records, "evidence_coverage", default=0.0)
    conflict_rate = _metric_from_records(records, "conflict_rate", default=0.0)
    duplicate_rate = _metric_from_records(records, "duplicate_rate", default=0.0)
    stale_object_count = int(_metric_from_records(records, "stale_object_count", default=0.0))

    if resolution_snapshot and resolution_snapshot.update_plan:
        stale_object_count = max(stale_object_count, len(resolution_snapshot.update_plan.stale_object_ids))

    affected_object_ids = _unique(item for record in records for item in record.affected_object_ids)
    affected_relation_ids = _unique(item for record in records for item in record.affected_relation_ids)
    input_artifact_ids = _unique(
        ref.artifact_id for record in records for ref in record.input_artifact_refs
    )
    output_artifact_ids = _unique(
        ref.artifact_id for record in records for ref in record.output_artifact_refs
    )
    evidence_anchor_ids = _evidence_anchor_ids(records)

    metrics = [
        _metric(
            metric_id="knowledge.concept_precision",
            metric_name="概念识别准确率",
            scope="archive",
            actual=concept_precision,
            threshold=0.85,
            direction="gte",
            explanation="候选概念中被规则或评估记录认可的比例，用于判断抽取出的业务概念是否可信。",
            affected_object_ids=affected_object_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "concept_precision"),
            input_artifact_ids=input_artifact_ids,
            output_artifact_ids=output_artifact_ids,
        ),
        _metric(
            metric_id="knowledge.evidence_coverage",
            metric_name="证据覆盖率",
            scope="archive",
            actual=evidence_coverage,
            threshold=0.90,
            direction="gte",
            explanation="可追溯到原文证据锚点的候选知识比例，用于判断知识是否有来源依据。",
            affected_object_ids=affected_object_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "evidence_coverage"),
            input_artifact_ids=input_artifact_ids,
            output_artifact_ids=output_artifact_ids,
            evidence_anchor_ids=evidence_anchor_ids,
        ),
        _metric(
            metric_id="knowledge.conflict_rate",
            metric_name="冲突率",
            scope="archive",
            actual=conflict_rate,
            threshold=0.05,
            direction="lte",
            explanation="定义、数值、关系方向或适用范围存在冲突的候选知识比例。",
            affected_object_ids=affected_object_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "conflict_rate"),
        ),
        _metric(
            metric_id="knowledge.duplicate_rate",
            metric_name="重复候选率",
            scope="archive",
            actual=duplicate_rate,
            threshold=0.08,
            direction="lte",
            explanation="跨文档归并前疑似重复候选的比例，用于发现同一知识被多次堆叠的问题。",
            affected_object_ids=affected_object_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "duplicate_rate"),
        ),
        _metric(
            metric_id="knowledge.stale_object_count",
            metric_name="需重算对象数",
            scope="archive",
            actual=float(stale_object_count),
            threshold=3,
            direction="lte",
            explanation="策略、证据或归并逻辑变化后需要候选态增量重算的对象数量。",
            affected_object_ids=resolution_snapshot.update_plan.stale_object_ids
            if resolution_snapshot and resolution_snapshot.update_plan
            else affected_object_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "stale_object_count"),
        ),
    ]

    return KnowledgeQualityReport(
        report_id=f"KQ-{runtime_snapshot.run_id}",
        archive_id=runtime_snapshot.archive_id,
        run_id=runtime_snapshot.run_id,
        document_id=runtime_snapshot.document_id,
        policy_snapshot_id=runtime_snapshot.policy_snapshot.snapshot_id,
        resolution_snapshot_id=resolution_snapshot.snapshot_id if resolution_snapshot else None,
        health_level=_health_level(metrics),
        concept_precision=concept_precision,
        evidence_coverage=evidence_coverage,
        conflict_rate=conflict_rate,
        duplicate_rate=duplicate_rate,
        stale_object_count=stale_object_count,
        metrics=metrics,
        recommended_actions=_knowledge_actions(metrics),
    )


def _build_graph_quality_report(runtime_snapshot: DocumentRuntimeSnapshot) -> GraphQualityReport:
    graph = runtime_snapshot.graph_projection
    records = runtime_snapshot.rule_execution_records
    relation_confidence_avg = _metric_from_records(records, "relation_confidence_avg", default=0.0)
    duplicate_relation_rate = _duplicate_relation_rate(graph)
    orphan_node_rate = _orphan_node_rate(graph)
    explainability_coverage = _explainability_coverage(graph, records)
    layout_readability = _layout_readability(graph)
    affected_relation_ids = _unique(edge.edge_id for edge in graph.edges)
    affected_object_ids = _unique(node.node_id for node in graph.nodes)
    evidence_anchor_ids = _evidence_anchor_ids(records)

    metrics = [
        _metric(
            metric_id="graph.relation_confidence_avg",
            metric_name="关系可信度",
            scope="graph",
            actual=relation_confidence_avg,
            threshold=0.80,
            direction="gte",
            explanation="关系质量记录输出的平均可信度，用于判断图谱边是否可靠。",
            affected_relation_ids=affected_relation_ids,
            rule_execution_record_ids=_record_ids_for_metric(records, "relation_confidence_avg"),
        ),
        _metric(
            metric_id="graph.orphan_node_rate",
            metric_name="孤立节点率",
            scope="graph",
            actual=orphan_node_rate,
            threshold=0.10,
            direction="lte",
            explanation="运行态图谱中没有任何入边或出边的节点比例。",
            affected_object_ids=_orphan_node_ids(graph),
        ),
        _metric(
            metric_id="graph.duplicate_relation_rate",
            metric_name="重复关系率",
            scope="graph",
            actual=duplicate_relation_rate,
            threshold=0.05,
            direction="lte",
            explanation="同一个投影内来源、目标和关系类型完全相同的重复边比例。",
            affected_relation_ids=_duplicate_relation_ids(graph),
        ),
        _metric(
            metric_id="graph.explainability_coverage",
            metric_name="可解释覆盖率",
            scope="graph",
            actual=explainability_coverage,
            threshold=0.85,
            direction="gte",
            explanation="图谱边可通过证据文本、规则节点或规则执行记录解释的比例。",
            affected_object_ids=affected_object_ids,
            affected_relation_ids=affected_relation_ids,
            rule_execution_record_ids=[record.execution_id for record in records],
            evidence_anchor_ids=evidence_anchor_ids,
        ),
        _metric(
            metric_id="graph.layout_readability",
            metric_name="布局可读性",
            scope="graph",
            actual=layout_readability,
            threshold=0.85,
            direction="gte",
            explanation="基于布局策略和关系密度计算的图谱可读性评分。",
            affected_object_ids=affected_object_ids,
            affected_relation_ids=affected_relation_ids,
        ),
    ]

    return GraphQualityReport(
        report_id=f"GQ-{runtime_snapshot.run_id}",
        archive_id=runtime_snapshot.archive_id,
        run_id=runtime_snapshot.run_id,
        graph_projection_id=graph.graph_projection_id,
        graph_scope="runtime",
        health_level=_health_level(metrics),
        relation_confidence_avg=relation_confidence_avg,
        orphan_node_rate=orphan_node_rate,
        duplicate_relation_rate=duplicate_relation_rate,
        explainability_coverage=explainability_coverage,
        layout_readability=layout_readability,
        metrics=metrics,
    )


def _metric(
    *,
    metric_id: str,
    metric_name: str,
    scope: str,
    actual: float,
    threshold: float,
    direction: MetricDirection,
    explanation: str,
    affected_object_ids: list[str] | None = None,
    affected_relation_ids: list[str] | None = None,
    rule_execution_record_ids: list[str] | None = None,
    input_artifact_ids: list[str] | None = None,
    output_artifact_ids: list[str] | None = None,
    evidence_anchor_ids: list[str] | None = None,
) -> QualityMetric:
    return QualityMetric(
        metric_id=metric_id,
        metric_name=metric_name,
        scope=scope,  # type: ignore[arg-type]
        actual=round(actual, 4),
        threshold=threshold,
        threshold_direction=direction,
        status=_metric_status(actual, threshold, direction),
        explanation=explanation,
        affected_object_ids=affected_object_ids or [],
        affected_relation_ids=affected_relation_ids or [],
        rule_execution_record_ids=rule_execution_record_ids or [],
        input_artifact_ids=input_artifact_ids or [],
        output_artifact_ids=output_artifact_ids or [],
        evidence_anchor_ids=evidence_anchor_ids or [],
    )


def _metric_status(actual: float, threshold: float, direction: MetricDirection) -> MetricStatus:
    if direction == "gte":
        if actual >= threshold:
            return "pass"
        if actual >= threshold * 0.9:
            return "warning"
        return "fail"
    if actual <= threshold:
        return "pass"
    if actual <= max(threshold * 1.5, threshold + 0.03):
        return "warning"
    return "fail"


def _metric_from_records(records: Iterable[RuleExecutionRecord], key: str, default: float) -> float:
    values = [_to_float(record.metrics.get(key)) for record in records if key in record.metrics]
    numeric_values = [value for value in values if value is not None]
    return mean(numeric_values) if numeric_values else default


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _record_ids_for_metric(records: Iterable[RuleExecutionRecord], metric_key: str) -> list[str]:
    return [record.execution_id for record in records if metric_key in record.metrics]


def _build_rule_hits(
    records: Iterable[RuleExecutionRecord],
    metrics: Iterable[QualityMetric],
) -> list[RuleHitExplanation]:
    metric_list = list(metrics)
    hits: list[RuleHitExplanation] = []
    for record in records:
        metric_ids = [
            metric.metric_id
            for metric in metric_list
            if record.execution_id in metric.rule_execution_record_ids
        ]
        evidence_anchor_ids = _evidence_anchor_ids([record])
        hits.append(
            RuleHitExplanation(
                hit_id=f"rule-hit-{record.execution_id}",
                rule_id=record.rule_id,
                rule_version=record.rule_version,
                rule_hash=record.rule_hash,
                stage_id=record.stage_id,
                decision=record.decision,
                metric_ids=metric_ids,
                input_artifact_refs=record.input_artifact_refs,
                output_artifact_refs=record.output_artifact_refs,
                affected_object_ids=record.affected_object_ids,
                affected_relation_ids=record.affected_relation_ids,
                evidence_anchor_ids=evidence_anchor_ids,
                explanation=(
                    f"{record.rule_id}@{record.rule_version} 基于 {len(record.input_artifact_refs)} 个输入产物"
                    f"生成 {len(record.output_artifact_refs)} 个输出产物，决策为 {record.decision}。"
                ),
            )
        )
    return hits


def _metric_hit(metric: QualityMetric) -> MetricHitExplanation:
    return MetricHitExplanation(
        hit_id=f"metric-hit-{metric.metric_id}",
        metric_id=metric.metric_id,
        actual=metric.actual,
        threshold=metric.threshold,
        threshold_direction=metric.threshold_direction,
        status=metric.status,
        affected_object_ids=metric.affected_object_ids,
        affected_relation_ids=metric.affected_relation_ids,
        rule_execution_record_ids=metric.rule_execution_record_ids,
        evidence_anchor_ids=metric.evidence_anchor_ids,
        explanation=metric.explanation,
    )


def _build_gate_decision(
    metrics: list[QualityMetric],
    rule_hits: list[RuleHitExplanation],
    metric_hits: list[MetricHitExplanation],
    generated_at: str,
    *,
    quality_finding_report: QualityFindingReport | None = None,
) -> QualityGateDecision:
    normalized_rule_decisions = {hit.decision.lower() for hit in rule_hits}
    has_fail = any(metric.status == "fail" for metric in metrics)
    has_warning = any(metric.status == "warning" for metric in metrics)
    has_blocking_quality_findings = bool(
        quality_finding_report and quality_finding_report.summary.publish_blocked
    )

    if "block" in normalized_rule_decisions or has_fail or has_blocking_quality_findings:
        decision: Literal["auto_pass", "warn_continue", "block", "defer"] = "block"
        output_action: Literal[
            "publish_candidate",
            "publish_candidate_with_warning",
            "return_for_rebuild",
            "delay_publication",
        ] = "return_for_rebuild"
    elif normalized_rule_decisions & {"defer", "require_governance"}:
        decision = "defer"
        output_action = "delay_publication"
    elif normalized_rule_decisions & {"warn", "warning", "warn_continue"} or has_warning:
        decision = "warn_continue"
        output_action = "publish_candidate_with_warning"
    else:
        decision = "auto_pass"
        output_action = "publish_candidate"

    pass_ratio = len([metric for metric in metrics if metric.status == "pass"]) / max(len(metrics), 1)
    score = round(pass_ratio * 100, 2)
    if has_blocking_quality_findings:
        score = min(score, 69.0)
    affected_object_ids = _unique(item for hit in rule_hits for item in hit.affected_object_ids)
    affected_relation_ids = _unique(item for hit in rule_hits for item in hit.affected_relation_ids)
    if quality_finding_report:
        affected_object_ids = _unique(
            [
                *affected_object_ids,
                *[
                    finding.target_id
                    for finding in quality_finding_report.findings
                    if finding.target_id and finding.scope in {"item", "evidence", "category"}
                ],
            ]
        )
        affected_relation_ids = _unique(
            [
                *affected_relation_ids,
                *[
                    finding.target_id
                    for finding in quality_finding_report.findings
                    if finding.target_id and finding.scope == "relation"
                ],
            ]
        )
    failed_metric_ids = [metric.metric_id for metric in metrics if metric.status == "fail"]
    warning_metric_ids = [metric.metric_id for metric in metrics if metric.status == "warning"]

    if decision == "block" and has_blocking_quality_findings and quality_finding_report:
        reason = (
            "Object-level quality findings block publication candidate generation: "
            f"{quality_finding_report.summary.blocked_count} blocked, "
            f"{quality_finding_report.summary.warning_count} warning."
        )
    elif decision == "block":
        reason = f"存在失败指标，阻断生成发布候选：{', '.join(failed_metric_ids) or '规则决策'}。"
    elif decision == "defer":
        reason = "机器规则要求延迟发布或等待治理确认。"
    elif decision == "warn_continue":
        reason = f"可生成发布候选，但需要携带警告：{', '.join(warning_metric_ids) or '规则决策'}。"
    else:
        reason = "全部质量指标和规则决策满足自动通过阈值。"

    return QualityGateDecision(
        decision=decision,
        score=score,
        metric_results=metrics,
        rule_hits=rule_hits,
        metric_hits=metric_hits,
        affected_object_ids=affected_object_ids,
        affected_relation_ids=affected_relation_ids,
        output_action=output_action,
        explanation=reason,
        generated_at=generated_at,
    )


def _health_level(metrics: list[QualityMetric]) -> Literal["good", "watch", "risk", "broken"]:
    if any(metric.status == "fail" for metric in metrics):
        return "risk"
    if any(metric.status == "warning" for metric in metrics):
        return "watch"
    return "good"


def _knowledge_actions(metrics: list[QualityMetric]) -> list[str]:
    actions: list[str] = []
    for metric in metrics:
        if metric.status == "pass":
            continue
        if metric.metric_id == "knowledge.evidence_coverage":
            actions.append("补齐低覆盖候选的证据锚点后再进入发布候选。")
        elif metric.metric_id == "knowledge.conflict_rate":
            actions.append("把冲突定义或关系方向送入治理队列，保留规则命中记录。")
        elif metric.metric_id == "knowledge.duplicate_rate":
            actions.append("先执行跨文档同知识归并，避免重复候选进入正式输出。")
        elif metric.metric_id == "knowledge.stale_object_count":
            actions.append("对 stale 对象执行候选态增量重算，不覆盖正式知识。")
        else:
            actions.append(f"复核 {metric.metric_name} 对应的规则记录和输入对象。")
    return actions


def _orphan_node_ids(graph: RuntimeGraphProjection) -> list[str]:
    connected_ids = {edge.source for edge in graph.edges} | {edge.target for edge in graph.edges}
    return [node.node_id for node in graph.nodes if node.node_id not in connected_ids]


def _orphan_node_rate(graph: RuntimeGraphProjection) -> float:
    return len(_orphan_node_ids(graph)) / max(len(graph.nodes), 1)


def _duplicate_relation_keys(graph: RuntimeGraphProjection) -> dict[tuple[str, str, str], list[RuntimeGraphEdge]]:
    relation_groups: dict[tuple[str, str, str], list[RuntimeGraphEdge]] = {}
    for edge in graph.edges:
        relation_groups.setdefault((edge.source, edge.target, edge.relation), []).append(edge)
    return {key: edges for key, edges in relation_groups.items() if len(edges) > 1}


def _duplicate_relation_ids(graph: RuntimeGraphProjection) -> list[str]:
    duplicate_ids: list[str] = []
    for edges in _duplicate_relation_keys(graph).values():
        duplicate_ids.extend(edge.edge_id for edge in edges[1:])
    return duplicate_ids


def _duplicate_relation_rate(graph: RuntimeGraphProjection) -> float:
    return len(_duplicate_relation_ids(graph)) / max(len(graph.edges), 1)


def _explainability_coverage(
    graph: RuntimeGraphProjection,
    records: Iterable[RuleExecutionRecord],
) -> float:
    rule_ids = {record.rule_id for record in records}
    explained_edges = 0
    rule_payload_refs = {node.node_id for node in graph.nodes if node.payload_ref and node.payload_ref.split("@")[0] in rule_ids}
    for edge in graph.edges:
        has_evidence = bool(edge.evidence)
        touches_rule = edge.source in rule_payload_refs or edge.target in rule_payload_refs
        if has_evidence or touches_rule:
            explained_edges += 1
    return explained_edges / max(len(graph.edges), 1)


def _layout_readability(graph: RuntimeGraphProjection) -> float:
    strategy_score = {
        "layered_dag": 1.0,
        "manual_adjusted": 0.9,
        "force_assist": 0.82,
    }[graph.layout_strategy]
    density = len(graph.edges) / max(len(graph.nodes), 1)
    density_penalty = max(density - 2.0, 0) * 0.08
    return max(round(strategy_score - density_penalty, 4), 0.0)


def _evidence_anchor_ids(records: Iterable[RuleExecutionRecord]) -> list[str]:
    anchor_ids: list[str] = []
    for record in records:
        for ref in [*record.input_artifact_refs, *record.output_artifact_refs]:
            if ref.artifact_type in {"source_anchor", "evidence_anchor"} or ref.artifact_id.startswith("anchor-"):
                anchor_ids.append(ref.artifact_id)
            metadata_anchor = ref.metadata.get("evidence_anchor_id")
            if isinstance(metadata_anchor, str):
                anchor_ids.append(metadata_anchor)
    return _unique(anchor_ids)


def _build_data_lineage(
    runtime_snapshot: DocumentRuntimeSnapshot,
    resolution_snapshot: ArchiveKnowledgeResolutionSnapshot | None,
) -> list[ArtifactRef]:
    lineage = [
        ArtifactRef(
            artifact_id=runtime_snapshot.run_id,
            artifact_type="DocumentRuntimeSnapshot",
            document_id=runtime_snapshot.document_id,
            summary="质量评估使用的运行态快照。",
        ),
        ArtifactRef(
            artifact_id=runtime_snapshot.graph_projection.graph_projection_id,
            artifact_type="RuntimeGraphProjection",
            document_id=runtime_snapshot.document_id,
            summary="图谱质量指标使用的运行态图谱投影。",
        ),
        ArtifactRef(
            artifact_id=runtime_snapshot.policy_snapshot.snapshot_id,
            artifact_type="PolicyRuntimeSnapshot",
            summary="规则执行记录绑定的冻结策略快照。",
            metadata={
                "policy_package_id": runtime_snapshot.policy_snapshot.policy_package_id,
                "policy_package_version_id": runtime_snapshot.policy_snapshot.policy_package_version_id,
                "policy_package_version_hash": runtime_snapshot.policy_snapshot.policy_package_version_hash,
            },
        ),
    ]
    if resolution_snapshot:
        lineage.append(
            ArtifactRef(
                artifact_id=resolution_snapshot.snapshot_id,
                artifact_type="ArchiveKnowledgeResolutionSnapshot",
                summary="用于重复、冲突和 stale 对象指标计算的库级归并快照。",
            )
        )
    return lineage


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
