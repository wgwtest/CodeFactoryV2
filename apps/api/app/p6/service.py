from __future__ import annotations

from datetime import UTC, datetime
import re

from app.p6.mock_scenarios import (
    DEFAULT_SCENARIO_ID,
    PORTAL_ARTIFACTS,
    PORTAL_FLOWS,
    STAGE_METADATA,
    STAGE_ORDER,
    get_mock_scenario_catalog,
    get_mock_scenario_definition,
)
from app.p6.models import (
    DisplayBadge,
    KnowledgeContext,
    MockScenarioCatalog,
    MockScenarioSummary,
    ObservationAlertSummary,
    ObservationComparisonItem,
    ObservationProjection,
    ObservationProjectionReadEnvelope,
    ObservationRouteAction,
    ObservationStageCard,
    ParticipantNodePayload,
    PortalDataViewReadEnvelope,
    PortalArtifact,
    PortalFlow,
    PortalNode,
    PortalProjection,
    PortalProjectionReadEnvelope,
    PortalSummary,
    P6DisplayExportContract,
    P6PortalDataFlowSeries,
    P6PortalDataScenarioSummary,
    P6PortalDataStageDetail,
    P6PortalDataStageRow,
    P6PortalDataViewModel,
    P6SimulatorContractSubmission,
    P6SimulatorFlowPoint,
    P6SimulatorHistorySample,
    P6SimulatorSubmissionResponse,
    StageEntryProjection,
    StageFlowPortProjection,
    StageHealthProjection,
    StageLiveCounterProjection,
    StageMetricProjection,
    StageNodeStatusPayload,
    StageOverallMetricProjection,
    StageOverview,
    StageQueueProjection,
    StageSnapshot,
    StageSnapshotReadEnvelope,
)


HEALTH_BADGE_TONES = {
    "healthy": "ready",
    "warning": "warning",
    "blocked": "blocked",
    "unknown": "neutral",
}

SIMULATOR_SCENARIO_ID = "simulator-latest"
_SIMULATOR_SUBMISSION: P6SimulatorContractSubmission | None = None
_SIMULATOR_HISTORY: list[P6SimulatorHistorySample] = []

PORTAL_DATA_FLOW_SPECS = [
    {
        "flow_id": "p1-p2",
        "label": "P1 -> P2",
        "from_stage_id": "P1",
        "to_stage_id": "P2",
        "semantic_type": "knowledge_supply",
        "payload_label": "发布态知识",
        "render_tone": "knowledge",
    },
    {
        "flow_id": "p2-p3",
        "label": "P2 -> P3",
        "from_stage_id": "P2",
        "to_stage_id": "P3",
        "semantic_type": "requirement_to_design",
        "payload_label": "需求规格",
        "render_tone": "analysis",
    },
    {
        "flow_id": "p3-p4",
        "label": "P3 -> P4",
        "from_stage_id": "P3",
        "to_stage_id": "P4",
        "semantic_type": "work_order_package",
        "payload_label": "模块工单包",
        "render_tone": "design",
    },
    {
        "flow_id": "p3-p5",
        "label": "P3 -> P5",
        "from_stage_id": "P3",
        "to_stage_id": "P5",
        "semantic_type": "design_baseline_to_build",
        "payload_label": "设计基线",
        "render_tone": "design",
    },
    {
        "flow_id": "p4-p5",
        "label": "P4 -> P5",
        "from_stage_id": "P4",
        "to_stage_id": "P5",
        "semantic_type": "tool_supply",
        "payload_label": "工具供给",
        "render_tone": "tooling",
    },
    {
        "flow_id": "p5-delivery",
        "label": "P5 -> 交付目录",
        "from_stage_id": "P5",
        "to_stage_id": "交付目录",
        "semantic_type": "delivery_catalog_output",
        "payload_label": "交付目录",
        "render_tone": "delivery",
    },
]

DISPLAY_CONTRACT_PROFILE = {
    "P1": {
        "overview": [
            ("knowledge_repository_count", "知识库", 12, "个", "累计资产"),
            ("published_knowledge_count", "已发布知识", 12480, "条", "累计产出"),
            ("domain_directory_count", "领域", 36, "个", "累计目录"),
            ("contributor_count", "贡献者", 58, "人", "累计贡献"),
        ],
        "live": [
            ("active_knowledge_intake_rate", "正在入库", 8, "条/小时", "1h", "input"),
            ("active_p2_supply_rate", "供给 P2", 5, "条/小时", "1h", "output"),
        ],
        "ports": [
            ("p1_p2_output", "right", "output", "发布态知识", "P2", "5 条/小时", False),
        ],
        "queue": ("p1-knowledge-hook-queue", "知识挂载队列", ["税务规则", "空域约束", "表单库", "资产库", "术语表"]),
        "users": [
            ("role:knowledge-librarian", "库", "知识库管理员"),
            ("role:domain-specialist", "专", "领域专家"),
            ("role:knowledge-reviewer", "审", "知识审核"),
            ("role:collector", "采", "知识采集"),
        ],
        "prototype_ref": "DOC/CODEX_DOC/08_原型与附图/2026-04-29-183315-CodeFactoryV2-P6业务知识库浅色方形头像端口队列卡详情原型-v12/",
        "summary": "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人",
    },
    "P2": {
        "overview": [
            ("supported_software_count", "支持软件", 24, "个", "累计承载"),
            ("requirement_spec_count", "需求规格", 86, "份", "累计产出"),
            ("business_object_count", "业务对象", 430, "个", "累计建模"),
        ],
        "live": [
            ("active_knowledge_receive_rate", "知识接入", 5, "条/小时", "1h", "input"),
            ("active_spec_output_rate", "规格输出", 4, "份/小时", "1h", "output"),
        ],
        "ports": [
            ("p1_knowledge_input", "left", "input", "发布态知识", "P1", "5 条/小时", False),
            ("p2_p3_output", "right", "output", "需求规格", "P3", "4 份/小时", False),
        ],
        "queue": ("p2-modeling-queue", "需求建模队列", ["访谈记录", "领域对象", "模型草案"]),
        "users": [
            ("role:industry-user", "业", "行业用户"),
            ("role:product-owner", "产", "产品负责人"),
            ("role:analyst", "分", "需求分析"),
            ("role:domain-owner", "域", "领域负责人"),
            ("role:requirement-reviewer", "审", "需求评审"),
            ("role:project-manager", "项", "项目管理"),
        ],
        "prototype_ref": "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
        "summary": "支持软件 24 个，需求规格 86 份，业务对象 430 个",
    },
    "P3": {
        "overview": [
            ("supported_software_count", "支持软件", 36, "个", "累计承载"),
            ("design_baseline_count", "设计基线", 112, "份", "累计设计资产"),
            ("work_order_package_count", "工单包", 268, "包", "累计产出"),
        ],
        "live": [
            ("active_requirement_input_rate", "规格接入", 4, "份/小时", "1h", "input"),
            ("active_workorder_output_rate", "工单输出", 5, "包/小时", "1h", "output"),
            ("active_design_baseline_sync_rate", "基线同步", 3, "份/小时", "1h", "output"),
        ],
        "ports": [
            ("p2_requirement_input", "left", "input", "需求规格", "P2", "4 份/小时", False),
            ("p3_p4_output", "right", "output", "模块工单包", "P4", "5 包/小时", False),
            ("p3_p5_baseline_output", "right", "output", "设计基线", "P5", "3 份/小时", False),
        ],
        "queue": ("p3-design-queue", "设计生成队列", ["规范输入", "分析草图", "草案", "评审", "冻结"]),
        "users": [
            ("role:architect", "架", "架构设计"),
            ("role:designer", "设", "软件设计"),
            ("role:reviewer", "审", "设计评审"),
            ("role:modeler", "模", "模型维护"),
            ("role:project-owner", "项", "项目负责人"),
        ],
        "prototype_ref": "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
        "summary": "支持软件 36 个，设计基线 112 份，工单包 268 包",
    },
    "P4": {
        "overview": [
            ("tool_definition_count", "工具定义", 286, "个", "累计工具资产"),
            ("domain_catalog_count", "领域目录", 42, "个", "累计目录"),
            ("tool_supply_result_count", "供给结果", 620, "项", "累计产出"),
        ],
        "live": [
            ("active_matching_rate", "正在匹配", 7, "项/小时", "1h", "process"),
            ("active_supply_output_rate", "工具供给", 4, "项/小时", "1h", "output"),
        ],
        "ports": [
            ("p3_workorder_input", "left", "input", "模块工单包", "P3", "5 包/小时", False),
            ("p4_p5_output", "right", "output", "工具供给", "P5", "4 项/小时", False),
        ],
        "queue": ("p4-supply-queue", "工具供给队列", ["查询", "生成", "验证"]),
        "users": [
            ("role:tool-engineer", "工", "工具工程"),
            ("role:researcher", "研", "工具研究"),
            ("role:tool-reviewer", "审", "工具评审"),
            ("role:maintainer", "维", "工具维护"),
        ],
        "prototype_ref": "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
        "summary": "工具定义 286 个，领域目录 42 个，供给结果 620 项",
    },
    "P5": {
        "overview": [
            ("supported_software_count", "支持软件", 24, "个", "累计承载"),
            ("delivery_version_count", "交付版本", 86, "个", "累计产出"),
            ("build_attempt_count", "构建尝试", 412, "次", "累计运行事实"),
        ],
        "live": [
            ("active_assembly_count", "正在装配", 4, "项", "now", "process"),
            ("delivery_catalog_output_rate", "目录输出", 2, "个/日", "1d", "output"),
        ],
        "ports": [
            ("p4_tool_supply_input", "left", "input", "工具供给", "P4", "4 项/小时", False),
            ("p3_baseline_input", "left", "input", "设计基线", "P3", "3 份/小时", False),
            ("delivery_catalog_output", "right", "output", "交付目录", "交付目录", "2 个/日", True),
        ],
        "queue": ("p5-build-queue", "构建交付队列", ["装配", "测试", "打包", "发布"]),
        "users": [
            ("role:builder", "构", "构建人员"),
            ("role:tester", "测", "测试人员"),
            ("role:release", "发", "发布人员"),
            ("role:version-manager", "版", "版本管理"),
        ],
        "prototype_ref": "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
        "summary": "支持软件 24 个，交付版本 86 个，构建尝试 412 次",
    },
}


def _metric_to_legacy(metric: StageOverallMetricProjection) -> StageMetricProjection:
    return StageMetricProjection(
        metric_key=metric.key,
        metric_label=metric.label,
        metric_value=f"{metric.value}{metric.unit}",
    )


class P6ProjectionService:
    def list_mock_scenarios(self) -> MockScenarioCatalog:
        items = [MockScenarioSummary.model_validate(item) for item in get_mock_scenario_catalog()]
        if _SIMULATOR_SUBMISSION is not None:
            items.append(
                MockScenarioSummary(
                    scenario_id=_SIMULATOR_SUBMISSION.scenario_id,
                    label=_SIMULATOR_SUBMISSION.label,
                    description=_SIMULATOR_SUBMISSION.description,
                    source_mode="mock",
                    recommended_focus_stage=_SIMULATOR_SUBMISSION.recommended_focus_stage,
                )
            )
        return MockScenarioCatalog(
            source_mode="mock",
            default_scenario_id=DEFAULT_SCENARIO_ID,
            items=items,
        )

    def submit_simulator_contracts(self, payload: P6SimulatorContractSubmission) -> P6SimulatorSubmissionResponse:
        if len(payload.contracts) != len(STAGE_ORDER):
            raise ValueError("P6 simulator requires exactly five stage contracts")

        stage_ids = [contract.stage_overview.stage_id for contract in payload.contracts]
        if stage_ids != STAGE_ORDER:
            raise ValueError("P6 simulator contracts must be ordered as P1, P2, P3, P4, P5")

        for contract in payload.contracts:
            self._validate_contract_ports(contract)

        global _SIMULATOR_SUBMISSION
        _SIMULATOR_SUBMISSION = payload
        captured_at = self._resolve_history_captured_at(payload.contracts)
        _SIMULATOR_HISTORY.append(
            P6SimulatorHistorySample(
                sample_id=f"{payload.scenario_id}-{len(_SIMULATOR_HISTORY) + 1}",
                scenario_id=payload.scenario_id,
                captured_at=captured_at,
                stage_contracts=payload.contracts,
                flow_points=self._build_simulator_flow_points(payload.contracts, captured_at),
                source_label=payload.label,
            )
        )
        scenario = MockScenarioSummary(
            scenario_id=payload.scenario_id,
            label=payload.label,
            description=payload.description,
            source_mode="mock",
            recommended_focus_stage=payload.recommended_focus_stage,
        )
        return P6SimulatorSubmissionResponse(
            scenario=scenario,
            accepted_contract_count=len(payload.contracts),
            portal_projection_path=f"/portal?scenario={payload.scenario_id}",
            portal_data_path=f"/portal-data?scenario={payload.scenario_id}",
        )

    def get_stage_snapshots(self, source: str = "mock", scenario: str = DEFAULT_SCENARIO_ID) -> StageSnapshotReadEnvelope:
        scenario_summary, scenario_definition = self._resolve_scenario(source, scenario)
        snapshots = self._build_stage_snapshots(scenario_definition)
        return StageSnapshotReadEnvelope(
            source_mode="mock",
            scenario=scenario_summary,
            items=snapshots,
            projection_at=snapshots[-1].projection_at,
            freshness=self._resolve_projection_freshness(snapshots),
            degraded_reason=self._resolve_projection_degraded_reason(snapshots),
        )

    def get_portal_projection(self, source: str = "mock", scenario: str = DEFAULT_SCENARIO_ID) -> PortalProjectionReadEnvelope:
        scenario_summary, scenario_definition = self._resolve_scenario(source, scenario)
        snapshots = self._build_stage_snapshots(scenario_definition)
        projection = PortalProjection(
            node_list=self._build_portal_nodes(scenario_summary, scenario_definition, snapshots),
            flow_list=[PortalFlow.model_validate(flow) for flow in PORTAL_FLOWS],
            artifact_list=[PortalArtifact.model_validate(artifact) for artifact in PORTAL_ARTIFACTS],
            portal_summary=self._build_portal_summary(scenario_summary, scenario_definition),
            knowledge_context=self._build_knowledge_context(scenario_definition, snapshots),
            freshness=self._resolve_projection_freshness(snapshots),
            degraded_reason=self._resolve_projection_degraded_reason(snapshots),
        )
        return PortalProjectionReadEnvelope(source_mode="mock", scenario=scenario_summary, projection=projection)

    def get_portal_data_view(
        self,
        source: str = "mock",
        scenario: str = DEFAULT_SCENARIO_ID,
        selected_stage_id: str = "P3",
    ) -> PortalDataViewReadEnvelope:
        scenario_summary, scenario_definition = self._resolve_scenario(source, scenario)
        snapshots = self._build_stage_snapshots(scenario_definition)
        scenario_history = [sample for sample in _SIMULATOR_HISTORY if sample.scenario_id == scenario_summary.scenario_id]
        stage_rows = [self._build_portal_data_stage_row(snapshot) for snapshot in snapshots]
        flow_series = self._build_portal_data_flow_series(scenario_history)
        selected_detail = self._build_portal_data_stage_detail(selected_stage_id, snapshots, scenario_history)
        projection_at = snapshots[-1].projection_at if snapshots else datetime.now(UTC).isoformat()
        view = P6PortalDataViewModel(
            scenario_summary=P6PortalDataScenarioSummary(
                scenario_id=scenario_summary.scenario_id,
                label=scenario_summary.label,
                source_label="模拟源",
                stage_count=len(stage_rows),
                flow_count=len(flow_series),
                connected_user_count=sum(row.connected_user_count for row in stage_rows),
                queue_item_count=sum(row.queue_item_count for row in stage_rows),
                history_sample_count=len(scenario_history),
                captured_at=projection_at,
            ),
            stage_rows=stage_rows,
            flow_series=flow_series,
            selected_stage_detail=selected_detail,
            history_sample_count=len(scenario_history),
        )
        return PortalDataViewReadEnvelope(source_mode="mock", scenario=scenario_summary, view=view)

    def get_observation_projection(
        self,
        source: str = "mock",
        scenario: str = DEFAULT_SCENARIO_ID,
    ) -> ObservationProjectionReadEnvelope:
        scenario_summary, scenario_definition = self._resolve_scenario(source, scenario)
        snapshots = self._build_stage_snapshots(scenario_definition)
        warning_stage_ids = [
            snapshot.stage_id for snapshot in snapshots if snapshot.health_projection.health_level == "warning"
        ]
        blocked_stage_ids = [
            snapshot.stage_id for snapshot in snapshots if snapshot.health_projection.health_level == "blocked"
        ]
        projection = ObservationProjection(
            stage_cards=[
                ObservationStageCard(
                    stage_id=snapshot.stage_id,
                    stage_name=snapshot.stage_name,
                    headline_value=snapshot.node_status_payload.headline_value,
                    summary_line=snapshot.node_status_payload.summary_line,
                    primary_status=snapshot.primary_status,
                    freshness=snapshot.freshness,
                    entry_badge=snapshot.node_status_payload.entry_badge,
                    health_badge=snapshot.node_status_payload.health_badge,
                    timestamp_label=snapshot.node_status_payload.timestamp_label,
                    degraded_hint=snapshot.node_status_payload.degraded_hint,
                )
                for snapshot in snapshots
            ],
            comparison_items=self._build_comparison_items(snapshots),
            alert_summary=ObservationAlertSummary(
                total=len(warning_stage_ids) + len(blocked_stage_ids),
                warning_stage_ids=warning_stage_ids,
                blocked_stage_ids=blocked_stage_ids,
                message=str(scenario_definition["portal_alert_message"]),
            ),
            route_actions=[
                ObservationRouteAction(
                    stage_id=snapshot.stage_id,
                    label=f"进入 {snapshot.stage_name}",
                    route=snapshot.entry_projection.entry_route,
                    route_available=snapshot.entry_projection.entry_available,
                )
                for snapshot in snapshots
            ],
            focus_stage_id=scenario_summary.recommended_focus_stage,
            freshness=self._resolve_projection_freshness(snapshots),
            degraded_reason=self._resolve_projection_degraded_reason(snapshots),
        )
        return ObservationProjectionReadEnvelope(source_mode="mock", scenario=scenario_summary, projection=projection)

    def _resolve_scenario(self, source: str, scenario: str) -> tuple[MockScenarioSummary, dict[str, object]]:
        if source == "live":
            raise NotImplementedError("P6 live source is not implemented yet")
        if source != "mock":
            raise ValueError(f"Unsupported P6 source mode: {source}")
        if _SIMULATOR_SUBMISSION is not None and scenario == _SIMULATOR_SUBMISSION.scenario_id:
            return (
                MockScenarioSummary(
                    scenario_id=_SIMULATOR_SUBMISSION.scenario_id,
                    label=_SIMULATOR_SUBMISSION.label,
                    description=_SIMULATOR_SUBMISSION.description,
                    source_mode="mock",
                    recommended_focus_stage=_SIMULATOR_SUBMISSION.recommended_focus_stage,
                ),
                {
                    "contracts": _SIMULATOR_SUBMISSION.contracts,
                    "portal_alert_message": _SIMULATOR_SUBMISSION.description,
                    "archive_label": "合同模拟器",
                    "context_hint": f"模拟源 · {_SIMULATOR_SUBMISSION.label}",
                },
            )
        scenario_definition = get_mock_scenario_definition(scenario)
        if scenario_definition is None:
            raise ValueError(f"P6 mock scenario not found: {scenario}")
        return MockScenarioSummary.model_validate(scenario_definition["summary"]), scenario_definition

    def _build_stage_snapshots(self, scenario_definition: dict[str, object]) -> list[StageSnapshot]:
        if "contracts" in scenario_definition:
            return self._build_stage_snapshots_from_contracts(
                scenario_definition["contracts"],  # type: ignore[arg-type]
                str(scenario_definition["portal_alert_message"]),
            )

        stage_states = dict(scenario_definition["stages"])
        snapshots: list[StageSnapshot] = []
        for stage_id in STAGE_ORDER:
            metadata = STAGE_METADATA[stage_id]
            state = dict(stage_states[stage_id])
            contract = self._build_mock_display_contract(stage_id, metadata, state)
            metrics = [_metric_to_legacy(metric) for metric in contract.system_overall_metrics[:2]]
            entry_projection = StageEntryProjection(
                entry_route=str(metadata["route"]),
                entry_available=bool(state["entry_available"]),
                entry_reason=str(state["entry_reason"]),
            )
            node_payload = StageNodeStatusPayload(
                stage_id=stage_id,
                headline_value=contract.stage_overview.summary,
                summary_line=str(state["summary_line"]),
                metric_items=metrics,
                system_overall_metric_items=contract.system_overall_metrics,
                live_counter_items=contract.live_counters,
                flow_port_items=contract.flow_ports,
                connected_user_items=contract.connected_users,
                queue_projection=contract.queue_projection,
                display_binding=contract.display_binding,
                source_trace=contract.source_trace,
                entry_badge=DisplayBadge(
                    label=str(state["entry_reason"]),
                    tone="ready" if entry_projection.entry_available else "blocked",
                ),
                health_badge=DisplayBadge(
                    label=str(state["health_badge_label"]),
                    tone=HEALTH_BADGE_TONES[str(state["health_level"])],
                    detail=str(state["health_message"]),
                ),
                timestamp_label=str(state["timestamp_label"]),
                degraded_hint=state.get("degraded_hint"),
            )
            snapshots.append(
                StageSnapshot(
                    snapshot_id=f"{stage_id.lower()}-snapshot-{scenario_definition['summary']['scenario_id']}",
                    stage_id=stage_id,
                    stage_name=str(metadata["stage_name"]),
                    primary_status=str(state["primary_status"]),
                    summary=str(state["summary"]),
                    entry_projection=entry_projection,
                    metric_list=metrics,
                    health_projection=StageHealthProjection(
                        health_level=str(state["health_level"]),
                        health_message=str(state["health_message"]),
                        health_source="p6_mock_source",
                        captured_at=str(state["captured_at"]),
                    ),
                    captured_at=str(state["captured_at"]),
                    projection_at=str(state["updated_at"]),
                    freshness=str(state["freshness"]),
                    degraded_reason=state.get("degraded_hint"),
                    node_status_payload=node_payload,
                    display_contract=contract,
                )
            )
        return snapshots

    def _build_stage_snapshots_from_contracts(
        self,
        contracts: list[P6DisplayExportContract],
        alert_message: str,
    ) -> list[StageSnapshot]:
        snapshots: list[StageSnapshot] = []
        for contract in contracts:
            overview = contract.stage_overview
            metrics = [_metric_to_legacy(metric) for metric in contract.system_overall_metrics[:2]]
            node_payload = StageNodeStatusPayload(
                stage_id=overview.stage_id,
                headline_value=overview.summary,
                summary_line=contract.health_projection.health_message,
                metric_items=metrics,
                system_overall_metric_items=contract.system_overall_metrics,
                live_counter_items=contract.live_counters,
                flow_port_items=contract.flow_ports,
                connected_user_items=contract.connected_users,
                queue_projection=contract.queue_projection,
                display_binding=contract.display_binding,
                source_trace=contract.source_trace,
                entry_badge=DisplayBadge(
                    label=contract.entry_projection.entry_reason,
                    tone="ready" if contract.entry_projection.entry_available else "blocked",
                ),
                health_badge=DisplayBadge(
                    label=self._health_badge_label(contract.health_projection.health_level),
                    tone=HEALTH_BADGE_TONES[contract.health_projection.health_level],
                    detail=contract.health_projection.health_message,
                ),
                timestamp_label=overview.updated_at,
                degraded_hint=None if contract.health_projection.health_level == "healthy" else alert_message,
            )
            snapshots.append(
                StageSnapshot(
                    snapshot_id=f"{overview.stage_id.lower()}-snapshot-simulator",
                    stage_id=overview.stage_id,
                    stage_name=overview.stage_display_name,
                    primary_status=overview.primary_status,
                    summary=overview.summary,
                    entry_projection=contract.entry_projection,
                    metric_list=metrics,
                    health_projection=contract.health_projection,
                    captured_at=contract.health_projection.captured_at,
                    projection_at=overview.updated_at,
                    freshness=overview.freshness,
                    degraded_reason=node_payload.degraded_hint,
                    node_status_payload=node_payload,
                    display_contract=contract,
                )
            )
        return snapshots

    def _build_portal_nodes(
        self,
        scenario_summary: MockScenarioSummary,
        scenario_definition: dict[str, object],
        snapshots: list[StageSnapshot],
    ) -> list[PortalNode]:
        nodes = []
        for snapshot in snapshots:
            metadata = STAGE_METADATA[snapshot.stage_id]
            nodes.append(
                PortalNode(
                    node_id=str(metadata["node_id"]),
                    node_kind="module",
                    title=str(metadata["stage_name"]),
                    stage_id=snapshot.stage_id,
                    route=str(metadata["route"]),
                    projection_mode="auto",
                    summary=snapshot.summary,
                    primary_status=snapshot.primary_status,
                    freshness=snapshot.freshness,
                    description=str(metadata["description"]),
                    stage_card=snapshot.node_status_payload,
                )
            )
        return nodes

    def _build_portal_summary(
        self,
        scenario_summary: MockScenarioSummary,
        scenario_definition: dict[str, object],
    ) -> PortalSummary:
        return PortalSummary(
            headline="P6 首屏观察门户",
            source_label="模拟源",
            scenario_label=scenario_summary.label,
            module_count=5,
            user_count=self._resolve_connected_user_count(scenario_definition),
            artifact_count=len(PORTAL_ARTIFACTS),
            flow_count=len(PORTAL_FLOWS),
            focus_hint=f"建议优先关注 {scenario_summary.recommended_focus_stage}",
            alert_message=str(scenario_definition["portal_alert_message"]),
        )

    def _build_knowledge_context(
        self,
        scenario_definition: dict[str, object],
        snapshots: list[StageSnapshot],
    ) -> KnowledgeContext:
        p1_snapshot = next(snapshot for snapshot in snapshots if snapshot.stage_id == "P1")
        return KnowledgeContext(
            current_knowledge_base_name=p1_snapshot.node_status_payload.headline_value,
            archive_label=str(scenario_definition["archive_label"]),
            context_hint=str(scenario_definition["context_hint"]),
        )

    def _build_comparison_items(self, snapshots: list[StageSnapshot]) -> list[ObservationComparisonItem]:
        available_entry_count = sum(1 for snapshot in snapshots if snapshot.entry_projection.entry_available)
        warning_count = sum(1 for snapshot in snapshots if snapshot.health_projection.health_level == "warning")
        blocked_count = sum(1 for snapshot in snapshots if snapshot.health_projection.health_level == "blocked")
        return [
            ObservationComparisonItem(
                comparison_id="entry-available",
                label="可用入口",
                value=f"{available_entry_count}/{len(snapshots)}",
                tone="ready" if available_entry_count == len(snapshots) else "warning",
            ),
            ObservationComparisonItem(
                comparison_id="warning-stage-count",
                label="注意阶段",
                value=str(warning_count),
                tone="warning" if warning_count else "neutral",
            ),
            ObservationComparisonItem(
                comparison_id="blocked-stage-count",
                label="阻塞阶段",
                value=str(blocked_count),
                tone="blocked" if blocked_count else "neutral",
            ),
        ]

    def _resolve_projection_freshness(self, snapshots: list[StageSnapshot]) -> str:
        if any(snapshot.freshness == "stale" for snapshot in snapshots):
            return "stale"
        if any(snapshot.freshness == "unknown" for snapshot in snapshots):
            return "unknown"
        return "fresh"

    def _resolve_projection_degraded_reason(self, snapshots: list[StageSnapshot]) -> str | None:
        reasons = [snapshot.degraded_reason for snapshot in snapshots if snapshot.degraded_reason]
        return reasons[0] if reasons else None

    def _build_mock_display_contract(
        self,
        stage_id: str,
        metadata: dict[str, object],
        state: dict[str, object],
    ) -> P6DisplayExportContract:
        profile = DISPLAY_CONTRACT_PROFILE[stage_id]
        system_overall_metrics = [
            StageOverallMetricProjection(key=key, label=label, value=value, unit=unit, basis=basis)
            for key, label, value, unit, basis in profile["overview"]
        ]
        live_counters = [
            StageLiveCounterProjection(key=key, label=label, value=value, unit=unit, window=window, direction=direction)
            for key, label, value, unit, window, direction in profile["live"]
        ]
        flow_ports = [
            StageFlowPortProjection(
                port_id=port_id,
                side=side,
                direction=direction,
                label=label,
                connected_target=target,
                current_rate=rate,
                terminal=terminal,
            )
            for port_id, side, direction, label, target, rate, terminal in profile["ports"]
        ]
        connected_users = [
            {
                "user_ref": user_ref,
                "display_label": display_label,
                "role_label": role_label,
                "activity_state": "active",
                "connected_at": str(state["captured_at"]),
            }
            for user_ref, display_label, role_label in profile["users"]
        ]
        queue_id, queue_label, queue_items = profile["queue"]
        queue_projection = StageQueueProjection(
            queue_id=queue_id,
            label=queue_label,
            items=[
                {
                    "item_id": f"{queue_id}-{index}",
                    "label": label,
                    "state": "active" if index == 0 else "waiting",
                    "order_index": index,
                }
                for index, label in enumerate(queue_items)
            ],
            active_index=0,
            advance_rule="active_done_then_shift_left",
        )
        return P6DisplayExportContract(
            contract_version="P6DisplayExportContract.v2",
            stage_overview=StageOverview(
                stage_id=stage_id,
                stage_name=str(metadata["stage_name"]),
                stage_display_name=str(metadata["stage_name"]),
                primary_status=str(state["primary_status"]),
                summary=str(profile["summary"]),
                updated_at=str(state["updated_at"]),
                freshness=str(state["freshness"]),
            ),
            entry_projection=StageEntryProjection(
                entry_route=str(metadata["route"]),
                entry_available=bool(state["entry_available"]),
                entry_reason=str(state["entry_reason"]),
            ),
            system_overall_metrics=system_overall_metrics,
            live_counters=live_counters,
            flow_ports=flow_ports,
            connected_users=connected_users,
            queue_projection=queue_projection,
            display_binding={
                "prototype_refs": [str(profile["prototype_ref"])],
                "regions": {
                    "top_participants": "connected_users",
                    "middle_overall": "system_overall_metrics",
                    "lower_realtime": "live_counters",
                    "left_input_port": "flow_ports[input]" if any(port.direction == "input" for port in flow_ports) else "queue_projection",
                    "right_output_port": "flow_ports[output]",
                    "bottom_queue": "queue_projection",
                },
            },
            health_projection=StageHealthProjection(
                health_level=str(state["health_level"]),
                health_message=str(state["health_message"]),
                health_source="p6_mock_source",
                captured_at=str(state["captured_at"]),
            ),
            source_trace=[
                {
                    "field": f"system_overall_metrics.{metric.key}",
                    "source_doc": f"DOC/CODEX_DOC/02_设计说明/{stage_id}_{metadata['stage_name']}/{stage_id}-{metadata['stage_name']}设计.md",
                    "source_object": metric.label,
                    "calculation_basis": metric.basis,
                    "freshness_policy": "mock-fresh",
                    "display_reason": "绑定详情卡中段总体状态",
                }
                for metric in system_overall_metrics
            ],
            stage_specific={metric.key: metric.value for metric in system_overall_metrics},
        )

    def _build_portal_data_stage_row(self, snapshot: StageSnapshot) -> P6PortalDataStageRow:
        payload = snapshot.node_status_payload
        input_counters = [counter for counter in payload.live_counter_items if counter.direction == "input"]
        process_counters = [counter for counter in payload.live_counter_items if counter.direction == "process"]
        output_ports = [port for port in payload.flow_port_items if port.direction == "output"]
        queue_item_count = len(payload.queue_projection.items) if payload.queue_projection else 0
        return P6PortalDataStageRow(
            stage_id=snapshot.stage_id,
            stage_name=snapshot.stage_name,
            primary_status=snapshot.primary_status,
            health_level=snapshot.health_projection.health_level,
            overall_status=payload.headline_value,
            realtime_input=self._format_live_counters(input_counters),
            processing_status=self._format_live_counters(process_counters) or snapshot.health_projection.health_message,
            output_flow=self._format_output_ports(output_ports),
            connected_user_count=len(payload.connected_user_items),
            queue_item_count=queue_item_count,
            updated_at=snapshot.projection_at,
        )

    def _build_portal_data_flow_series(
        self,
        history_samples: list[P6SimulatorHistorySample],
    ) -> list[P6PortalDataFlowSeries]:
        return [
            P6PortalDataFlowSeries(
                flow_id=str(spec["flow_id"]),
                label=str(spec["label"]),
                from_stage_id=str(spec["from_stage_id"]),
                to_stage_id=str(spec["to_stage_id"]),
                semantic_type=str(spec["semantic_type"]),
                payload_label=str(spec["payload_label"]),
                render_tone=str(spec["render_tone"]),
                points=[
                    point
                    for sample in history_samples
                    for point in sample.flow_points
                    if point.flow_id == spec["flow_id"]
                ],
            )
            for spec in PORTAL_DATA_FLOW_SPECS
        ]

    def _build_portal_data_stage_detail(
        self,
        selected_stage_id: str,
        snapshots: list[StageSnapshot],
        history_samples: list[P6SimulatorHistorySample],
    ) -> P6PortalDataStageDetail:
        snapshot = next((item for item in snapshots if item.stage_id == selected_stage_id), snapshots[0])
        payload = snapshot.node_status_payload
        recent_points = [
            point
            for sample in history_samples[-3:]
            for point in sample.flow_points
            if point.from_stage_id == snapshot.stage_id or point.to_stage_id == snapshot.stage_id
        ]
        return P6PortalDataStageDetail(
            stage_id=snapshot.stage_id,
            stage_name=snapshot.stage_name,
            summary=snapshot.summary,
            overall_metrics=payload.system_overall_metric_items,
            live_counters=payload.live_counter_items,
            flow_ports=payload.flow_port_items,
            connected_users=payload.connected_user_items,
            queue_projection=payload.queue_projection,
            source_trace=payload.source_trace,
            display_contract=snapshot.display_contract,
            recent_flow_points=recent_points,
        )

    def _build_simulator_flow_points(
        self,
        contracts: list[P6DisplayExportContract],
        captured_at: str,
    ) -> list[P6SimulatorFlowPoint]:
        contracts_by_stage = {contract.stage_overview.stage_id: contract for contract in contracts}
        points: list[P6SimulatorFlowPoint] = []
        for spec in PORTAL_DATA_FLOW_SPECS:
            contract = contracts_by_stage.get(str(spec["from_stage_id"]))
            if contract is None:
                continue
            output_port = next(
                (
                    port
                    for port in contract.flow_ports
                    if port.direction == "output" and port.connected_target == spec["to_stage_id"]
                ),
                None,
            )
            if output_port is None:
                continue

            value, unit = self._parse_rate_label(output_port.current_rate)
            points.append(
                P6SimulatorFlowPoint(
                    flow_id=str(spec["flow_id"]),
                    from_stage_id=str(spec["from_stage_id"]),
                    to_stage_id=str(spec["to_stage_id"]),
                    semantic_type=str(spec["semantic_type"]),
                    payload_label=str(spec["payload_label"]),
                    value=value,
                    unit=unit,
                    rate_label=output_port.current_rate,
                    captured_at=captured_at,
                )
            )
        return points

    def _resolve_history_captured_at(self, contracts: list[P6DisplayExportContract]) -> str:
        captured_values = [contract.health_projection.captured_at for contract in contracts if contract.health_projection.captured_at]
        return captured_values[-1] if captured_values else datetime.now(UTC).isoformat()

    def _parse_rate_label(self, rate_label: str) -> tuple[int | float, str]:
        matched = re.match(r"\s*(\d+(?:\.\d+)?)\s*(.*)\s*$", rate_label)
        if matched is None:
            return 0, rate_label
        raw_value = float(matched.group(1))
        value: int | float = int(raw_value) if raw_value.is_integer() else raw_value
        return value, matched.group(2)

    def _format_live_counters(self, counters: list[StageLiveCounterProjection]) -> str:
        return "；".join(f"{counter.label} {counter.value}{counter.unit}" for counter in counters)

    def _format_output_ports(self, ports: list[StageFlowPortProjection]) -> str:
        return "；".join(f"{port.label} -> {port.connected_target} {port.current_rate}" for port in ports)

    def _validate_contract_ports(self, contract: P6DisplayExportContract) -> None:
        expected_outputs = {
            "P1": ("P2", False),
            "P2": ("P3", False),
            "P3": ("P4", False),
            "P4": ("P5", False),
            "P5": ("交付目录", True),
        }
        expected_target, expected_terminal = expected_outputs[contract.stage_overview.stage_id]
        output_ports = [port for port in contract.flow_ports if port.direction == "output"]
        main_output_ports = [
            port for port in output_ports if port.connected_target == expected_target and port.terminal == expected_terminal
        ]
        if len(main_output_ports) != 1:
            raise ValueError(f"{contract.stage_overview.stage_id} output port must target {expected_target}")
        extra_output_targets = {port.connected_target for port in output_ports if port not in main_output_ports}
        allowed_extra_targets = {"P3": {"P5"}}.get(contract.stage_overview.stage_id, set())
        if extra_output_targets - allowed_extra_targets:
            raise ValueError(f"{contract.stage_overview.stage_id} exposes unsupported output targets")
        if contract.stage_overview.stage_id == "P1":
            input_ports = [port for port in contract.flow_ports if port.direction == "input"]
            if input_ports:
                raise ValueError("P1 must express external knowledge intake through queue_projection, not an input port")

    def _health_badge_label(self, health_level: str) -> str:
        return {
            "healthy": "健康",
            "warning": "注意",
            "blocked": "阻塞",
            "unknown": "未知",
        }[health_level]

    def _resolve_connected_user_count(self, scenario_definition: dict[str, object]) -> int:
        if "contracts" in scenario_definition:
            contracts = scenario_definition["contracts"]
            return sum(len(contract.connected_users) for contract in contracts)  # type: ignore[union-attr]
        return sum(len(profile["users"]) for profile in DISPLAY_CONTRACT_PROFILE.values())
