from __future__ import annotations

from typing import TypeVar

from app.archive_knowledge.contracts import (
    ApiExposureScope,
    ArchiveKnowledgeResolutionSnapshot,
    ArtifactRef,
    CanonicalKnowledgeItem,
    CrossDocumentMatchCandidate,
    DeprecatedOutputRoute,
    DocumentRuntimeSnapshot,
    EvaluationRunReport,
    ImpactSet,
    KnowledgeIdentityKey,
    KnowledgeMergeDecision,
    KnowledgeResolutionTrace,
    KnowledgeUpdatePlan,
    P1KnowledgeSupplyExport,
    P1NavigationEntry,
    P1RefactorBootstrap,
    P1ResponseEnvelope,
    P1WorkLine,
    P6DisplayExportContractV2,
    PolicyPackage,
    PolicyPackageVersion,
    PolicyRuntimeSnapshot,
    PublicationCandidateSnapshot,
    PublishedKnowledgeSnapshot,
    RuleActionMapping,
    RuleConditionContract,
    RuleContract,
    RuleExecutionRecord,
    RuleFieldContract,
    ResolvedKnowledgeObject,
    ResolvedKnowledgeRelation,
    RuntimeGraphEdge,
    RuntimeGraphNode,
    RuntimeGraphProjection,
    StageExecutionContract,
    StageSnapshot,
    TraceRef,
)
from app.archive_knowledge.quality import build_evaluation_run_report


PayloadT = TypeVar("PayloadT")
GENERATED_AT = "2026-05-08T10:00:00+08:00"
ARCHIVE_ID = "archive-contract-demo"
DOCUMENT_ID = "doc-contract-2026q1"
RUN_ID = "RUN-P1-R0-001"


def _envelope(contract_version: str, data: PayloadT) -> P1ResponseEnvelope[PayloadT]:
    return P1ResponseEnvelope[PayloadT](
        contract_version=contract_version,
        source_kind="fixture",
        generated_at=GENERATED_AT,
        data=data,
    )


def _coverage_rule() -> RuleContract:
    return RuleContract(
        rule_id="RL-QG-COVERAGE-001",
        rule_name="证据覆盖质量门禁",
        rule_version="r1.0",
        rule_hash="sha256:rulecoverage001",
        stage_id="quality_gate",
        effect_kind="score",
        enabled=True,
        scope_selector={"knowledge_type": "contract_clause"},
        input_schema=[
            RuleFieldContract(
                field_name="evidence_coverage",
                source_artifact="candidate-knowledge",
                field_type="number",
                required=True,
                include_in_hash=True,
                validation="0 <= value <= 1",
                example="0.91",
                business_meaning="候选知识的证据覆盖程度",
                missing_action="block",
            ),
            RuleFieldContract(
                field_name="input_hash",
                source_artifact="runtime-snapshot",
                field_type="string",
                required=True,
                include_in_hash=True,
                validation="sha256",
                example="sha256:input001",
                business_meaning="规则输入载荷的稳定摘要",
                missing_action="block",
            ),
        ],
        output_schema=[
            RuleFieldContract(
                field_name="quality_decision",
                source_artifact="quality-gate",
                field_type="enum",
                required=True,
                include_in_hash=True,
                validation="pass | warn_continue | block",
                example="warn_continue",
                business_meaning="机器质量门禁决策",
            ),
            RuleFieldContract(
                field_name="affected_object_ids",
                target_artifact="impact-set",
                field_type="array",
                required=True,
                include_in_hash=True,
                validation="len >= 1",
                example="[K-24, K-31, P-24]",
                business_meaning="受该规则决策影响的知识对象",
                used_for_impact=True,
            ),
            RuleFieldContract(
                field_name="output_hash",
                target_artifact="runtime-snapshot",
                field_type="string",
                required=True,
                include_in_hash=True,
                validation="sha256",
                example="sha256:output001",
                business_meaning="规则输出载荷的稳定摘要",
            ),
        ],
        parameters={
            "conditions": [
                RuleConditionContract(
                    condition_id="coverage-threshold",
                    left_field="evidence_coverage",
                    operator=">=",
                    right_value=0.9,
                    description="只有证据覆盖率达到阈值时才允许自动通过",
                ).model_dump()
            ],
            "thresholds": {"warning": 0.85, "pass": 0.9},
            "ai_adaptation": "suggest_threshold",
        },
        action_mapping=RuleActionMapping(
            when_hit="auto_pass",
            when_miss="warn_continue",
            output_fields=["quality_decision", "affected_object_ids", "output_hash"],
            downstream_stage_ids=["publication_candidate"],
        ),
        trace_fields=["rule_id", "rule_version", "rule_hash", "input_hash", "output_hash", "affected_object_ids"],
        contract_status="valid",
        contract_errors=[],
    )


def _policy_snapshot() -> PolicyRuntimeSnapshot:
    return PolicyRuntimeSnapshot(
        snapshot_id="RS-P1-R0-001",
        archive_id=ARCHIVE_ID,
        run_id=RUN_ID,
        policy_package_id="PKG-CONTRACT-GENERAL",
        policy_package_version_id="PKGV-20260508-R0",
        policy_package_version_hash="sha256:p1r0policy0001",
        frozen_at=GENERATED_AT,
        stage_contract_refs=["unified_document", "quality_gate"],
        rule_contract_refs=["RL-QG-COVERAGE-001@r1.0"],
    )


def _graph_projection() -> RuntimeGraphProjection:
    return RuntimeGraphProjection(
        graph_projection_id="GRAPH-P1-R0-001",
        archive_id=ARCHIVE_ID,
        document_id=DOCUMENT_ID,
        view_mode="semantic_aggregate",
        layout_strategy="layered_dag",
        highlighted_node_ids=["node-rule-coverage"],
        highlighted_edge_ids=["edge-rule-to-output"],
        nodes=[
            RuntimeGraphNode(
                node_id="node-input-candidates",
                label="候选知识集合 24 项",
                node_type="input_object",
                stage_id="quality_gate",
                status="running",
                semantic_role="input",
                object_count=24,
            ),
            RuntimeGraphNode(
                node_id="node-rule-coverage",
                label="证据覆盖质量门禁",
                node_type="rule",
                stage_id="quality_gate",
                status="running",
                semantic_role="basis",
                payload_ref="RL-QG-COVERAGE-001@r1.0",
            ),
            RuntimeGraphNode(
                node_id="node-output-publication",
                label="发布候选输入包 6 项",
                node_type="output_object",
                stage_id="quality_gate",
                status="pending",
                semantic_role="output",
                object_count=6,
            ),
        ],
        edges=[
            RuntimeGraphEdge(
                edge_id="edge-input-to-rule",
                source="node-input-candidates",
                target="node-rule-coverage",
                relation="evaluated_by",
                stage_id="quality_gate",
                evidence="证据覆盖率 actual=0.91",
            ),
            RuntimeGraphEdge(
                edge_id="edge-rule-to-output",
                source="node-rule-coverage",
                target="node-output-publication",
                relation="warn_continue",
                stage_id="quality_gate",
                evidence="阈值 >= 0.90",
            ),
        ],
    )


def _rule_execution_record() -> RuleExecutionRecord:
    return RuleExecutionRecord(
        execution_id="RECORD-QG-001",
        run_id=RUN_ID,
        archive_id=ARCHIVE_ID,
        document_id=DOCUMENT_ID,
        stage_id="quality_gate",
        policy_package_version_id="PKGV-20260508-R0",
        rule_id="RL-QG-COVERAGE-001",
        rule_version="r1.0",
        rule_hash="sha256:rulecoverage001",
        input_artifact_refs=[
            ArtifactRef(artifact_id="candidate-knowledge", artifact_type="knowledge_candidate"),
            ArtifactRef(
                artifact_id="anchor-A-102",
                artifact_type="source_anchor",
                document_id=DOCUMENT_ID,
                summary="合同金额与质量判断的原文段落锚点",
            ),
        ],
        output_artifact_refs=[ArtifactRef(artifact_id="publication-candidate", artifact_type="publication_candidate")],
        input_hash="sha256:input001",
        output_hash="sha256:output001",
        affected_object_ids=["K-24", "K-31", "P-24"],
        affected_relation_ids=["R-11"],
        metrics={
            "concept_precision": 0.88,
            "evidence_coverage": 0.91,
            "conflict_rate": 0.03,
            "duplicate_rate": 0.02,
            "stale_object_count": 2,
            "relation_confidence_avg": 0.86,
        },
        decision="warn_continue",
        executed_at=GENERATED_AT,
    )


def get_p1_bootstrap() -> P1ResponseEnvelope[P1RefactorBootstrap]:
    return _envelope(
        "p1.refactor.r0",
        P1RefactorBootstrap(
            refactor_id="P1-R0-20260508",
            title="P1 业务知识库黄金样例",
            goal="用显式合同串起用户入口、策略合同、运行态图谱、质量评估、跨文档归并和系统输出。",
            next_parallel_threads=6,
            navigation=[
                P1NavigationEntry(
                    key="user-home",
                    title="业务知识库入口",
                    route="/archives",
                    owner_line="W1",
                    status="existing_page",
                    contract_refs=["PolicyPackage", "DocumentRuntimeSnapshot"],
                ),
                P1NavigationEntry(
                    key="policy-center",
                    title="策略包与规则合同",
                    route="/policies",
                    owner_line="W2",
                    status="existing_page",
                    contract_refs=["PolicyPackage", "RuleContract", "RuleExecutionRecord"],
                ),
                P1NavigationEntry(
                    key="runtime-workbench",
                    title="实时抽取图谱工作台",
                    route="/archives",
                    owner_line="W3",
                    status="existing_page",
                    contract_refs=["DocumentRuntimeSnapshot", "RuntimeGraphProjection"],
                ),
                P1NavigationEntry(
                    key="quality-center",
                    title="知识质量与图谱质量",
                    route="/p1/quality",
                    owner_line="W4",
                    status="r0_shell",
                    contract_refs=["KnowledgeQualityReport", "GraphQualityReport", "EvaluationRunReport"],
                ),
                P1NavigationEntry(
                    key="resolution-center",
                    title="跨文档同知识归并",
                    route="/p1/resolution",
                    owner_line="W5",
                    status="r0_shell",
                    contract_refs=["ArchiveKnowledgeResolutionSnapshot", "KnowledgeUpdatePlan"],
                ),
                P1NavigationEntry(
                    key="system-output",
                    title="系统间正式输出合同",
                    route="/p1/system-output",
                    owner_line="W6",
                    status="r0_shell",
                    contract_refs=["P1KnowledgeSupplyExport", "P6DisplayExportContract.v2"],
                ),
            ],
            work_lines=[
                P1WorkLine(
                    line_id="W1",
                    title="用户入口与任务闭环",
                    responsibility="让终端用户能理解知识库创建、文档导入、启动抽取和结果查看。",
                    input_contracts=["PolicyPackage", "PolicyRuntimeSnapshot"],
                    output_contracts=["DocumentRuntimeSnapshot"],
                    verification=["启动抽取不刷新整页", "文档清单能进入实时工作台"],
                    suggested_parallel_owner="frontend-user-flow",
                ),
                P1WorkLine(
                    line_id="W2",
                    title="策略包与规则合同主干",
                    responsibility="保证规则合同与抽取运行记录一一对应。",
                    input_contracts=["RuleContract", "StageExecutionContract"],
                    output_contracts=["PolicyPackageVersion", "RuleExecutionRecord"],
                    verification=["缺失字段会触发合同校验失败", "运行记录包含 rule_id/version/hash"],
                    suggested_parallel_owner="policy-contract",
                ),
                P1WorkLine(
                    line_id="W3",
                    title="运行态图谱与事件流",
                    responsibility="运行态优先走 Stream，并生成可解释的语义图谱投影。",
                    input_contracts=["DocumentRuntimeSnapshot", "RuleExecutionRecord"],
                    output_contracts=["RuntimeGraphProjection", "StageSnapshot"],
                    verification=["不整页刷新", "选中节点或边能联动观察窗"],
                    suggested_parallel_owner="runtime-graph",
                ),
                P1WorkLine(
                    line_id="W4",
                    title="知识与图谱质量评估",
                    responsibility="衡量抽取概念、证据链和图谱关系是否可信。",
                    input_contracts=["RuntimeGraphProjection", "RuleExecutionRecord"],
                    output_contracts=["KnowledgeQualityReport", "GraphQualityReport", "EvaluationRunReport"],
                    verification=["报告解释概念/证据/冲突/关系质量", "门禁决策可追溯到规则"],
                    suggested_parallel_owner="quality-evaluation",
                ),
                P1WorkLine(
                    line_id="W5",
                    title="跨文档匹配、合并与更新",
                    responsibility="识别同一知识库内多文档重复知识，并生成增量更新计划。",
                    input_contracts=["KnowledgeIdentityKey", "CrossDocumentMatchCandidate"],
                    output_contracts=["ArchiveKnowledgeResolutionSnapshot", "KnowledgeUpdatePlan"],
                    verification=["新文档能匹配既有知识", "策略变化只生成候选态重算计划"],
                    suggested_parallel_owner="knowledge-resolution",
                ),
                P1WorkLine(
                    line_id="W6",
                    title="正式输出与系统间合同",
                    responsibility="只向下游系统暴露治理确认后的正式知识快照。",
                    input_contracts=["PublishedKnowledgeSnapshot"],
                    output_contracts=["P1KnowledgeSupplyExport", "P6DisplayExportContract.v2"],
                    verification=["候选知识不会作为正式输出暴露", "输出 API 版本稳定"],
                    suggested_parallel_owner="system-output",
                ),
            ],
        ),
    )


def get_p1_policy_package() -> P1ResponseEnvelope[PolicyPackage]:
    return _envelope(
        "p1.policy_package.r0",
        PolicyPackage(
            policy_package_id="PKG-CONTRACT-GENERAL",
            policy_package_name="合同通用抽取",
            business_domain="用户选择的业务资料文件夹",
            knowledge_types=["contract_clause", "obligation", "amount_clause", "risk_hint"],
            owner="P1 策略合同",
            lifecycle_status="published",
            current_version_id="PKGV-20260508-R0",
            versions=[
                PolicyPackageVersion(
                    policy_package_version_id="PKGV-20260508-R0",
                    version_label="v3.12-r0",
                    status="published",
                    hash="sha256:p1r0policy0001",
                    created_at=GENERATED_AT,
                    stage_contracts=[
                        StageExecutionContract(
                            stage_id="unified_document",
                            stage_name="统一文档",
                            order_hint=1,
                            input_artifacts=[ArtifactRef(artifact_id="raw-document", artifact_type="uploaded_document")],
                            output_artifacts=[
                                ArtifactRef(artifact_id="unified-document", artifact_type="unified_document")
                            ],
                            rule_ids=["RL-DOC-STRUCT-001"],
                            can_run_independently=True,
                            downstream_stage_ids=["evidence_construction"],
                        ),
                        StageExecutionContract(
                            stage_id="quality_gate",
                            stage_name="质量门禁",
                            order_hint=4,
                            input_artifacts=[
                                ArtifactRef(artifact_id="candidate-knowledge", artifact_type="knowledge_candidate")
                            ],
                            output_artifacts=[
                                ArtifactRef(artifact_id="publication-candidate", artifact_type="publication_candidate")
                            ],
                            rule_ids=["RL-QG-COVERAGE-001"],
                            downstream_stage_ids=["publication_candidate"],
                        ),
                    ],
                    rule_contracts=[_coverage_rule()],
                    compatible_output_contracts=["P1KnowledgeSupplyExport.v1", "P6DisplayExportContract.v2"],
                )
            ],
        ),
    )


def get_p1_runtime_snapshot() -> P1ResponseEnvelope[DocumentRuntimeSnapshot]:
    return _envelope(
        "p1.document_runtime.r0",
        DocumentRuntimeSnapshot(
            archive_id=ARCHIVE_ID,
            document_id=DOCUMENT_ID,
            run_id=RUN_ID,
            status="running",
            current_stage_id="quality_gate",
            current_stage_message="质量门禁正在评估候选知识的证据覆盖率。",
            stream_status="connected",
            policy_snapshot=_policy_snapshot(),
            stage_snapshots=[
                StageSnapshot(
                    stage_id="unified_document",
                    stage_name="统一文档",
                    status="completed",
                    input_object_count=1,
                    output_object_count=128,
                    rule_execution_record_ids=["RECORD-DOC-STRUCT-001"],
                    graph_projection_id="GRAPH-P1-R0-001",
                ),
                StageSnapshot(
                    stage_id="quality_gate",
                    stage_name="质量门禁",
                    status="running",
                    input_object_count=24,
                    output_object_count=6,
                    rule_execution_record_ids=["RECORD-QG-001"],
                    graph_projection_id="GRAPH-P1-R0-001",
                ),
            ],
            graph_projection=_graph_projection(),
            rule_execution_records=[_rule_execution_record()],
            event_trace=[
                TraceRef(
                    trace_id="TRACE-QG-001",
                    source_kind="runtime",
                    object_ids=["RL-QG-COVERAGE-001", "K-24"],
                    summary="质量门禁生成带警告继续的发布候选。",
                )
            ],
        ),
    )


def get_p1_evaluation_report(
    archive_id: str = ARCHIVE_ID,
    run_id: str = RUN_ID,
) -> P1ResponseEnvelope[EvaluationRunReport]:
    runtime_snapshot = get_p1_runtime_snapshot().data
    runtime_snapshot.archive_id = archive_id
    runtime_snapshot.run_id = run_id
    runtime_snapshot.policy_snapshot.archive_id = archive_id
    runtime_snapshot.policy_snapshot.run_id = run_id
    runtime_snapshot.graph_projection.archive_id = archive_id
    for record in runtime_snapshot.rule_execution_records:
        record.archive_id = archive_id
        record.run_id = run_id

    resolution_snapshot = get_p1_resolution_snapshot().data
    resolution_snapshot.archive_id = archive_id

    return _envelope(
        "p1.evaluation_report.r0",
        build_evaluation_run_report(runtime_snapshot, resolution_snapshot, GENERATED_AT),
    )


def _identity_key() -> KnowledgeIdentityKey:
    return KnowledgeIdentityKey(
        identity_key_id="IK-contract-amount",
        knowledge_type="amount_clause",
        normalized_name="合同总金额",
        business_scope="采购合同",
        key_fields={"currency": "CNY", "subject": "contract amount"},
    )


def get_p1_resolution_snapshot() -> P1ResponseEnvelope[ArchiveKnowledgeResolutionSnapshot]:
    identity_key = _identity_key()
    return _envelope(
        "p1.knowledge_resolution.r0",
        ArchiveKnowledgeResolutionSnapshot(
            snapshot_id="RESOLVE-P1-R0-001",
            archive_id=ARCHIVE_ID,
            run_id=RUN_ID,
            policy_snapshot_id="RS-P1-R0-001",
            runtime_snapshot_id=RUN_ID,
            policy_package_version_id="PKGV-20260508-R0",
            input_document_ids=[DOCUMENT_ID, "doc-contract-supplement"],
            generated_at=GENERATED_AT,
            match_candidates=[
                CrossDocumentMatchCandidate(
                    candidate_id="MATCH-K-24-K-88",
                    identity_key=identity_key,
                    source_candidate_item_ids=["K-24", "K-88"],
                    source_document_ids=[DOCUMENT_ID, "doc-contract-supplement"],
                    similarity_score=0.94,
                    evidence_refs=[ArtifactRef(artifact_id="anchor-A-102", artifact_type="source_anchor")],
                    suggested_action="merge",
                )
            ],
            merge_decisions=[
                KnowledgeMergeDecision(
                    decision_id="MERGE-K-24-K-88",
                    candidate_ids=["MATCH-K-24-K-88"],
                    decision="merged",
                    reason="身份键与来源证据锚点高度相似，可合并为同一规范知识。",
                    rule_execution_record_ids=["RECORD-QG-001"],
                )
            ],
            canonical_items=[
                CanonicalKnowledgeItem(
                    knowledge_id="CK-contract-amount",
                    identity_key=identity_key,
                    status="candidate",
                    display_name="合同总金额",
                    source_document_ids=[DOCUMENT_ID, "doc-contract-supplement"],
                    source_candidate_item_ids=["K-24", "K-88"],
                    evidence_refs=[ArtifactRef(artifact_id="anchor-A-102", artifact_type="source_anchor")],
                    version="candidate-v1",
                )
            ],
            resolved_objects=[
                ResolvedKnowledgeObject(
                    object_id="CK-contract-amount",
                    canonical_name="合同总金额",
                    object_type="amount_clause",
                    source_candidate_ids=["K-24", "K-88"],
                    source_document_ids=[DOCUMENT_ID, "doc-contract-supplement"],
                    evidence_refs=[ArtifactRef(artifact_id="anchor-A-102", artifact_type="source_anchor")],
                    confidence=0.94,
                    merge_decision="merged",
                    conflict_status="clean",
                    identity_key=identity_key,
                    resolution_trace_ids=["TRACE-OBJ-contract-amount", "TRACE-MATCH-contract-amount"],
                    quality_summary={"source_document_count": 2, "candidate_only": True},
                )
            ],
            resolved_relations=[],
            resolution_trace=[
                KnowledgeResolutionTrace(
                    trace_id="TRACE-OBJ-contract-amount",
                    trace_type="object_resolution",
                    object_ids=["CK-contract-amount"],
                    source_candidate_ids=["K-24", "K-88"],
                    evidence_refs=[ArtifactRef(artifact_id="anchor-A-102", artifact_type="source_anchor")],
                    reason="merged object with 2 source documents and confidence=0.94",
                ),
                KnowledgeResolutionTrace(
                    trace_id="TRACE-MATCH-contract-amount",
                    trace_type="merge_decision",
                    object_ids=["CK-contract-amount"],
                    source_candidate_ids=["K-24", "K-88"],
                    rule_execution_record_ids=["RECORD-QG-001"],
                    evidence_refs=[ArtifactRef(artifact_id="anchor-A-102", artifact_type="source_anchor")],
                    reason="身份键与来源证据锚点高度相似，可合并为同一规范知识。",
                ),
            ],
            update_plan=KnowledgeUpdatePlan(
                update_plan_id="PLAN-P1-R0-STALE-001",
                archive_id=ARCHIVE_ID,
                minimum_rebuild_stage_id="quality_gate",
                stale_object_ids=["K-31", "P-24"],
                affected_knowledge_ids=["CK-contract-amount"],
                recommended_actions=["对 stale 的合同金额证据执行候选态增量重算"],
            ),
        ),
    )


def get_p1_impact_set() -> P1ResponseEnvelope[ImpactSet]:
    return _envelope(
        "p1.impact_set.r0",
        ImpactSet(
            impact_set_id="IMPACT-P1-R0-001",
            archive_id=ARCHIVE_ID,
            policy_package_version_id="PKGV-20260508-R0",
            previous_policy_package_version_id="PKGV-20260507-R0",
            changed_rule_ids=["RL-QG-COVERAGE-001"],
            affected_stage_ids=["quality_gate", "publication_candidate"],
            minimum_rebuild_stage_id="quality_gate",
            affected_document_ids=[DOCUMENT_ID],
            affected_object_ids=["K-24", "K-31"],
            affected_relation_ids=["R-11"],
            affected_publication_snapshot_ids=["PCS-P1-R0-001"],
            writes_official_knowledge=False,
        ),
    )


def get_p1_publication_candidate() -> P1ResponseEnvelope[PublicationCandidateSnapshot]:
    return _envelope(
        "p1.publication_candidate.r0",
        PublicationCandidateSnapshot(
            publication_candidate_snapshot_id="PCS-P1-R0-001",
            archive_id=ARCHIVE_ID,
            run_id=RUN_ID,
            generated_at=GENERATED_AT,
            status="candidate",
            governance_status="pending",
            candidate_knowledge_refs=[
                ArtifactRef(artifact_id="CK-contract-amount", artifact_type="canonical_knowledge_candidate")
            ],
            api_exposure_scope=ApiExposureScope(
                readonly_candidate_api_paths=["/api/p1/candidates/knowledge/read", "/api/p1/candidates/graph/search"],
                index_names=["candidate_contract_v3", "candidate_relation_v3"],
            ),
        ),
    )


def get_p1_system_output() -> P1ResponseEnvelope[P1KnowledgeSupplyExport]:
    published_snapshot = PublishedKnowledgeSnapshot(
        published_snapshot_id="REL-P1-R0-001",
        archive_id=ARCHIVE_ID,
        publication_candidate_snapshot_id="PCS-P1-R0-001",
        formal_version="REL-20260508-R0",
        published_at=GENERATED_AT,
        governed_by="governance-confirmation",
        api_paths=["/api/p1/knowledge-supply/read", "/api/p1/knowledge-supply/graph/query"],
    )
    return _envelope(
        "p1.knowledge_supply.v1",
        P1KnowledgeSupplyExport(
            export_id="P1-EXPORT-R0-001",
            archive_id=ARCHIVE_ID,
            contract_version="P1KnowledgeSupplyExport.v1",
            published_snapshot_id=published_snapshot.published_snapshot_id,
            formal_version=published_snapshot.formal_version,
            governed_by=published_snapshot.governed_by,
            published_at=published_snapshot.published_at,
            published_snapshot=published_snapshot,
            formal_knowledge_refs=[
                ArtifactRef(
                    artifact_id="CK-contract-amount",
                    artifact_type="published_knowledge",
                    stage_id="publication",
                    document_id=DOCUMENT_ID,
                    summary="治理确认后的合同总金额正式知识。",
                )
            ],
            quality_report_ref=ArtifactRef(artifact_id=f"KQ-{RUN_ID}", artifact_type="KnowledgeQualityReport"),
            graph_quality_report_ref=ArtifactRef(artifact_id=f"GQ-{RUN_ID}", artifact_type="GraphQualityReport"),
            consumer_systems=["P2RequirementAuthoring", "P6Display"],
            api_base_path="/api/p1/knowledge-supply",
            knowledge_read_path="/api/p1/knowledge-supply/read",
            graph_query_path="/api/p1/knowledge-supply/graph/query",
            generated_at=GENERATED_AT,
        ),
    )


def get_deprecated_p1_system_output() -> P1ResponseEnvelope[P1KnowledgeSupplyExport]:
    payload = get_p1_system_output()
    payload.contract_version = "p1.system_output.r0"
    payload.warnings.append(
        "Deprecated route: use /api/p1/knowledge-supply/read for formal knowledge supply."
    )
    payload.data.deprecation = DeprecatedOutputRoute(
        replacement_path="/api/p1/knowledge-supply/read",
        removal_policy="kept during R0 compatibility window; do not use for new consumers",
    )
    return payload


def get_p1_p6_display_export() -> P1ResponseEnvelope[P6DisplayExportContractV2]:
    supply = get_p1_system_output().data
    return _envelope(
        "p1.p6_display_export.v2",
        P6DisplayExportContractV2(
            export_id="P1-P6-DISPLAY-R0-001",
            source_export_id=supply.export_id,
            contract_version="P6DisplayExportContract.v2",
            published_snapshot_id=supply.published_snapshot_id,
            formal_version=supply.formal_version,
            governed_by=supply.governed_by,
            published_at=supply.published_at,
            graph_summary_path="/api/p1/knowledge-supply/graph/summary",
            entity_lookup_path="/api/p1/knowledge-supply/graph/entities/{entity_id}",
            relation_lookup_path="/api/p1/knowledge-supply/graph/relations/{relation_id}",
            source_trace=[
                ArtifactRef(
                    artifact_id=supply.published_snapshot_id,
                    artifact_type="PublishedKnowledgeSnapshot",
                    summary="P6 展示输出仅来源于正式发布知识快照。",
                )
            ],
        ),
    )
