from __future__ import annotations

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
    PortalArtifact,
    PortalFlow,
    PortalNode,
    PortalProjection,
    PortalProjectionReadEnvelope,
    PortalSummary,
    StageEntryProjection,
    StageHealthProjection,
    StageMetricProjection,
    StageNodeStatusPayload,
    StageSnapshot,
    StageSnapshotReadEnvelope,
)


HEALTH_BADGE_TONES = {
    "healthy": "ready",
    "warning": "warning",
    "blocked": "blocked",
    "unknown": "neutral",
}


class P6ProjectionService:
    def list_mock_scenarios(self) -> MockScenarioCatalog:
        return MockScenarioCatalog(
            source_mode="mock",
            default_scenario_id=DEFAULT_SCENARIO_ID,
            items=[MockScenarioSummary.model_validate(item) for item in get_mock_scenario_catalog()],
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
        scenario_definition = get_mock_scenario_definition(scenario)
        if scenario_definition is None:
            raise ValueError(f"P6 mock scenario not found: {scenario}")
        return MockScenarioSummary.model_validate(scenario_definition["summary"]), scenario_definition

    def _build_stage_snapshots(self, scenario_definition: dict[str, object]) -> list[StageSnapshot]:
        stage_states = dict(scenario_definition["stages"])
        snapshots: list[StageSnapshot] = []
        for stage_id in STAGE_ORDER:
            metadata = STAGE_METADATA[stage_id]
            state = dict(stage_states[stage_id])
            metrics = [StageMetricProjection.model_validate(metric) for metric in state["metrics"]]
            entry_projection = StageEntryProjection(
                entry_route=str(metadata["route"]),
                entry_available=bool(state["entry_available"]),
                entry_reason=str(state["entry_reason"]),
            )
            node_payload = StageNodeStatusPayload(
                stage_id=stage_id,
                headline_value=str(state["headline_value"]),
                summary_line=str(state["summary_line"]),
                metric_items=metrics,
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
                )
            )
        return snapshots

    def _build_portal_nodes(
        self,
        scenario_summary: MockScenarioSummary,
        scenario_definition: dict[str, object],
        snapshots: list[StageSnapshot],
    ) -> list[PortalNode]:
        nodes = [
            PortalNode(
                node_id="user",
                node_kind="user",
                title="行业用户",
                projection_mode="manual",
                summary="以业务语言提出目标并进入平台主链。",
                description="门户中的参与角色节点，不承担系统级指标展示。",
                participant_payload=ParticipantNodePayload(
                    role_label="参与角色",
                    title="行业用户",
                    context_label=str(scenario_definition["context_hint"]),
                    interaction_hints=["提出目标", "确认对象", "进入需求"],
                    availability_hint="持续接入",
                ),
            )
        ]
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
            user_count=1,
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
