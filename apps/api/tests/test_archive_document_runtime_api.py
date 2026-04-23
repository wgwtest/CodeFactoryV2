from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.archive_knowledge.builder as builder_module
from app.api.routes.knowledge import get_archive_document_runtime_service
from app.archive_knowledge.builder import _build_formal_archive_contributions
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.archive_knowledge.runtime_asset_intake import build_asset_intake_snapshot
from app.archive_knowledge.runtime_evidence_constructor import (
    build_evidence_constructor_snapshot,
)
from app.archive_knowledge.runtime_evidence_graph_chunk_layer import (
    build_evidence_graph_chunk_layer_snapshot,
)
from app.archive_knowledge.runtime_evidence_pack import build_evidence_pack_snapshot
from app.archive_knowledge.runtime_concept_candidate_review import (
    build_concept_candidate_review_snapshot,
)
from app.archive_knowledge.runtime_relation_review_family_normalization import (
    build_relation_review_family_normalization_snapshot,
)
from app.archive_knowledge.runtime_definition_summary_conflict_consolidation import (
    build_definition_summary_conflict_consolidation_snapshot,
)
from app.archive_knowledge.runtime_parser_router import build_parser_router_snapshot
from app.archive_knowledge.runtime_canonical_knowledge import (
    build_canonical_knowledge_snapshot,
)
from app.archive_knowledge.runtime_indexes_snapshots_apis import (
    build_indexes_snapshots_apis_snapshot,
)
from app.archive_knowledge.runtime_parser_execution import build_parser_execution_snapshot
from app.archive_knowledge.quality_gate_policy import build_quality_gate_runtime_trace
from app.archive_knowledge.runtime_quality_gate import build_quality_gate_snapshot
from app.archive_knowledge.runtime_unified_document_object import build_unified_document_object_snapshot
from app.archive_knowledge.policy_config import build_default_archive_policy_config, build_policy_run_snapshot
from app.archive_knowledge.runtime_repository import DocumentRuntimeRepository
from app.archive_knowledge.runtime_service import ArchiveDocumentRuntimeService
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.extraction.service import ExtractionService
from app.extraction.schema import ExtractionBatch, ExtractedCandidate
from app.knowledge_builder import SourceDocument, _document_id
from app.main import create_app
from app.parsing.models import ParsedDocument, ParsedSegment


def _sample_contribution(document_id: str = "doc-1") -> dict:
    return {
        "document": {
            "id": document_id,
            "path": "runtime/SV-2.docx",
            "title": "SV-2 Translation",
            "file_type": "docx",
            "source_archive": "test-archive",
            "character_count": 2400,
            "parser_name": "docling.docx",
            "segment_count": 8,
            "source_file_path": "E:/sample/SV-2.docx",
            "source_digest": "sha256:demo",
        },
        "entities": [
            {
                "id": "entity-1",
                "name": "National Airspace System",
                "category": "domain_concept",
                "aliases": ["NAS"],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": "National Airspace System overview."}],
            }
        ],
        "events": [],
        "processes": [
            {
                "id": "process-1",
                "name": "Mission Orchestration",
                "category": "domain_process",
                "aliases": [],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": "Mission orchestration depends on evidence packs."}],
            }
        ],
        "relations": [
            {
                "type": "part_of",
                "source_name": "National Airspace System",
                "target_name": "Mission Orchestration",
                "confidence": 0.92,
                "evidence": "The NAS contains mission orchestration flows.",
            }
        ],
        "extraction": {
            "strategy": "formal",
            "schema_version": "v1",
            "candidate_count": 2,
            "relation_count": 1,
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
            "chunking_used": True,
        },
    }


def test_archive_document_runtime_endpoint_returns_13_stage_contract(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()

    assert payload["archive_id"] == "nas-a"
    assert payload["document_id"] == "doc-1"
    assert payload["document_title"] == "SV-2 Translation"
    assert len(payload["stages"]) == 13
    assert payload["current_stage_id"] == "quality_policy_evaluation_governance_gate"
    assert payload["runtime_mode"] == "persisted"
    assert len(payload["persisted_stage_ids"]) == 13

    asset_intake = payload["stages"][0]
    assert asset_intake["stage_id"] == "asset_intake"
    assert asset_intake["graph"]["nodes"]
    assert asset_intake["stage_observer"]["mode"] == "stage"

    quality_gate = next(stage for stage in payload["stages"] if stage["stage_id"] == "quality_policy_evaluation_governance_gate")
    assert quality_gate["graph"]["nodes"]
    assert quality_gate["graph"]["edges"]


def test_unified_document_snapshot_covers_all_sections_and_paragraphs() -> None:
    parsed_document = ParsedDocument(
        parser_name="docling.docx",
        parser_version="1.0.0",
        segments=[
            ParsedSegment(heading="Overview", content="Overview paragraph 1", anchor={"page": 1, "paragraph": 1}),
            ParsedSegment(heading="Overview", content="Overview paragraph 2", anchor={"page": 1, "paragraph": 2}),
            ParsedSegment(heading="Inputs", content="Inputs paragraph 1", anchor={"page": 1, "paragraph": 3}),
            ParsedSegment(heading="Inputs", content="Inputs paragraph 2", anchor={"page": 1, "paragraph": 4}),
            ParsedSegment(heading="Processing", content="Processing paragraph 1", anchor={"page": 2, "paragraph": 1}),
            ParsedSegment(heading="Processing", content="Processing paragraph 2", anchor={"page": 2, "paragraph": 2}),
            ParsedSegment(heading="Outputs", content="Outputs paragraph 1", anchor={"page": 2, "paragraph": 3}),
            ParsedSegment(heading="Appendix", content="Appendix paragraph 1", anchor={"page": 3, "paragraph": 1}),
        ],
    )

    snapshot = build_unified_document_object_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        file_type="docx",
        parsed_document=parsed_document,
    )

    section_nodes = [node for node in snapshot.graph.nodes if node.node_type == "unified_section"]
    paragraph_nodes = [node for node in snapshot.graph.nodes if node.node_type == "unified_paragraph"]

    assert len(section_nodes) == 5
    assert len(paragraph_nodes) == 8
    assert {node.node_id for node in section_nodes}.issubset(snapshot.node_observers.keys())
    assert {node.node_id for node in paragraph_nodes}.issubset(snapshot.node_observers.keys())
    assert any(edge.target == "doc-1:unified-paragraph:8" for edge in snapshot.graph.edges)


def test_archive_document_runtime_stream_endpoint_emits_initial_runtime_event(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/knowledge/archive/nas-a/documents/doc-1/runtime/stream?interval_ms=1000&heartbeat_ms=1000&max_events=1"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    first_event = response.text.split("\n\n", 1)[0]
    assert "retry: 1000" in first_event
    assert "event: runtime" in first_event

    data_line = next(line for line in first_event.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["archive_id"] == "nas-a"
    assert payload["document_id"] == "doc-1"
    assert payload["current_stage_id"] == "quality_policy_evaluation_governance_gate"
    assert len(payload["stages"]) == 13


def test_archive_document_runtime_stream_endpoint_returns_404_for_missing_runtime(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/missing-doc/runtime/stream")
    assert response.status_code == 404
    assert response.json()["detail"] == "Archive document runtime not found"


def test_archive_document_runtime_falls_back_to_running_build_state_before_manifest_exists(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.save_build_state(
        "nas-a",
        {
            "archive_id": "nas-a",
            "archive_name": "NAS Archive",
            "mode": "formal",
            "status": "running",
            "started_at": "2026-04-22T10:00:00+00:00",
            "updated_at": "2026-04-22T10:01:00+00:00",
            "expected_document_count": 1,
            "completed_document_ids": [],
            "pending_document_ids": [],
            "failed_document_id": None,
            "failed_message": None,
            "current_document_id": "doc-live",
            "current_document_title": "Live Runtime Document",
            "current_document_path": "runtime/live.docx",
            "current_chunk": {
                "chunk_id": "chunk-3",
                "position": 3,
                "total": 7,
                "heading": "Evidence assembly",
                "char_count": 1800,
                "segment_count": 4,
                "retry_depth": 0,
            },
            "policy_snapshot": {
                "snapshot_id": "policy-live-1",
                "captured_at": "2026-04-22T10:00:00+00:00",
                "archive_id": "nas-a",
                "version_label": "13 阶段抽取蓝图 v2",
                "scope_label": "单文档抽取过程",
                "ai_autoadapt_enabled": True,
                "config_updated_at": "2026-04-22T09:58:00+00:00",
                "stage_order": ["asset_intake", "parser_router"],
                "stages": [
                    {
                        "stage_id": "asset_intake",
                        "label": "素材接入",
                        "enabled": True,
                        "ai_mode": "轻量识别 + 规则兜底",
                        "default_action": "block_return",
                        "rule_count": 3,
                    }
                ],
            },
            "documents": [
                {
                    "document_id": "doc-live",
                    "path": "runtime/live.docx",
                    "title": "Live Runtime Document",
                    "file_type": "docx",
                    "source_archive": "runtime",
                    "source_file_path": "E:/runtime/live.docx",
                    "source_digest": "sha256:live",
                    "state": "running",
                }
            ],
            "warnings": [],
            "warning_count": 0,
        },
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-live/runtime")
    assert response.status_code == 200
    payload = response.json()

    assert payload["document_id"] == "doc-live"
    assert payload["document_title"] == "Live Runtime Document"
    assert payload["current_stage_id"] == "evidence_graph_chunk_layer"
    assert payload["status"] == "running"
    assert payload["source_document"]["source_file_path"] == "E:/runtime/live.docx"
    assert payload["policy_snapshot"]["version_label"] == "13 阶段抽取蓝图 v2"
    assert payload["policy_snapshot"]["snapshot_id"] == "policy-live-1"


def test_formal_archive_contributions_persist_parse_stage_snapshots_before_document_contribution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact_repository = DocumentArtifactRepository(tmp_path)
    runtime_repository = DocumentRuntimeRepository(tmp_path)
    document_id = _document_id("runtime/live.docx")

    discovered_document = SimpleNamespace(
        path="runtime/live.docx",
        title="Live Runtime Document",
        file_type="docx",
        source_archive="runtime",
        source_file_path="E:/runtime/live.docx",
        source_digest="sha256:live",
    )
    parsed_source_document = SourceDocument(
        path=discovered_document.path,
        title=discovered_document.title,
        file_type=discovered_document.file_type,
        source_archive=discovered_document.source_archive,
        text="live runtime text",
        parser_name="docling_docx",
        segment_count=2,
        segments=[
            ParsedSegment(
                heading="Overview",
                content="Evidence assembly overview",
                anchor={"page": 1, "paragraph": 1},
            ),
            ParsedSegment(
                heading="Detail",
                content="Quality gate detail",
                anchor={"page": 1, "paragraph": 2},
            ),
        ],
        source_file_path=discovered_document.source_file_path,
        source_digest=discovered_document.source_digest,
    )

    monkeypatch.setattr(
        builder_module,
        "parse_discovered_document",
        lambda document, formal_extraction_mode=True: parsed_source_document,
    )

    def fake_build_document_contribution(document, extraction_service, *, document_id=None, policy_snapshot=None):
        del policy_snapshot
        stage_ids = runtime_repository.list_stage_snapshot_ids("nas-a", document_id or "missing")
        assert "asset_intake" in stage_ids
        assert "parser_router" in stage_ids
        assert "parser_execution" in stage_ids
        assert "unified_document_object" in stage_ids
        return _sample_contribution(document_id or "doc-1")

    monkeypatch.setattr(builder_module, "build_document_contribution", fake_build_document_contribution)

    contributions = _build_formal_archive_contributions(
        archive_id="nas-a",
        archive_name="NAS Archive",
        source_dir=tmp_path / "source",
        documents=[discovered_document],
        extraction_service=ExtractionService(formal_extraction_mode=True),
        artifact_repository=artifact_repository,
        warnings=[],
        policy_snapshot=None,
    )

    assert len(contributions) == 1
    persisted_stage_ids = runtime_repository.list_stage_snapshot_ids("nas-a", document_id)
    assert "quality_policy_evaluation_governance_gate" in persisted_stage_ids
    assert "indexes_snapshots_apis" in persisted_stage_ids


def test_archive_document_runtime_backfills_missing_stage_snapshots_for_existing_contribution(
    tmp_path: Path,
) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    service = ArchiveDocumentRuntimeService(tmp_path)
    payload = service.get_document_runtime("nas-a", "doc-1")

    assert payload is not None
    assert payload["runtime_mode"] == "persisted"
    assert len(payload["persisted_stage_ids"]) == 13
    runtime_repository = DocumentRuntimeRepository(tmp_path)
    assert runtime_repository.load_stage_snapshot("nas-a", "doc-1", "asset_intake") is not None
    assert runtime_repository.load_stage_snapshot(
        "nas-a",
        "doc-1",
        "quality_policy_evaluation_governance_gate",
    ) is not None


def test_archive_document_runtime_refreshes_outdated_unified_document_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    outdated_snapshot = build_unified_document_object_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        file_type="docx",
        parsed_document=ParsedDocument(
            parser_name="docling.docx",
            parser_version="legacy",
            segments=[
                ParsedSegment(heading="Overview", content="Only one paragraph", anchor={"page": 1, "paragraph": 1}),
            ],
        ),
    ).model_dump(mode="json")
    outdated_snapshot["graph"]["nodes"][0]["metrics"]["paragraph_count"] = 8
    outdated_snapshot["graph"]["nodes"][0]["metrics"]["section_count"] = 4
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "unified_document_object", outdated_snapshot)

    service = ArchiveDocumentRuntimeService(tmp_path)
    monkeypatch.setattr(
        service.runtime_snapshot_service,
        "load_or_derive_parsed_document",
        lambda document: ParsedDocument(
            parser_name="docling.docx",
            parser_version="1.0.0",
            segments=[
                ParsedSegment(heading="Overview", content="Overview paragraph 1", anchor={"page": 1, "paragraph": 1}),
                ParsedSegment(heading="Overview", content="Overview paragraph 2", anchor={"page": 1, "paragraph": 2}),
                ParsedSegment(heading="Inputs", content="Inputs paragraph 1", anchor={"page": 1, "paragraph": 3}),
                ParsedSegment(heading="Inputs", content="Inputs paragraph 2", anchor={"page": 1, "paragraph": 4}),
                ParsedSegment(heading="Processing", content="Processing paragraph 1", anchor={"page": 2, "paragraph": 1}),
                ParsedSegment(heading="Processing", content="Processing paragraph 2", anchor={"page": 2, "paragraph": 2}),
                ParsedSegment(heading="Outputs", content="Outputs paragraph 1", anchor={"page": 2, "paragraph": 3}),
                ParsedSegment(heading="Appendix", content="Appendix paragraph 1", anchor={"page": 3, "paragraph": 1}),
            ],
        ),
    )

    payload = service.get_document_runtime("nas-a", "doc-1")

    assert payload is not None
    refreshed_stage = next(stage for stage in payload["stages"] if stage["stage_id"] == "unified_document_object")
    paragraph_nodes = [node for node in refreshed_stage["graph"]["nodes"] if node["node_type"] == "unified_paragraph"]
    section_nodes = [node for node in refreshed_stage["graph"]["nodes"] if node["node_type"] == "unified_section"]
    assert len(paragraph_nodes) == 8
    assert len(section_nodes) == 5


def test_archive_document_runtime_prefers_persisted_asset_intake_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_asset_intake_snapshot(
        archive_id="nas-a",
        archive_name="NAS Archive",
        document_id="doc-1",
        document_title="Persisted Intake Example",
        document_path="runtime/SV-2.docx",
        source_dir=tmp_path / "source",
        source_file_path="E:/sample/SV-2.docx",
        file_type="docx",
        source_archive="test-archive",
        source_digest="sha256:persisted",
        included_in_archive=True,
        mode="archive_extract",
        intake_timestamp="2026-04-21T10:00:00+00:00",
    )
    snapshot.stage_observer.title = "Persisted Asset Intake"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "asset_intake", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    asset_intake = payload["stages"][0]
    assert payload["runtime_mode"] == "hybrid"
    assert payload["persisted_stage_ids"] == ["asset_intake"]
    assert asset_intake["stage_observer"]["title"] == "Persisted Asset Intake"
    assert asset_intake["graph"]["nodes"][0]["label"] == "Persisted Intake Example"


def test_archive_document_runtime_prefers_persisted_parser_router_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_parser_router_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        file_type="docx",
        source_file_path="E:/sample/SV-2.docx",
        parser_name="docling.docx",
        parser_version="9.9.9",
    )
    snapshot.stage_observer.title = "Persisted Parser Router"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "parser_router", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    parser_router = next(stage for stage in payload["stages"] if stage["stage_id"] == "parser_router")
    assert parser_router["stage_observer"]["title"] == "Persisted Parser Router"


def test_build_document_contribution_attaches_runtime_trace(monkeypatch) -> None:
    document = SourceDocument(
        path="runtime/live.docx",
        title="Live Runtime Document",
        file_type="docx",
        source_archive="runtime",
        text="Overview paragraph\nDetail paragraph",
        parser_name="docling_docx",
        segment_count=2,
        segments=[
            ParsedSegment(heading="Overview", content="Overview paragraph", anchor={"page": 1, "paragraph": 1}),
            ParsedSegment(heading="Detail", content="Detail paragraph", anchor={"page": 1, "paragraph": 2}),
        ],
        source_file_path="E:/runtime/live.docx",
        source_digest="sha256:live",
    )

    def fake_extract(document, doc_id, extraction_service):
        del extraction_service
        return ExtractionBatch(
            document_id=doc_id,
            title=document.title,
            strategy="formal",
            schema_version="p1.v1",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Gate Input Relation R-17",
                    payload={
                        "id": "entity-1",
                        "category": "relation_candidate",
                        "aliases": [],
                        "evidence": "Gate input relation appears in overview paragraph.",
                        "source_refs": [
                            {
                                "chunk_id": "chunk-001",
                                "chunk_heading": "Overview",
                                "segment_ids": ["segment-1"],
                                "anchors": [{"page": 1, "paragraph": 1}],
                            }
                        ],
                    },
                )
            ],
            relations=[],
            metadata={
                "runtime_trace": {
                    "unified_document_object": {
                        "events": [
                            {
                                "event_id": "doc-1:unified",
                                "kind": "result",
                                "level": "success",
                                "message": "Unified document object normalized two segments.",
                                "object_id": "doc-1:unified-document",
                                "object_kind": "node",
                            }
                        ],
                        "sections": [
                            {
                                "section_id": "trace-unified",
                                "title": "Runtime Trace",
                                "fields": [{"key": "input_count", "label": "input_count", "value": "2", "tone": "info"}],
                            }
                        ],
                    }
                }
            },
        )

    monkeypatch.setattr(
        "app.archive_knowledge.document_artifacts._extract_document_knowledge",
        fake_extract,
    )

    contribution = builder_module.build_document_contribution(document, extraction_service=None)

    runtime_trace = contribution["extraction"]["runtime_trace"]
    assert "unified_document_object" in runtime_trace
    assert "quality_policy_evaluation_governance_gate" in runtime_trace
    assert runtime_trace["quality_policy_evaluation_governance_gate"]["decision"]["status"] == "blocked"


def test_quality_gate_policy_snapshot_changes_gate_decision(monkeypatch) -> None:
    document = SourceDocument(
        path="runtime/live.docx",
        title="Live Runtime Document",
        file_type="docx",
        source_archive="runtime",
        text="Overview paragraph\nDetail paragraph",
        parser_name="docling_docx",
        segment_count=2,
        segments=[
            ParsedSegment(heading="Overview", content="Overview paragraph", anchor={"page": 1, "paragraph": 1}),
            ParsedSegment(heading="Detail", content="Detail paragraph", anchor={"page": 1, "paragraph": 2}),
        ],
        source_file_path="E:/runtime/live.docx",
        source_digest="sha256:live",
    )

    def fake_extract(document, doc_id, extraction_service):
        del extraction_service
        return ExtractionBatch(
            document_id=doc_id,
            title=document.title,
            strategy="formal",
            schema_version="p1.v1",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Gate Input Relation R-17",
                    payload={
                        "id": "entity-1",
                        "category": "relation_candidate",
                        "aliases": [],
                        "evidence": "Gate input relation appears in overview paragraph.",
                    },
                )
            ],
            relations=[],
            metadata={},
        )

    monkeypatch.setattr(
        "app.archive_knowledge.document_artifacts._extract_document_knowledge",
        fake_extract,
    )

    policy_config = build_default_archive_policy_config("nas-a")
    quality_gate = policy_config["stages"]["quality_policy_evaluation_governance_gate"]
    quality_gate["rules"] = [
        {
            "key": "gate-support",
            "name": "supporting document minimum",
            "meaning": "allow single-document support in this test policy",
            "threshold": "supporting_documents >= 1",
            "action": "block_return",
        },
        {
            "key": "gate-risk",
            "name": "risk score ceiling",
            "meaning": "allow pending review to continue for this test policy",
            "threshold": "risk_score < 1",
            "action": "manual_review",
        },
        {
            "key": "gate-conflict",
            "name": "hard conflict block",
            "meaning": "block only hard conflicts",
            "threshold": "hard_conflict = 0",
            "action": "block_return",
        },
    ]
    policy_snapshot = build_policy_run_snapshot("nas-a", policy_config, captured_at="2026-04-23T10:00:00+00:00")

    contribution = builder_module.build_document_contribution(
        document,
        extraction_service=None,
        policy_snapshot=policy_snapshot,
    )
    quality_trace = contribution["extraction"]["runtime_trace"]["quality_policy_evaluation_governance_gate"]

    assert quality_trace["policy"]["snapshot_id"] == policy_snapshot["snapshot_id"]
    assert quality_trace["decision"]["status"] == "passed"
    assert [hit["key"] for hit in quality_trace["rule_hits"]] == ["gate-support", "gate-risk", "gate-conflict"]
    assert all(hit["outcome"] == "passed" for hit in quality_trace["rule_hits"])

    snapshot = build_quality_gate_snapshot(
        archive_id="nas-a",
        document_id=contribution["document"]["id"],
        document_title=contribution["document"]["title"],
        contribution=contribution,
        runtime_trace=quality_trace,
    )
    rule_nodes = [node for node in snapshot.graph.nodes if node.node_type == "rule_hit"]
    assert snapshot.status == "completed"
    assert len(rule_nodes) == 3
    assert any(node.attributes["rule_key"] == "gate-risk" for node in rule_nodes)


def test_quality_gate_does_not_route_to_manual_review_for_warning_policy() -> None:
    contribution = _sample_contribution("doc-qg-warning")
    policy_config = build_default_archive_policy_config("nas-a")
    quality_gate = policy_config["stages"]["quality_policy_evaluation_governance_gate"]
    quality_gate["rules"] = [
        {
            "key": "gate-support",
            "name": "supporting document minimum",
            "meaning": "single source is enough for this policy",
            "threshold": "supporting_documents >= 1",
            "action": "block_return",
        },
        {
            "key": "gate-risk",
            "name": "risk score ceiling",
            "meaning": "legacy manual review action must become a gate warning",
            "threshold": "risk_score < 0.1",
            "action": "manual_review",
        },
        {
            "key": "gate-conflict",
            "name": "hard conflict block",
            "meaning": "block only hard conflicts",
            "threshold": "hard_conflict = 0",
            "action": "block_return",
        },
    ]
    policy_snapshot = build_policy_run_snapshot("nas-a", policy_config, captured_at="2026-04-23T10:00:00+00:00")

    trace = build_quality_gate_runtime_trace(
        document_id="doc-qg-warning",
        document_title="Quality Gate Warning",
        contribution=contribution,
        policy_snapshot=policy_snapshot,
    )

    risk_hit = next(hit for hit in trace["rule_hits"] if hit["key"] == "gate-risk")
    assert risk_hit["outcome"] == "failed"
    assert risk_hit["action"] == "warn_continue"
    assert trace["decision"]["status"] == "warning"
    assert trace["decision"]["next_action"] == "continue_with_warning"

    snapshot = build_quality_gate_snapshot(
        archive_id="nas-a",
        document_id="doc-qg-warning",
        document_title="Quality Gate Warning",
        contribution=contribution,
        runtime_trace=trace,
    )
    assert snapshot.status == "warning"
    assert all(node.node_type != "manual_review" for node in snapshot.graph.nodes)


def test_archive_document_runtime_uses_build_state_current_stage(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.save_build_state(
        "nas-a",
        {
            "archive_id": "nas-a",
            "archive_name": "NAS Archive",
            "mode": "formal",
            "status": "running",
            "started_at": "2026-04-23T10:00:00+00:00",
            "updated_at": "2026-04-23T10:00:05+00:00",
            "expected_document_count": 1,
            "completed_document_ids": [],
            "pending_document_ids": [],
            "failed_document_id": None,
            "failed_message": None,
            "current_document_id": "doc-live",
            "current_document_title": "Live Runtime Document",
            "current_document_path": "runtime/live.docx",
            "current_chunk": None,
            "current_stage_id": "evidence_constructor",
            "current_stage_label": "Evidence Constructor",
            "current_stage_status": "running",
            "current_stage_message": "Evidence constructor is assembling traceable evidence units.",
            "documents": [
                {
                    "document_id": "doc-live",
                    "path": "runtime/live.docx",
                    "title": "Live Runtime Document",
                    "file_type": "docx",
                    "source_archive": "runtime",
                    "source_file_path": "E:/runtime/live.docx",
                    "source_digest": "sha256:live",
                    "state": "running",
                }
            ],
            "warnings": [],
            "warning_count": 0,
            "policy_snapshot": None,
        },
    )

    service = ArchiveDocumentRuntimeService(tmp_path)
    payload = service.get_document_runtime("nas-a", "doc-live")

    assert payload is not None
    assert payload["current_stage_id"] == "evidence_constructor"
    assert next(stage for stage in payload["stages"] if stage["stage_id"] == "evidence_constructor")["status"] == "running"


def test_archive_document_runtime_prefers_persisted_evidence_pack_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_evidence_pack_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
    )
    snapshot.stage_observer.title = "Persisted Evidence Pack"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "evidence_pack", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    evidence_pack = next(stage for stage in payload["stages"] if stage["stage_id"] == "evidence_pack")
    assert evidence_pack["stage_observer"]["title"] == "Persisted Evidence Pack"
    assert evidence_pack["graph"]["nodes"]


def test_archive_document_runtime_prefers_persisted_concept_candidate_review_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_concept_candidate_review_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
    )
    snapshot.stage_observer.title = "Persisted Concept Candidate Review"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "concept_candidate_review",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    concept_candidate_review = next(
        stage for stage in payload["stages"] if stage["stage_id"] == "concept_candidate_review"
    )
    assert concept_candidate_review["stage_observer"]["title"] == "Persisted Concept Candidate Review"
    assert concept_candidate_review["graph"]["nodes"]
    assert concept_candidate_review["graph"]["edges"]


def test_archive_document_runtime_prefers_persisted_relation_review_family_normalization_snapshot(
    tmp_path: Path,
) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_relation_review_family_normalization_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
    )
    snapshot.stage_observer.title = "Persisted Relation Review / Family Normalization"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "relation_review_family_normalization",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    stage = next(stage for stage in payload["stages"] if stage["stage_id"] == "relation_review_family_normalization")
    assert stage["stage_observer"]["title"] == "Persisted Relation Review / Family Normalization"
    assert stage["graph"]["nodes"]
    assert stage["graph"]["edges"]


def test_archive_document_runtime_prefers_persisted_definition_summary_conflict_consolidation_snapshot(
    tmp_path: Path,
) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_definition_summary_conflict_consolidation_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
    )
    snapshot.stage_observer.title = "Persisted Definition / Summary / Conflict Consolidation"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "definition_summary_conflict_consolidation",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    stage = next(
        stage for stage in payload["stages"] if stage["stage_id"] == "definition_summary_conflict_consolidation"
    )
    assert stage["stage_observer"]["title"] == "Persisted Definition / Summary / Conflict Consolidation"
    assert stage["graph"]["nodes"]
    assert stage["graph"]["edges"]


def test_archive_document_runtime_prefers_persisted_parser_execution_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_parser_execution_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        file_type="docx",
        parsed_document=ParsedDocument(
            parser_name="docling.docx",
            parser_version="9.9.9",
            segments=[
                ParsedSegment(
                    heading="Section 1",
                    content="Mission orchestration overview.",
                    anchor={"page": 1, "paragraph": 1},
                )
            ],
        ),
    )
    snapshot.stage_observer.title = "Persisted Parser Execution"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "parser_execution", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    parser_execution = next(stage for stage in payload["stages"] if stage["stage_id"] == "parser_execution")
    assert parser_execution["stage_observer"]["title"] == "Persisted Parser Execution"
    assert parser_execution["graph"]["nodes"]


def test_archive_document_runtime_prefers_persisted_unified_document_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    repository.upsert("nas-a", _sample_contribution(), included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_unified_document_object_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        file_type="docx",
        parsed_document=ParsedDocument(
            parser_name="docling.docx",
            parser_version="9.9.9",
            segments=[
                ParsedSegment(
                    heading="Section 1",
                    content="Mission orchestration overview.",
                    anchor={"page": 1, "paragraph": 1},
                )
            ],
        ),
    )
    snapshot.stage_observer.title = "Persisted Unified Document"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "unified_document_object", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    unified_document = next(stage for stage in payload["stages"] if stage["stage_id"] == "unified_document_object")
    assert unified_document["stage_observer"]["title"] == "Persisted Unified Document"
    assert unified_document["graph"]["nodes"]


def test_archive_document_runtime_prefers_persisted_evidence_constructor_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_evidence_constructor_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
        parsed_document=ParsedDocument(
            parser_name="docling.docx",
            parser_version="9.9.9",
            segments=[
                ParsedSegment(
                    heading="Overview",
                    content="National Airspace System overview.",
                    anchor={"page": 1, "paragraph": 1},
                ),
                ParsedSegment(
                    heading="Mission",
                    content="Mission orchestration depends on evidence packs.",
                    anchor={"page": 1, "paragraph": 2},
                ),
            ],
        ),
    )
    snapshot.stage_observer.title = "Persisted Evidence Constructor"
    runtime_repository.save_stage_snapshot("nas-a", "doc-1", "evidence_constructor", snapshot.model_dump(mode="json"))

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    evidence_constructor = next(stage for stage in payload["stages"] if stage["stage_id"] == "evidence_constructor")
    assert evidence_constructor["stage_observer"]["title"] == "Persisted Evidence Constructor"
    assert evidence_constructor["graph"]["nodes"]


def test_archive_document_runtime_prefers_persisted_evidence_graph_chunk_layer_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_evidence_graph_chunk_layer_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
        parsed_document=ParsedDocument(
            parser_name="docling.docx",
            parser_version="9.9.9",
            segments=[
                ParsedSegment(
                    heading="Overview",
                    content="National Airspace System overview.",
                    anchor={"page": 1, "paragraph": 1},
                ),
                ParsedSegment(
                    heading="Mission",
                    content="Mission orchestration depends on evidence packs.",
                    anchor={"page": 1, "paragraph": 2},
                ),
            ],
        ),
    )
    snapshot.stage_observer.title = "Persisted Evidence Graph / Chunk Layer"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "evidence_graph_chunk_layer",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    stage = next(stage for stage in payload["stages"] if stage["stage_id"] == "evidence_graph_chunk_layer")
    assert stage["stage_observer"]["title"] == "Persisted Evidence Graph / Chunk Layer"
    assert stage["graph"]["nodes"]
    assert stage["graph"]["edges"]


def test_archive_document_runtime_prefers_persisted_quality_gate_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_quality_gate_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
        knowledge_items=ArchiveKnowledgeService._build_document_knowledge_items_from_contribution(
            contribution,
            contribution["document"],
        ),
    )
    snapshot.stage_observer.title = "Persisted Quality Gate"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "quality_policy_evaluation_governance_gate",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    quality_gate = next(
        stage for stage in payload["stages"] if stage["stage_id"] == "quality_policy_evaluation_governance_gate"
    )
    assert quality_gate["stage_observer"]["title"] == "Persisted Quality Gate"
    assert quality_gate["graph"]["nodes"]


def test_archive_document_runtime_prefers_persisted_canonical_knowledge_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_canonical_knowledge_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        contribution=contribution,
        knowledge_items=ArchiveKnowledgeService._build_document_knowledge_items_from_contribution(
            contribution,
            contribution["document"],
        ),
    )
    snapshot.stage_observer.title = "Persisted Canonical Knowledge"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "canonical_knowledge",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    canonical_knowledge = next(stage for stage in payload["stages"] if stage["stage_id"] == "canonical_knowledge")
    assert canonical_knowledge["stage_observer"]["title"] == "Persisted Canonical Knowledge"
    assert canonical_knowledge["graph"]["nodes"]
    assert canonical_knowledge["graph"]["edges"]


def test_archive_document_runtime_prefers_persisted_indexes_snapshots_apis_snapshot(tmp_path: Path) -> None:
    repository = DocumentArtifactRepository(tmp_path)
    contribution = _sample_contribution()
    repository.upsert("nas-a", contribution, included_in_archive=True)

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = build_indexes_snapshots_apis_snapshot(
        archive_id="nas-a",
        document_id="doc-1",
        document_title="SV-2 Translation",
        current_version={"version_label": "v2026.04"},
        document_published=True,
    )
    snapshot.stage_observer.title = "Persisted Indexes / Snapshots / APIs"
    runtime_repository.save_stage_snapshot(
        "nas-a",
        "doc-1",
        "indexes_snapshots_apis",
        snapshot.model_dump(mode="json"),
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/nas-a/documents/doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()
    indexes_snapshots_apis = next(
        stage for stage in payload["stages"] if stage["stage_id"] == "indexes_snapshots_apis"
    )
    assert indexes_snapshots_apis["stage_observer"]["title"] == "Persisted Indexes / Snapshots / APIs"
    assert indexes_snapshots_apis["graph"]["nodes"]
    assert indexes_snapshots_apis["graph"]["edges"]


def test_import_document_persists_asset_intake_snapshot(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / ".extract" / "nas-a"
    extract_root.mkdir(parents=True)

    existing_repository = DocumentArtifactRepository(tmp_path)
    existing_repository.upsert("nas-a", _sample_contribution("doc-existing"), included_in_archive=True)

    document_path = f"manual_uploads/{date.today().isoformat()}/new.docx"
    document_id = _document_id(document_path)

    monkeypatch.setattr(
        ArchiveExtractionService,
        "_build_uploaded_source_document",
        staticmethod(
            lambda *, source_dir, stored_file_path, source_digest: SourceDocument(
                path=document_path,
                title="New Intake Doc",
                file_type="docx",
                source_archive="manual_uploads",
                text="Example text",
                parser_name="docling.docx",
                segment_count=1,
                segments=[
                    ParsedSegment(
                        heading="Overview",
                        content="Example text",
                        anchor={"page": 1, "paragraph": 1},
                    )
                ],
                source_file_path=str(stored_file_path),
                source_digest=source_digest,
            )
        ),
    )
    monkeypatch.setattr(
        "app.archive_knowledge.extraction.build_document_contribution",
        lambda document, extraction_service=None, *, document_id=None: {
            **_sample_contribution(document_id or "doc-new"),
            "document": {
                "id": document_id or "doc-new",
                "path": document.path,
                "title": document.title,
                "file_type": document.file_type,
                "source_archive": document.source_archive,
                "character_count": len(document.text),
                "parser_name": document.parser_name,
                "segment_count": document.segment_count,
                "source_file_path": document.source_file_path,
                "source_digest": document.source_digest,
            },
        },
    )
    monkeypatch.setattr(
        ArchiveExtractionService,
        "_rebuild_archive_from_artifacts",
        lambda self, **kwargs: SimpleNamespace(summary={"document_count": 2}),
    )
    monkeypatch.setattr(
        ArchiveKnowledgeService,
        "get_document_detail",
        lambda self, archive_id, document_id: {"document": {"id": document_id, "title": "New Intake Doc"}},
    )

    service = ArchiveExtractionService(tmp_path)
    result = service.import_document(
        "nas-a",
        file_name="new.docx",
        file_bytes=b"demo-content",
        source_dir=source_dir,
        extract_root=extract_root,
        archive_name="NAS Archive",
    )

    assert result["document_id"] == document_id

    runtime_repository = DocumentRuntimeRepository(tmp_path)
    snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "asset_intake")
    assert snapshot is not None
    assert snapshot["stage_id"] == "asset_intake"
    assert snapshot["stage_observer"]["title"] == "Asset Intake"
    assert snapshot["graph"]["nodes"]

    parser_router_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "parser_router")
    assert parser_router_snapshot is not None
    assert parser_router_snapshot["stage_id"] == "parser_router"
    assert parser_router_snapshot["stage_observer"]["title"] == "Parser Router"
    assert parser_router_snapshot["graph"]["nodes"]

    parser_execution_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "parser_execution")
    assert parser_execution_snapshot is not None
    assert parser_execution_snapshot["stage_id"] == "parser_execution"
    assert parser_execution_snapshot["stage_observer"]["title"] == "Parser Execution"
    assert parser_execution_snapshot["graph"]["nodes"]

    unified_document_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "unified_document_object")
    assert unified_document_snapshot is not None
    assert unified_document_snapshot["stage_id"] == "unified_document_object"
    assert unified_document_snapshot["stage_observer"]["title"] == "Unified Document Object"
    assert unified_document_snapshot["graph"]["nodes"]

    evidence_constructor_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "evidence_constructor")
    assert evidence_constructor_snapshot is not None
    assert evidence_constructor_snapshot["stage_id"] == "evidence_constructor"
    assert evidence_constructor_snapshot["stage_observer"]["title"] == "Evidence Constructor"
    assert evidence_constructor_snapshot["graph"]["nodes"]

    evidence_graph_chunk_layer_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "evidence_graph_chunk_layer",
    )
    assert evidence_graph_chunk_layer_snapshot is not None
    assert evidence_graph_chunk_layer_snapshot["stage_id"] == "evidence_graph_chunk_layer"
    assert evidence_graph_chunk_layer_snapshot["stage_observer"]["title"] == "Evidence Graph / Chunk Layer"
    assert evidence_graph_chunk_layer_snapshot["graph"]["nodes"]
    assert evidence_graph_chunk_layer_snapshot["graph"]["edges"]

    evidence_pack_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "evidence_pack")
    assert evidence_pack_snapshot is not None
    assert evidence_pack_snapshot["stage_id"] == "evidence_pack"
    assert evidence_pack_snapshot["stage_observer"]["title"] == "阶段视角 · 证据包"
    assert evidence_pack_snapshot["graph"]["nodes"]

    concept_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "concept_candidate_review",
    )
    assert concept_snapshot is not None
    assert concept_snapshot["stage_id"] == "concept_candidate_review"
    assert concept_snapshot["stage_observer"]["title"] == "Concept Candidate Review"
    assert concept_snapshot["graph"]["nodes"]
    assert concept_snapshot["graph"]["edges"]

    relation_review_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "relation_review_family_normalization",
    )
    assert relation_review_snapshot is not None
    assert relation_review_snapshot["stage_id"] == "relation_review_family_normalization"
    assert relation_review_snapshot["stage_observer"]["title"] == "Relation Review / Family Normalization"
    assert relation_review_snapshot["graph"]["nodes"]
    assert relation_review_snapshot["graph"]["edges"]

    definition_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "definition_summary_conflict_consolidation",
    )
    assert definition_snapshot is not None
    assert definition_snapshot["stage_id"] == "definition_summary_conflict_consolidation"
    assert definition_snapshot["stage_observer"]["title"] == "Definition / Summary / Conflict Consolidation"
    assert definition_snapshot["graph"]["nodes"]
    assert definition_snapshot["graph"]["edges"]

    canonical_snapshot = runtime_repository.load_stage_snapshot("nas-a", document_id, "canonical_knowledge")
    assert canonical_snapshot is not None
    assert canonical_snapshot["stage_id"] == "canonical_knowledge"
    assert canonical_snapshot["stage_observer"]["title"] == "Canonical Knowledge"
    assert canonical_snapshot["graph"]["nodes"]
    assert canonical_snapshot["graph"]["edges"]

    quality_gate_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "quality_policy_evaluation_governance_gate",
    )
    assert quality_gate_snapshot is not None
    assert quality_gate_snapshot["stage_id"] == "quality_policy_evaluation_governance_gate"
    assert quality_gate_snapshot["stage_observer"]["title"] == "阶段视角 · 质量门禁"
    assert quality_gate_snapshot["graph"]["nodes"]

    indexes_snapshot = runtime_repository.load_stage_snapshot(
        "nas-a",
        document_id,
        "indexes_snapshots_apis",
    )
    assert indexes_snapshot is not None
    assert indexes_snapshot["stage_id"] == "indexes_snapshots_apis"
    assert indexes_snapshot["stage_observer"]["title"] == "Indexes / Snapshots / APIs"
    assert indexes_snapshot["graph"]["nodes"]
    assert indexes_snapshot["graph"]["edges"]


def test_archive_document_runtime_falls_back_to_legacy_archive_payload(tmp_path: Path) -> None:
    legacy_payload = {
        "documents": [
            {
                "id": "legacy-doc-1",
                "path": "legacy/overview.pdf",
                "title": "Legacy Overview",
                "file_type": "pdf",
                "source_archive": "legacy-source",
                "character_count": 1800,
            }
        ],
        "entities": [
            {
                "id": "entity-legacy-1",
                "name": "Legacy NAS",
                "category": "domain_concept",
                "aliases": ["NAS Legacy"],
                "document_ids": ["legacy-doc-1"],
                "evidence": [{"document_id": "legacy-doc-1", "excerpt": "Legacy NAS overview."}],
                "review_status": "approved",
            }
        ],
        "events": [],
        "processes": [],
        "relations": [],
        "summary": {
            "document_count": 1,
            "entity_count": 1,
            "event_count": 0,
            "process_count": 0,
        },
    }
    (tmp_path / "legacy-archive-knowledge-curated.json").write_text(
        json.dumps(legacy_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    app = create_app()
    app.dependency_overrides[get_archive_document_runtime_service] = lambda: ArchiveDocumentRuntimeService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/knowledge/archive/legacy-archive/documents/legacy-doc-1/runtime")
    assert response.status_code == 200
    payload = response.json()

    assert payload["document_id"] == "legacy-doc-1"
    assert payload["document_title"] == "Legacy Overview"
    assert len(payload["stages"]) == 13
    assert payload["runtime_mode"] == "legacy_fallback"
    assert payload["persisted_stage_ids"] == []
    assert payload["stages"][0]["stage_id"] == "asset_intake"
