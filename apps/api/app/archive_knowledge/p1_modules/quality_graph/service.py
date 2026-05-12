from __future__ import annotations

from app.archive_knowledge.contracts import EvaluationRunReport, P1ResponseEnvelope
from app.archive_knowledge.fixtures.p1_refactor import GENERATED_AT, get_p1_resolution_snapshot, get_p1_runtime_snapshot
from app.archive_knowledge.quality import build_evaluation_run_report


class QualityGraphReportService:
    """Builds the W4 quality graph report from runtime snapshot and policy version inputs."""

    def build_report(
        self,
        *,
        archive_id: str,
        runtime_snapshot_id: str,
        policy_package_version_id: str,
    ) -> P1ResponseEnvelope[EvaluationRunReport]:
        runtime_snapshot = get_p1_runtime_snapshot().data.model_copy(deep=True)
        runtime_snapshot.archive_id = archive_id
        runtime_snapshot.run_id = runtime_snapshot_id
        runtime_snapshot.policy_snapshot.archive_id = archive_id
        runtime_snapshot.policy_snapshot.run_id = runtime_snapshot_id
        runtime_snapshot.policy_snapshot.policy_package_version_id = policy_package_version_id
        runtime_snapshot.graph_projection.archive_id = archive_id

        for record in runtime_snapshot.rule_execution_records:
            record.archive_id = archive_id
            record.run_id = runtime_snapshot_id
            record.policy_package_version_id = policy_package_version_id

        resolution_snapshot = get_p1_resolution_snapshot().data.model_copy(deep=True)
        resolution_snapshot.archive_id = archive_id

        return P1ResponseEnvelope[EvaluationRunReport](
            contract_version="p1.quality_graph_report.r0",
            source_kind="fixture",
            generated_at=GENERATED_AT,
            data=build_evaluation_run_report(runtime_snapshot, resolution_snapshot, GENERATED_AT),
        )
