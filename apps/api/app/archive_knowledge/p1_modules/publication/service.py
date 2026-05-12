from __future__ import annotations

import re

from app.archive_knowledge.contracts import (
    ApiExposureScope,
    ArtifactRef,
    GovernanceStatusProjection,
    P1ResponseEnvelope,
    PublicationCandidateObject,
    PublicationCandidateRelation,
    PublicationCandidateSnapshot,
    PublicationCandidateSummary,
    PublicationQualityDecisionSummary,
)
from app.archive_knowledge.fixtures import get_p1_evaluation_report, get_p1_resolution_snapshot, get_p1_runtime_snapshot


class P1PublicationCandidateService:
    """Builds candidate-only publication snapshots from stable runtime contracts."""

    def build_latest_candidate_envelope(
        self,
        *,
        archive_id: str,
        runtime_snapshot_id: str | None = None,
        policy_package_version_id: str | None = None,
    ) -> P1ResponseEnvelope[PublicationCandidateSnapshot]:
        runtime_envelope = get_p1_runtime_snapshot()
        runtime = runtime_envelope.data
        runtime.archive_id = archive_id
        runtime.policy_snapshot.archive_id = archive_id

        source_runtime_snapshot_id = runtime_snapshot_id or runtime.run_id
        source_policy_package_version_id = policy_package_version_id or runtime.policy_snapshot.policy_package_version_id
        evaluation = get_p1_evaluation_report(archive_id=archive_id, run_id=runtime.run_id).data
        quality_finding_report = evaluation.quality_finding_report
        resolution_envelope = get_p1_resolution_snapshot()
        resolution = resolution_envelope.data
        resolution.archive_id = archive_id
        resolution.run_id = runtime.run_id
        resolution.runtime_snapshot_id = source_runtime_snapshot_id
        resolution.policy_package_version_id = source_policy_package_version_id
        gate_decision = evaluation.gate_decision
        candidate_objects = self._candidate_objects_from_resolution(
            resolution,
            output_action=gate_decision.output_action,
        )
        candidate_relations = self._candidate_relations_from_resolution(
            resolution,
            output_action=gate_decision.output_action,
        )
        candidate_refs = self._candidate_refs_from_resolution(resolution)
        if not candidate_refs:
            candidate_refs = self._candidate_refs_from_runtime(runtime.rule_execution_records)
        publication_snapshot_id = self._build_publication_snapshot_id(archive_id, source_runtime_snapshot_id)
        should_publish_candidate = gate_decision.output_action in {
            "publish_candidate",
            "publish_candidate_with_warning",
        }
        is_stale_after_policy_change = source_policy_package_version_id != runtime.policy_snapshot.policy_package_version_id
        publication_status = self._publication_status(
            output_action=gate_decision.output_action,
            should_publish_candidate=should_publish_candidate,
            stale_after_policy_change=is_stale_after_policy_change,
        )

        governance_projection = GovernanceStatusProjection(
            governance_confirmation_status="waiting_confirmation" if should_publish_candidate else "not_ready",
            governance_confirmation_label="等待治理确认" if should_publish_candidate else "未进入治理确认",
            formal_entry_status="not_admitted",
            formal_entry_label="尚未正式入库",
            confirmation_required=True,
        )
        candidate_summary = PublicationCandidateSummary(
            publication_snapshot_id=publication_snapshot_id if should_publish_candidate else None,
            status_label="机器已发布候选" if should_publish_candidate else "质量门禁未放行候选",
            source_scope="post_quality_gate_publication_candidate",
            generated_from_runtime_snapshot_id=source_runtime_snapshot_id,
            candidate_count=self._candidate_count(runtime, candidate_objects, candidate_refs),
            candidate_knowledge_count=len(candidate_objects) or len(candidate_refs),
        )
        quality_decision = PublicationQualityDecisionSummary(
            decision=gate_decision.decision,
            output_action=gate_decision.output_action,
            score=gate_decision.score,
            explanation=gate_decision.explanation,
            affected_object_ids=gate_decision.affected_object_ids,
            affected_relation_ids=gate_decision.affected_relation_ids,
        )

        payload = PublicationCandidateSnapshot(
            publication_candidate_snapshot_id=publication_snapshot_id,
            publication_snapshot_id=publication_snapshot_id if should_publish_candidate else None,
            archive_id=archive_id,
            run_id=runtime.run_id,
            runtime_snapshot_id=source_runtime_snapshot_id,
            policy_package_version_id=source_policy_package_version_id,
            resolution_snapshot_id=resolution.snapshot_id,
            generated_at=evaluation.generated_at,
            status=publication_status,
            governance_status="pending",
            candidate_summary=candidate_summary,
            quality_decision_summary=quality_decision,
            quality_decision=quality_decision,
            quality_finding_report=quality_finding_report,
            governance_projection=governance_projection,
            candidate_objects=candidate_objects,
            candidate_relations=candidate_relations,
            candidate_knowledge_refs=candidate_refs,
            api_exposure_scope=ApiExposureScope(
                readonly_candidate_api_paths=[
                    "/api/p1/candidates/knowledge/read",
                    "/api/p1/candidates/graph/search",
                    "/api/p1/archives/{archive_id}/publication-candidates/latest",
                ],
                readonly_formal_api_paths=[],
                index_names=[
                    f"candidate_{self._slug(archive_id)}_knowledge",
                    f"candidate_{self._slug(archive_id)}_graph",
                ],
                exposure_mode="candidate_preview_only" if should_publish_candidate else "blocked",
                not_supply_reason=(
                    "候选快照尚未经过治理确认，禁止作为正式知识供应。"
                    if should_publish_candidate
                    else "质量门禁未放行发布候选，禁止进入系统间供应。"
                ),
            ),
        )

        return P1ResponseEnvelope[PublicationCandidateSnapshot](
            contract_version="p1.publication_candidate.r1",
            source_kind="live",
            generated_at=evaluation.generated_at,
            data=payload,
            warnings=[
                "当前候选由 P1 Mid Term 演示运行合同、质量报告和知识解析快照投影生成；不代表正式入库结果。"
            ],
        )

    @staticmethod
    def _candidate_refs_from_runtime(rule_execution_records) -> list[ArtifactRef]:
        refs: list[ArtifactRef] = []
        seen: set[str] = set()
        for record in rule_execution_records:
            for ref in record.output_artifact_refs:
                if ref.artifact_type != "publication_candidate" or ref.artifact_id in seen:
                    continue
                seen.add(ref.artifact_id)
                refs.append(
                    ArtifactRef(
                        artifact_id=ref.artifact_id,
                        artifact_type="canonical_knowledge_candidate",
                        stage_id="publication",
                        document_id=ref.document_id,
                        summary=ref.summary or "质量门禁放行后的发布候选知识引用。",
                    )
                )
        return refs

    @staticmethod
    def _candidate_refs_from_resolution(resolution) -> list[ArtifactRef]:
        refs: list[ArtifactRef] = []
        for item in resolution.canonical_items:
            refs.append(
                ArtifactRef(
                    artifact_id=item.knowledge_id,
                    artifact_type="canonical_knowledge_candidate",
                    stage_id="publication",
                    summary=f"{item.display_name} 发布候选知识。",
                    metadata={
                        "version": item.version,
                        "resolution_snapshot_id": resolution.snapshot_id,
                    },
                )
            )
        return refs

    @classmethod
    def _candidate_objects_from_resolution(cls, resolution, *, output_action: str) -> list[PublicationCandidateObject]:
        quality_status = cls._quality_status(output_action)
        if resolution.resolved_objects:
            return [
                PublicationCandidateObject(
                    object_id=item.object_id,
                    canonical_name=item.canonical_name,
                    object_type=item.object_type,
                    source_document_ids=item.source_document_ids,
                    source_candidate_ids=item.source_candidate_ids,
                    evidence_refs=item.evidence_refs,
                    confidence=item.confidence,
                    quality_status=quality_status,
                    version="candidate-v1",
                    source_snapshot_id=resolution.snapshot_id,
                )
                for item in resolution.resolved_objects
            ]

        return [
            PublicationCandidateObject(
                object_id=item.knowledge_id,
                canonical_name=item.display_name,
                object_type=item.identity_key.knowledge_type,
                source_document_ids=item.source_document_ids,
                source_candidate_ids=item.source_candidate_item_ids,
                evidence_refs=item.evidence_refs,
                confidence=item.quality_summary.get("confidence")
                if isinstance(item.quality_summary.get("confidence"), (int, float))
                else None,
                quality_status=quality_status,
                version=item.version,
                source_snapshot_id=resolution.snapshot_id,
            )
            for item in resolution.canonical_items
        ]

    @classmethod
    def _candidate_relations_from_resolution(
        cls,
        resolution,
        *,
        output_action: str,
    ) -> list[PublicationCandidateRelation]:
        quality_status = cls._quality_status(output_action)
        return [
            PublicationCandidateRelation(
                relation_id=relation.relation_id,
                source_object_id=relation.source_object_id,
                target_object_id=relation.target_object_id,
                relation_type=relation.relation_type,
                source_document_ids=relation.source_document_ids,
                source_candidate_relation_ids=relation.source_candidate_relation_ids,
                evidence_refs=relation.evidence_refs,
                confidence=relation.confidence,
                quality_status=quality_status,
                source_snapshot_id=resolution.snapshot_id,
            )
            for relation in resolution.resolved_relations
        ]

    @staticmethod
    def _candidate_count(runtime, objects: list[PublicationCandidateObject], refs: list[ArtifactRef]) -> int:
        quality_stage = next(
            (stage for stage in runtime.stage_snapshots if stage.stage_id == "quality_gate"),
            None,
        )
        if quality_stage and quality_stage.output_object_count:
            return quality_stage.output_object_count
        return len(objects) or len(refs)

    @staticmethod
    def _publication_status(
        *,
        output_action: str,
        should_publish_candidate: bool,
        stale_after_policy_change: bool,
    ) -> str:
        if stale_after_policy_change:
            return "stale_after_policy_change"
        if output_action == "return_for_rebuild":
            return "blocked_by_quality"
        if should_publish_candidate:
            return "governance_pending"
        return "machine_candidate_created"

    @staticmethod
    def _quality_status(output_action: str) -> str:
        if output_action == "publish_candidate":
            return "passed"
        if output_action == "return_for_rebuild":
            return "blocked"
        if output_action == "delay_publication":
            return "stale"
        return "warning"

    @classmethod
    def _build_publication_snapshot_id(cls, archive_id: str, runtime_snapshot_id: str) -> str:
        return f"PCS-{cls._slug(archive_id)}-{cls._slug(runtime_snapshot_id)}"

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
        return slug or "snapshot"
