from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.routes.archives import get_archive_registry_service
from app.archive_knowledge.contracts import (
    ArchiveKnowledgeResolutionSnapshot,
    DocumentRuntimeSnapshot,
    DownstreamConsumptionGuide,
    EvaluationRunReport,
    FormalApiExposureScope,
    FormalKnowledgeInterface,
    FormalKnowledgeVersionRule,
    ImpactSet,
    P1CleanSystemOutputContract,
    P1KnowledgeSupplyExport,
    P1RefactorBootstrap,
    P1ResponseEnvelope,
    P6DisplayExportContractV2,
    PolicyPackage,
    PolicyPackageVersion,
    PublicationCandidateSnapshot,
    RuleContract,
    SystemOutputAdapterContract,
    SystemReadableEvidence,
    SystemReadableKnowledgeObject,
    SystemReadableKnowledgeRelation,
)
from app.archive_knowledge.registry import ArchiveRegistryService
from app.archive_knowledge.fixtures import (
    get_deprecated_p1_system_output,
    get_p1_bootstrap,
    get_p1_evaluation_report,
    get_p1_impact_set,
    get_p1_p6_display_export,
    get_p1_policy_package,
    get_p1_publication_candidate,
    get_p1_resolution_snapshot,
    get_p1_runtime_snapshot,
    get_p1_system_output,
)
from app.archive_knowledge.p1_modules.publication import P1PublicationCandidateService
from app.archive_knowledge.p1_modules.intake import P1IntakeService, P1IntakeSnapshot
from app.archive_knowledge.p1_modules.knowledge_resolution import P1KnowledgeResolutionService
from app.archive_knowledge.resolution import ArchiveKnowledgeResolutionService
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.archive_knowledge.p1_modules.quality_graph import QualityGraphReportService
from app.config import settings

router = APIRouter(prefix="/p1", tags=["p1-refactor"])


def get_p1_resolution_service() -> ArchiveKnowledgeResolutionService:
    return P1KnowledgeResolutionService(settings.knowledge_output_root)


def get_quality_graph_report_service() -> QualityGraphReportService:
    return QualityGraphReportService()


def get_p1_publication_service() -> P1PublicationCandidateService:
    return P1PublicationCandidateService()


def get_p1_archive_knowledge_service() -> ArchiveKnowledgeService:
    return ArchiveKnowledgeService(settings.knowledge_output_root)


def get_p1_intake_service() -> P1IntakeService:
    return P1IntakeService(settings.knowledge_output_root)


@router.get("/refactor/bootstrap", response_model=P1ResponseEnvelope[P1RefactorBootstrap])
def get_refactor_bootstrap() -> P1ResponseEnvelope[P1RefactorBootstrap]:
    return get_p1_bootstrap()


@router.get("/refactor/policy-package", response_model=P1ResponseEnvelope[PolicyPackage])
def get_refactor_policy_package() -> P1ResponseEnvelope[PolicyPackage]:
    return get_p1_policy_package()


@router.get(
    "/refactor/policy-package/versions/{policy_package_version_id}",
    response_model=P1ResponseEnvelope[PolicyPackageVersion],
)
def get_refactor_policy_package_version(
    policy_package_version_id: str,
) -> P1ResponseEnvelope[PolicyPackageVersion]:
    package = get_p1_policy_package()
    for version in package.data.versions:
        if version.policy_package_version_id == policy_package_version_id:
            return P1ResponseEnvelope[PolicyPackageVersion](
                contract_version="p1.policy_package_version.r0",
                source_kind=package.source_kind,
                generated_at=package.generated_at,
                data=version,
            )
    raise HTTPException(status_code=404, detail="Policy package version not found")


@router.get(
    "/refactor/policy-package/versions/{policy_package_version_id}/rules/{rule_id}",
    response_model=P1ResponseEnvelope[RuleContract],
)
def get_refactor_rule_contract(
    policy_package_version_id: str,
    rule_id: str,
) -> P1ResponseEnvelope[RuleContract]:
    version_envelope = get_refactor_policy_package_version(policy_package_version_id)
    for rule in version_envelope.data.rule_contracts:
        if rule.rule_id == rule_id:
            return P1ResponseEnvelope[RuleContract](
                contract_version="p1.rule_contract.r0",
                source_kind=version_envelope.source_kind,
                generated_at=version_envelope.generated_at,
                data=rule,
            )
    raise HTTPException(status_code=404, detail="Rule contract not found")


@router.get("/archives/{archive_id}/intake", response_model=P1ResponseEnvelope[P1IntakeSnapshot])
def get_archive_intake_snapshot(
    archive_id: str,
    registry_service: ArchiveRegistryService = Depends(get_archive_registry_service),
    service: P1IntakeService = Depends(get_p1_intake_service),
) -> P1ResponseEnvelope[P1IntakeSnapshot]:
    archive = registry_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Archive not found")

    policy_config = registry_service.get_policy_config(archive_id) or {}
    return service.build_envelope(
        archive,
        policy_package_version_id=policy_config.get("policy_package_version_id"),
    )


@router.get(
    "/archives/{archive_id}/documents/{document_id}/runtime",
    response_model=P1ResponseEnvelope[DocumentRuntimeSnapshot],
)
def get_document_runtime_snapshot(archive_id: str, document_id: str) -> P1ResponseEnvelope[DocumentRuntimeSnapshot]:
    payload = get_p1_runtime_snapshot()
    payload.data.archive_id = archive_id
    payload.data.document_id = document_id
    payload.data.policy_snapshot.archive_id = archive_id
    payload.data.graph_projection.archive_id = archive_id
    payload.data.graph_projection.document_id = document_id
    for record in payload.data.rule_execution_records:
        record.archive_id = archive_id
        record.document_id = document_id
    return payload


@router.get("/archives/{archive_id}/documents/{document_id}/runtime/stream")
def stream_document_runtime_snapshot(archive_id: str, document_id: str) -> StreamingResponse:
    def event_stream() -> Iterator[str]:
        payload = get_document_runtime_snapshot(archive_id, document_id).model_dump(mode="json")
        yield "event: runtime\n"
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/archives/{archive_id}/runs/{run_id}/evaluation-report",
    response_model=P1ResponseEnvelope[EvaluationRunReport],
)
def get_evaluation_report(archive_id: str, run_id: str) -> P1ResponseEnvelope[EvaluationRunReport]:
    return get_p1_evaluation_report(archive_id=archive_id, run_id=run_id)


@router.get(
    "/archives/{archive_id}/quality-graph/report",
    response_model=P1ResponseEnvelope[EvaluationRunReport],
)
def get_quality_graph_report(
    archive_id: str,
    runtime_snapshot_id: str = Query(...),
    policy_package_version_id: str = Query(...),
    service: QualityGraphReportService = Depends(get_quality_graph_report_service),
) -> P1ResponseEnvelope[EvaluationRunReport]:
    return service.build_report(
        archive_id=archive_id,
        runtime_snapshot_id=runtime_snapshot_id,
        policy_package_version_id=policy_package_version_id,
    )


@router.get(
    "/archives/{archive_id}/knowledge-resolution/latest",
    response_model=P1ResponseEnvelope[ArchiveKnowledgeResolutionSnapshot],
)
def get_knowledge_resolution_snapshot(
    archive_id: str,
    runtime_snapshot_id: str | None = Query(None),
    policy_package_version_id: str | None = Query(None),
    service: ArchiveKnowledgeResolutionService = Depends(get_p1_resolution_service),
) -> P1ResponseEnvelope[ArchiveKnowledgeResolutionSnapshot]:
    live_payload = service.build_latest_resolution_envelope(
        archive_id,
        runtime_snapshot_id=runtime_snapshot_id,
        policy_package_version_id=policy_package_version_id,
    )
    if live_payload is not None:
        return live_payload

    payload = get_p1_resolution_snapshot()
    payload.data.archive_id = archive_id
    payload.data.run_id = runtime_snapshot_id
    payload.data.runtime_snapshot_id = runtime_snapshot_id
    payload.data.policy_package_version_id = policy_package_version_id or payload.data.policy_package_version_id
    return payload


@router.get("/archives/{archive_id}/impact-set/latest", response_model=P1ResponseEnvelope[ImpactSet])
def get_latest_impact_set(
    archive_id: str,
    service: ArchiveKnowledgeResolutionService = Depends(get_p1_resolution_service),
) -> P1ResponseEnvelope[ImpactSet]:
    live_payload = service.build_latest_impact_envelope(archive_id)
    if live_payload is not None:
        return live_payload

    payload = get_p1_impact_set()
    payload.data.archive_id = archive_id
    return payload


@router.get(
    "/archives/{archive_id}/publication-candidates/latest",
    response_model=P1ResponseEnvelope[PublicationCandidateSnapshot],
)
def get_publication_candidate_snapshot(
    archive_id: str,
    runtime_snapshot_id: str | None = None,
    policy_package_version_id: str | None = None,
    service: P1PublicationCandidateService = Depends(get_p1_publication_service),
) -> P1ResponseEnvelope[PublicationCandidateSnapshot]:
    return service.build_latest_candidate_envelope(
        archive_id=archive_id,
        runtime_snapshot_id=runtime_snapshot_id,
        policy_package_version_id=policy_package_version_id,
    )


@router.get(
    "/candidates/publication/latest",
    response_model=P1ResponseEnvelope[PublicationCandidateSnapshot],
)
def get_candidate_publication_preview() -> P1ResponseEnvelope[PublicationCandidateSnapshot]:
    return get_p1_publication_candidate()


def _system_output_adapter_contract() -> SystemOutputAdapterContract:
    return SystemOutputAdapterContract(
        adapter_name="P1CleanSystemOutputAdapter",
        contract_version="P1CleanSystemOutputContract.v1",
        input_keys=["archiveId", "publicationSnapshotId"],
        output_keys=[
            "supplyAvailable",
            "formalInterfaces",
            "readableObjects",
            "readableRelations",
            "readableEvidence",
            "versionSelectionRules",
        ],
        allowed_backend_calls=[
            "getP1CleanSystemOutputContract",
            "getArchiveSummary",
            "getArchiveGraph",
            "getArchivePublication",
        ],
        forbidden_sources=[
            "runtime_temporary_nodes",
            "publication_candidate_snapshot",
            "unconfirmed_candidate_knowledge",
            "modules/publication/internal_state",
        ],
    )


def _system_output_consumers(supply_available: bool) -> list[DownstreamConsumptionGuide]:
    if supply_available:
        return [
            DownstreamConsumptionGuide(
                consumer="P2",
                read_pattern="Bind requirements to formal object ids from the governed publication snapshot only.",
                notes=["Use formal_version_id for provenance.", "Do not read candidate preview APIs."],
            ),
            DownstreamConsumptionGuide(
                consumer="P3",
                read_pattern="Read formal graph relations and evidence as immutable design context.",
                notes=["Keep downstream graph traversal read-only.", "Reject missing formal_version_id."],
            ),
        ]

    return [
        DownstreamConsumptionGuide(
            consumer="P2",
            read_pattern="Do not hydrate requirements until supply_available is true.",
            notes=["Only show the unavailable reason and candidate trace id."],
        ),
        DownstreamConsumptionGuide(
            consumer="P3",
            read_pattern="Do not consume graph data until governance confirms a formal publication.",
            notes=["Candidate graph APIs are preview-only and are not a formal supply source."],
        ),
    ]


def _build_unavailable_system_output_contract(
    *,
    archive_id: str,
    publication_snapshot_id: str | None,
    reason: str,
) -> P1CleanSystemOutputContract:
    selected_snapshot_id = publication_snapshot_id or "publicationSnapshotId-not-generated"
    generated_at = datetime.now(UTC).isoformat()
    return P1CleanSystemOutputContract(
        contract_version="P1CleanSystemOutputContract.v1",
        archive_id=archive_id,
        publication_snapshot_id=publication_snapshot_id,
        canonical_publication_snapshot_id=None,
        formal_version=None,
        formal_version_id=None,
        governed_by=None,
        published_at=None,
        generated_at=generated_at,
        source_kind="governed_publication_snapshot",
        is_formalized=False,
        supply_available=False,
        unavailable_reason=reason,
        boundary="系统间输出只允许读取治理确认后的正式快照；当前 publicationSnapshotId 不可作为正式知识供应。",
        source_summary={"document_count": 0, "entity_count": 0, "event_count": 0, "process_count": 0},
        formal_interfaces=[],
        version_selection_rules=[
            FormalKnowledgeVersionRule(
                rule_id="reject-unconfirmed-publication-candidate",
                description="候选发布快照必须经过治理确认并生成正式版本后，才能进入系统间输出。",
                selected_publication_snapshot_id=selected_snapshot_id,
                selected_version_label="not-formalized",
                governance_boundary="post_publication_confirmation",
            )
        ],
        api_exposure_scope=FormalApiExposureScope(
            exposure_mode="not_available",
            formal_api_paths=[],
            candidate_api_paths=[
                "/api/p1/candidates/knowledge/read",
                "/api/p1/candidates/graph/search",
            ],
            blocked_candidate_sources=[
                "publication_candidate_snapshot",
                "unconfirmed_candidate_knowledge",
            ],
            not_supply_reason=reason,
        ),
        adapter_contract=_system_output_adapter_contract(),
        downstream_consumers=_system_output_consumers(False),
    )


def _enrich_formal_system_output_contract(
    *,
    archive_id: str,
    contract: P1CleanSystemOutputContract,
    service: ArchiveKnowledgeService,
) -> P1CleanSystemOutputContract:
    graph = service.get_graph(archive_id)
    version_id = contract.canonical_publication_snapshot_id or contract.formal_version
    contract.formal_version_id = version_id
    contract.is_formalized = True
    contract.supply_available = True
    contract.unavailable_reason = None
    contract.adapter_contract = _system_output_adapter_contract()
    contract.api_exposure_scope = FormalApiExposureScope(
        exposure_mode="formal_only",
        formal_api_paths=[item.path for item in contract.formal_interfaces],
        candidate_api_paths=[],
        blocked_candidate_sources=[
            "publication_candidate_snapshot",
            "unconfirmed_candidate_knowledge",
        ],
    )
    contract.readable_objects = [
        SystemReadableKnowledgeObject(
            object_id=node["id"],
            name=node["label"],
            item_type=node.get("item_type") or node.get("type") or "knowledge_item",
            category=node.get("type"),
            document_count=int(node.get("document_count") or 0),
            evidence_count=len((service.get_item_detail(archive_id, node["id"]) or {}).get("evidence", [])),
            version_id=version_id,
        )
        for node in graph.get("nodes", [])
    ]
    contract.readable_relations = [
        SystemReadableKnowledgeRelation(
            relation_id=f"{edge['source']}::{edge['label']}::{edge['target']}",
            source_object_id=edge["source"],
            target_object_id=edge["target"],
            relation_type=edge["label"],
            version_id=version_id,
        )
        for edge in graph.get("edges", [])
    ]
    evidence_rows: list[SystemReadableEvidence] = []
    for node in graph.get("nodes", []):
        detail = service.get_item_detail(archive_id, node["id"]) or {}
        for index, evidence in enumerate(detail.get("evidence", []), start=1):
            evidence_rows.append(
                SystemReadableEvidence(
                    evidence_id=f"{node['id']}::evidence::{index}",
                    object_id=node["id"],
                    document_id=evidence.get("document_id"),
                    excerpt=evidence.get("excerpt"),
                    version_id=version_id,
                )
            )
    contract.readable_evidence = evidence_rows
    contract.downstream_consumers = _system_output_consumers(True)
    return contract


@router.get(
    "/archives/{archive_id}/system-output",
    response_model=P1ResponseEnvelope[P1CleanSystemOutputContract],
)
def get_clean_system_output_contract(
    archive_id: str,
    publication_snapshot_id: str | None = Query(default=None),
    service: ArchiveKnowledgeService = Depends(get_p1_archive_knowledge_service),
) -> P1ResponseEnvelope[P1CleanSystemOutputContract]:
    generated_at = datetime.now(UTC).isoformat()
    if not publication_snapshot_id:
        contract = _build_unavailable_system_output_contract(
            archive_id=archive_id,
            publication_snapshot_id=None,
            reason="尚未生成 publicationSnapshotId，无法向后续系统供应正式知识。",
        )
        return P1ResponseEnvelope[P1CleanSystemOutputContract](
            contract_version="p1.system_output.preview.r1",
            source_kind="live",
            generated_at=generated_at,
            data=contract,
            warnings=["系统间输出未开放：缺少可追溯的 publicationSnapshotId。"],
        )

    try:
        contract = service.get_system_output_contract(archive_id, publication_snapshot_id)
    except ValueError as exc:
        unavailable_contract = _build_unavailable_system_output_contract(
            archive_id=archive_id,
            publication_snapshot_id=publication_snapshot_id,
            reason=str(exc),
        )
        return P1ResponseEnvelope[P1CleanSystemOutputContract](
            contract_version="p1.system_output.preview.r1",
            source_kind="live",
            generated_at=generated_at,
            data=unavailable_contract,
            warnings=["系统间输出未开放：当前快照仍处于候选或未正式入库状态。"],
        )

    return P1ResponseEnvelope[P1CleanSystemOutputContract](
        contract_version="p1.system_output.preview.r1",
        source_kind="live",
        generated_at=generated_at,
        data=_enrich_formal_system_output_contract(
            archive_id=archive_id,
            contract=contract,
            service=service,
        ),
    )


@router.get("/knowledge-supply/read", response_model=P1ResponseEnvelope[P1KnowledgeSupplyExport])
def read_formal_knowledge_supply() -> P1ResponseEnvelope[P1KnowledgeSupplyExport]:
    return get_p1_system_output()


@router.get(
    "/knowledge-supply/graph/query",
    response_model=P1ResponseEnvelope[P6DisplayExportContractV2],
)
def query_formal_knowledge_graph() -> P1ResponseEnvelope[P6DisplayExportContractV2]:
    return get_p1_p6_display_export()


@router.get("/system-output/knowledge-supply", response_model=P1ResponseEnvelope[P1KnowledgeSupplyExport])
def get_system_output_knowledge_supply() -> P1ResponseEnvelope[P1KnowledgeSupplyExport]:
    return get_deprecated_p1_system_output()
