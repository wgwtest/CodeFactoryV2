from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes.p1_refactor import get_p1_resolution_service
from app.archive_knowledge.contracts import (
    RuleActionMapping,
    RuleContract,
    RuleExecutionRecord,
    RuleFieldContract,
)
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.resolution import ArchiveKnowledgeResolutionService
from app.archive_knowledge.runtime_incremental_rebuild import (
    ArchiveRuntimeIncrementalRebuildService,
    ImpactSet as RuntimeImpactSet,
)
from app.main import create_app
from app.requirement_exchange.p1_knowledge_adapter import P1KnowledgeAdapter


def test_p1_refactor_bootstrap_exposes_parallel_work_lines() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/refactor/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "p1.refactor.r0"
    assert body["data"]["next_parallel_threads"] >= 5
    assert {item["owner_line"] for item in body["data"]["navigation"]} >= {"W1", "W2", "W3", "W4", "W5", "W6"}


def test_p1_runtime_fixture_keeps_rule_contract_trace_fields() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/archives/archive-demo/documents/doc-demo/runtime")

    assert response.status_code == 200
    body = response.json()
    record = body["data"]["rule_execution_records"][0]
    assert record["rule_id"] == "RL-QG-COVERAGE-001"
    assert record["rule_version"] == "r1.0"
    assert record["rule_hash"] == "sha256:rulecoverage001"
    assert record["policy_package_version_id"] == "PKGV-20260508-R0"
    assert record["input_hash"]
    assert record["output_hash"]
    assert record["affected_object_ids"] == ["K-24", "K-31", "P-24"]


def test_p1_runtime_stream_uses_same_envelope_as_polling() -> None:
    client = TestClient(create_app())

    polling = client.get("/api/p1/archives/archive-demo/documents/doc-demo/runtime")
    stream = client.get("/api/p1/archives/archive-demo/documents/doc-demo/runtime/stream")

    assert polling.status_code == 200
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")

    data_line = next(line for line in stream.text.splitlines() if line.startswith("data: "))
    streamed = json.loads(data_line.removeprefix("data: "))
    polled = polling.json()

    assert streamed["contract_version"] == polled["contract_version"] == "p1.document_runtime.r0"
    assert streamed["data"]["archive_id"] == polled["data"]["archive_id"] == "archive-demo"
    assert streamed["data"]["document_id"] == polled["data"]["document_id"] == "doc-demo"
    assert streamed["data"]["graph_projection"]["view_mode"] == "semantic_aggregate"


def test_p1_evaluation_report_explains_metrics_and_rule_trace() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/archives/archive-demo/runs/run-demo/evaluation-report")

    assert response.status_code == 200
    body = response.json()
    report = body["data"]
    assert report["archive_id"] == "archive-demo"
    assert report["run_id"] == "run-demo"
    assert report["gate_decision"]["decision"] == "block"
    assert report["gate_decision"]["output_action"] == "return_for_rebuild"
    assert report["quality_finding_report"]["summary"]["publish_blocked"] is True
    assert report["quality_finding_report"]["summary"]["blocked_count"] == 3
    assert report["knowledge_quality"]["policy_snapshot_id"] == "RS-P1-R0-001"
    assert report["knowledge_quality"]["resolution_snapshot_id"] == "RESOLVE-P1-R0-001"
    evidence_metric = next(
        metric for metric in report["knowledge_quality"]["metrics"] if metric["metric_id"] == "knowledge.evidence_coverage"
    )
    assert evidence_metric["actual"] == 0.91
    assert evidence_metric["threshold"] == 0.9
    assert evidence_metric["rule_execution_record_ids"] == ["RECORD-QG-001"]
    assert "anchor-A-102" in evidence_metric["evidence_anchor_ids"]
    rule_hit = report["rule_hits"][0]
    assert rule_hit["rule_id"] == "RL-QG-COVERAGE-001"
    assert rule_hit["rule_hash"] == "sha256:rulecoverage001"
    assert rule_hit["affected_object_ids"] == ["K-24", "K-31", "P-24"]
    assert rule_hit["input_artifact_refs"][0]["artifact_id"] == "candidate-knowledge"
    assert report["graph_quality"]["metrics"]


def test_rule_contract_marks_missing_required_fields_invalid() -> None:
    contract = RuleContract(
        rule_id="RL-BROKEN-001",
        rule_name="broken contract",
        rule_version="r1.0",
        rule_hash="sha256:broken",
        stage_id="quality_gate",
        effect_kind="score",
        input_schema=[
            RuleFieldContract(
                field_name="evidence_coverage",
                source_artifact="candidate-knowledge",
                field_type="number",
            )
        ],
        output_schema=[
            RuleFieldContract(
                field_name="quality_decision",
                target_artifact="quality-gate",
                field_type="enum",
            )
        ],
        parameters={},
        action_mapping=RuleActionMapping(
            when_hit="",
            when_miss="",
            output_fields=[],
            downstream_stage_ids=[],
        ),
        trace_fields=[],
        contract_status="valid",
    )

    assert contract.contract_status == "invalid"
    assert "missing input_schema.input_hash" in contract.contract_errors
    assert "missing output_schema.output_hash" in contract.contract_errors
    assert "missing output_schema.affected_object_ids" in contract.contract_errors
    assert "missing parameters.conditions" in contract.contract_errors
    assert "missing action_mapping.when_hit" in contract.contract_errors
    assert "missing trace_fields.rule_hash" in contract.contract_errors


def test_rule_execution_record_round_trips_required_trace_fields() -> None:
    record = RuleExecutionRecord(
        execution_id="RECORD-ROUND-TRIP",
        run_id="RUN-P1-R0-001",
        archive_id="archive-contract-demo",
        document_id="doc-contract-2026q1",
        stage_id="quality_gate",
        policy_package_version_id="PKGV-20260508-R0",
        rule_id="RL-QG-COVERAGE-001",
        rule_version="r1.0",
        rule_hash="sha256:rulecoverage001",
        input_hash="sha256:input001",
        output_hash="sha256:output001",
        affected_object_ids=["K-24", "K-31", "P-24"],
        decision="warn_continue",
        executed_at="2026-05-08T10:00:00+08:00",
    )

    round_tripped = RuleExecutionRecord.model_validate(record.model_dump(mode="json"))

    assert round_tripped.rule_id == "RL-QG-COVERAGE-001"
    assert round_tripped.rule_version == "r1.0"
    assert round_tripped.rule_hash == "sha256:rulecoverage001"
    assert round_tripped.input_hash == "sha256:input001"
    assert round_tripped.output_hash == "sha256:output001"
    assert round_tripped.affected_object_ids == ["K-24", "K-31", "P-24"]


def test_p1_policy_package_version_and_rule_detail_endpoints() -> None:
    client = TestClient(create_app())

    version_response = client.get("/api/p1/refactor/policy-package/versions/PKGV-20260508-R0")
    assert version_response.status_code == 200
    version_body = version_response.json()
    assert version_body["contract_version"] == "p1.policy_package_version.r0"
    assert version_body["data"]["policy_package_version_id"] == "PKGV-20260508-R0"

    rule_response = client.get(
        "/api/p1/refactor/policy-package/versions/PKGV-20260508-R0/rules/RL-QG-COVERAGE-001"
    )
    assert rule_response.status_code == 200
    rule = rule_response.json()["data"]
    assert rule["contract_status"] == "valid"
    assert {field["field_name"] for field in rule["input_schema"]} >= {"evidence_coverage", "input_hash"}
    assert {field["field_name"] for field in rule["output_schema"]} >= {
        "quality_decision",
        "affected_object_ids",
        "output_hash",
    }
    assert set(rule["trace_fields"]) >= {
        "rule_id",
        "rule_version",
        "rule_hash",
        "input_hash",
        "output_hash",
        "affected_object_ids",
    }


def test_p1_system_output_is_formal_contract_not_candidate_only() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/knowledge-supply/read")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "p1.knowledge_supply.v1"
    assert body["data"]["contract_version"] == "P1KnowledgeSupplyExport.v1"
    assert body["data"]["published_snapshot_id"] == "REL-P1-R0-001"
    assert body["data"]["published_snapshot"]["formal_version"] == "REL-20260508-R0"
    assert body["data"]["formal_version"] == "REL-20260508-R0"
    assert body["data"]["governed_by"] == "governance-confirmation"
    assert body["data"]["published_at"] == "2026-05-08T10:00:00+08:00"
    assert body["data"]["knowledge_read_path"] == "/api/p1/knowledge-supply/read"
    assert body["data"]["graph_query_path"] == "/api/p1/knowledge-supply/graph/query"
    assert all(item["artifact_type"] != "canonical_knowledge_candidate" for item in body["data"]["formal_knowledge_refs"])


def test_p1_candidate_preview_stays_outside_formal_supply_namespace() -> None:
    client = TestClient(create_app())

    candidate_response = client.get("/api/p1/candidates/publication/latest")
    formal_response = client.get("/api/p1/knowledge-supply/read")

    assert candidate_response.status_code == 200
    assert formal_response.status_code == 200
    candidate = candidate_response.json()["data"]
    formal = formal_response.json()["data"]
    assert candidate["governance_status"] == "pending"
    assert candidate["api_exposure_scope"]["readonly_candidate_api_paths"] == [
        "/api/p1/candidates/knowledge/read",
        "/api/p1/candidates/graph/search",
    ]
    assert formal["published_snapshot"]["publication_candidate_snapshot_id"] == candidate["publication_candidate_snapshot_id"]
    assert formal["knowledge_read_path"].startswith("/api/p1/knowledge-supply/")
    assert all(path.startswith("/api/p1/candidates/") for path in candidate["api_exposure_scope"]["readonly_candidate_api_paths"])


def test_p1_resolution_latest_uses_live_cross_document_candidates(tmp_path) -> None:
    app = create_app()
    _write_resolution_document_artifacts(tmp_path)
    app.dependency_overrides[get_p1_resolution_service] = lambda: ArchiveKnowledgeResolutionService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/p1/archives/kb/knowledge-resolution/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["source_kind"] == "live"
    candidate = body["data"]["match_candidates"][0]
    assert candidate["suggested_action"] == "merge"
    assert candidate["source_document_ids"] == ["doc-1", "doc-2"]
    assert candidate["source_candidate_item_ids"] == ["doc-1:entity-nas", "doc-2:entity-nas-cn"]
    assert candidate["identity_key"]["key_fields"]["category"] == "system_or_service"
    assert candidate["identity_key"]["alias_tokens"] == ["nas", "国家空域体系"]
    assert candidate["match_features"]["name_score"] == 1.0
    assert len(candidate["evidence_refs"]) == 2
    assert body["data"]["merge_decisions"][0]["decision"] == "merged"
    canonical = body["data"]["canonical_items"][0]
    assert canonical["source_document_ids"] == ["doc-1", "doc-2"]
    assert canonical["quality_summary"]["candidate_only"] is True


def test_p1_resolution_update_plan_is_candidate_only_and_does_not_write_formal_knowledge(tmp_path) -> None:
    app = create_app()
    _write_resolution_document_artifacts(tmp_path)
    impact_set = RuntimeImpactSet(
        impact_id="impact-knowledge-resolution",
        archive_id="kb",
        changed_rule_ids=["RL-KR-MATCH-001"],
        changed_stage_ids=["knowledge_resolution"],
        affected_docs=["doc-1"],
        affected_document_ids=["doc-1"],
        affected_stages=["knowledge_resolution", "publication_candidate"],
        affected_stage_ids=["knowledge_resolution", "publication_candidate"],
        affected_candidates=["doc-1:entity-nas"],
        affected_candidate_ids=["doc-1:entity-nas"],
        affected_relations=["doc-1:relation:1"],
        affected_relation_ids=["doc-1:relation:1"],
        affected_publication_snapshots=["PCS-kb-candidate"],
        affected_publication_snapshot_ids=["PCS-kb-candidate"],
        minimum_rebuild_stage_id="knowledge_resolution",
        source_policy_snapshot_id="policy-v1",
        target_policy_snapshot_id="policy-v2",
        generated_at="2026-05-09T00:00:00+00:00",
    )
    ArchiveRuntimeIncrementalRebuildService(tmp_path).create_incremental_rebuild_task("kb", impact_set)
    app.dependency_overrides[get_p1_resolution_service] = lambda: ArchiveKnowledgeResolutionService(tmp_path)
    client = TestClient(app)

    resolution_response = client.get("/api/p1/archives/kb/knowledge-resolution/latest")
    impact_response = client.get("/api/p1/archives/kb/impact-set/latest")

    assert resolution_response.status_code == 200
    update_plan = resolution_response.json()["data"]["update_plan"]
    assert update_plan["minimum_rebuild_stage_id"] == "knowledge_resolution"
    assert update_plan["stale_object_ids"] == ["doc-1:entity-nas", "doc-1:relation:1", "PCS-kb-candidate"]
    assert update_plan["affected_knowledge_ids"]
    assert update_plan["writes_official_knowledge"] is False
    assert "keep formal knowledge unchanged until governance confirmation" in update_plan["recommended_actions"]
    assert impact_response.status_code == 200
    impact_body = impact_response.json()
    assert impact_body["source_kind"] == "live"
    impact = impact_body["data"]
    assert impact["impact_set_id"] == "impact-knowledge-resolution"
    assert impact["affected_candidate_ids"] == ["doc-1:entity-nas"]
    assert impact["writes_official_knowledge"] is False
    assert (tmp_path / "kb-knowledge.json").exists() is False


def test_p1_p6_display_export_exposes_graph_lookup_paths() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/knowledge-supply/graph/query")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "p1.p6_display_export.v2"
    assert body["data"]["contract_version"] == "P6DisplayExportContract.v2"
    assert body["data"]["published_snapshot_id"] == "REL-P1-R0-001"
    assert body["data"]["graph_summary_path"] == "/api/p1/knowledge-supply/graph/summary"
    assert body["data"]["entity_lookup_path"] == "/api/p1/knowledge-supply/graph/entities/{entity_id}"
    assert body["data"]["relation_lookup_path"] == "/api/p1/knowledge-supply/graph/relations/{relation_id}"


def test_p1_legacy_system_output_route_is_deprecated_but_compatible() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/system-output/knowledge-supply")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["contract_version"] == "P1KnowledgeSupplyExport.v1"
    assert body["warnings"]
    assert body["data"]["deprecation"]["deprecated"] is True
    assert body["data"]["deprecation"]["replacement_path"] == "/api/p1/knowledge-supply/read"


def test_p1_requirement_adapter_validates_supply_contract_version() -> None:
    adapter = P1KnowledgeAdapter()

    payload = adapter.get_formal_knowledge_supply()

    assert payload["contract_version"] == "P1KnowledgeSupplyExport.v1"
    with pytest.raises(ValueError):
        adapter.validate_knowledge_supply_contract({"contract_version": "PublicationCandidateSnapshot"})


def _write_resolution_document_artifacts(output_root) -> None:
    DocumentArtifactRepository(output_root).replace_all(
        "kb",
        [
            {
                "document": {
                    "id": "doc-1",
                    "path": "docs/doc-1.docx",
                    "title": "Document One",
                    "file_type": "docx",
                    "source_archive": "airspace-kb",
                    "character_count": 1000,
                    "parser_name": "docling_docx",
                    "segment_count": 8,
                    "source_file_path": str(output_root / "doc-1.docx"),
                    "source_digest": "sha256:doc-1",
                },
                "entities": [
                    {
                        "id": "entity-nas",
                        "name": "国家空域系统",
                        "category": "system_or_service",
                        "aliases": ["NAS"],
                        "document_ids": ["doc-1"],
                        "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统是空域协同的核心系统。"}],
                    }
                ],
                "events": [],
                "processes": [],
                "relations": [
                    {
                        "type": "part_of",
                        "source_name": "国家空域系统",
                        "target_name": "空域协同",
                    }
                ],
                "extraction": {
                    "strategy": "formal",
                    "candidate_count": 1,
                    "relation_count": 1,
                    "runtime_trace": {
                        "knowledge_resolution": {
                            "rule_execution_records": [
                                {
                                    "execution_id": "rex-doc-1-kr",
                                    "rule_id": "RL-KR-MATCH-001",
                                    "input_hash": "sha256:input-1",
                                    "output_hash": "sha256:output-1",
                                }
                            ]
                        }
                    },
                },
            },
            {
                "document": {
                    "id": "doc-2",
                    "path": "docs/doc-2.docx",
                    "title": "Document Two",
                    "file_type": "docx",
                    "source_archive": "airspace-kb",
                    "character_count": 900,
                    "parser_name": "docling_docx",
                    "segment_count": 6,
                    "source_file_path": str(output_root / "doc-2.docx"),
                    "source_digest": "sha256:doc-2",
                },
                "entities": [
                    {
                        "id": "entity-nas-cn",
                        "name": "国家空域系统",
                        "category": "system_or_service",
                        "aliases": ["国家空域体系"],
                        "document_ids": ["doc-2"],
                        "evidence": [{"document_id": "doc-2", "excerpt": "国家空域体系支撑跨区域运行协同。"}],
                    }
                ],
                "events": [],
                "processes": [],
                "relations": [
                    {
                        "type": "part_of",
                        "source_name": "国家空域系统",
                        "target_name": "空域协同",
                    }
                ],
                "extraction": {
                    "strategy": "formal",
                    "candidate_count": 1,
                    "relation_count": 1,
                    "runtime_trace": {
                        "knowledge_resolution": {
                            "rule_execution_records": [
                                {
                                    "execution_id": "rex-doc-2-kr",
                                    "rule_id": "RL-KR-MATCH-001",
                                    "input_hash": "sha256:input-2",
                                    "output_hash": "sha256:output-2",
                                }
                            ]
                        }
                    },
                },
            },
        ],
    )
