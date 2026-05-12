from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.p1_refactor import get_p1_resolution_service
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.resolution import ArchiveKnowledgeResolutionService
from app.archive_knowledge.runtime_incremental_rebuild import (
    ArchiveRuntimeIncrementalRebuildService,
    ImpactSet as RuntimeImpactSet,
)
from app.main import create_app


def test_midterm_resolution_merges_av_ov_sv_objects_and_relations(tmp_path) -> None:
    app = create_app()
    _write_midterm_resolution_artifacts(tmp_path)
    app.dependency_overrides[get_p1_resolution_service] = lambda: ArchiveKnowledgeResolutionService(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/p1/archives/midterm/knowledge-resolution/latest",
        params={
            "runtime_snapshot_id": "RUN-MIDTERM-001",
            "policy_package_version_id": "PKGV-MIDTERM-R1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_kind"] == "live"
    snapshot = body["data"]
    assert snapshot["runtime_snapshot_id"] == "RUN-MIDTERM-001"
    assert snapshot["policy_package_version_id"] == "PKGV-MIDTERM-R1"

    nas_object = next(
        item
        for item in snapshot["resolved_objects"]
        if item["canonical_name"] == "NAS Enterprise Architecture"
    )
    assert nas_object["object_type"] == "system"
    assert set(nas_object["source_document_ids"]) == {"av-1", "ov-2", "sv-1"}
    assert set(nas_object["source_candidate_ids"]) == {
        "av-1:system-nas-ea-av",
        "ov-2:system-nas-ea-ov",
        "sv-1:system-nas-ea-sv",
    }
    assert len(nas_object["evidence_refs"]) == 3
    assert nas_object["confidence"] >= 0.85
    assert nas_object["merge_decision"] == "merged"
    assert nas_object["conflict_status"] == "clean"

    support_relations = [
        relation
        for relation in snapshot["resolved_relations"]
        if relation["source_object_id"] == nas_object["object_id"] and relation["relation_type"] == "support"
    ]
    assert support_relations
    assert set(support_relations[0]["source_document_ids"]) == {"av-1", "ov-2"}
    assert support_relations[0]["confidence"] >= 0.82

    merge_trace = [
        trace
        for trace in snapshot["resolution_trace"]
        if trace["trace_type"] == "merge_decision"
        and nas_object["object_id"] in trace["object_ids"]
        and trace["metadata"]["match_features"]["view_number_score"] >= 0.9
    ]
    assert merge_trace


def test_midterm_resolution_keeps_conflicts_and_marks_stale_candidates(tmp_path) -> None:
    app = create_app()
    _write_midterm_resolution_artifacts(tmp_path)
    impact_set = RuntimeImpactSet(
        impact_id="impact-midterm-resolution",
        archive_id="midterm",
        changed_rule_ids=["RL-KR-VIEW-MERGE-001"],
        changed_stage_ids=["knowledge_resolution"],
        affected_docs=["ov-2"],
        affected_document_ids=["ov-2"],
        affected_stages=["knowledge_resolution", "publication_candidate"],
        affected_stage_ids=["knowledge_resolution", "publication_candidate"],
        affected_candidates=["ov-2:system-nas-ea-ov"],
        affected_candidate_ids=["ov-2:system-nas-ea-ov"],
        affected_relations=["ov-2:rel-supports"],
        affected_relation_ids=["ov-2:rel-supports"],
        affected_publication_snapshots=["PCS-midterm-candidate"],
        affected_publication_snapshot_ids=["PCS-midterm-candidate"],
        minimum_rebuild_stage_id="knowledge_resolution",
        source_policy_snapshot_id="PKGV-MIDTERM-R0",
        target_policy_snapshot_id="PKGV-MIDTERM-R1",
        generated_at="2026-05-11T00:00:00+08:00",
    )
    ArchiveRuntimeIncrementalRebuildService(tmp_path).create_incremental_rebuild_task("midterm", impact_set)
    app.dependency_overrides[get_p1_resolution_service] = lambda: ArchiveKnowledgeResolutionService(tmp_path)
    client = TestClient(app)

    response = client.get("/api/p1/archives/midterm/knowledge-resolution/latest")

    assert response.status_code == 200
    snapshot = response.json()["data"]
    conflict_objects = [
        item
        for item in snapshot["resolved_objects"]
        if item["canonical_name"] == "Trajectory Synchronization"
    ]
    assert len(conflict_objects) == 2
    assert {item["conflict_status"] for item in conflict_objects} == {"conflict_pending"}
    assert snapshot["conflict_count"] >= 1
    assert any(
        trace["trace_type"] == "conflict"
        and "Trajectory Synchronization" not in trace["reason"]
        and trace["evidence_refs"]
        for trace in snapshot["resolution_trace"]
    )

    nas_object = next(
        item
        for item in snapshot["resolved_objects"]
        if "ov-2:system-nas-ea-ov" in item["source_candidate_ids"]
    )
    assert nas_object["conflict_status"] == "stale"
    assert snapshot["update_plan"]["minimum_rebuild_stage_id"] == "knowledge_resolution"
    assert snapshot["update_plan"]["writes_official_knowledge"] is False
    assert (tmp_path / "midterm-knowledge.json").exists() is False


def _write_midterm_resolution_artifacts(output_root) -> None:
    DocumentArtifactRepository(output_root).replace_all(
        "midterm",
        [
            _contribution(
                document_id="av-1",
                title="NAS-EA AV-1 Mid Term Overview",
                entities=[
                    _entity(
                        "system-nas-ea-av",
                        "NAS Enterprise Architecture",
                        aliases=["NAS EA"],
                        evidence="AV-1 identifies the NAS Enterprise Architecture as the cross-view architecture baseline.",
                    ),
                    _entity(
                        "system-swim-av",
                        "System Wide Information Management",
                        aliases=["SWIM"],
                        evidence="AV-1 names System Wide Information Management as a supporting NAS capability.",
                    ),
                ],
                processes=[
                    _process(
                        "process-trajectory-av",
                        "Trajectory Synchronization",
                        "Trajectory synchronization aligns planned flight trajectories before departure.",
                        "AV evidence for flight trajectory planning synchronization.",
                    )
                ],
                relations=[
                    _relation(
                        "rel-supports",
                        "supports",
                        "NAS Enterprise Architecture",
                        "System Wide Information Management",
                        evidence="AV-1 states that the architecture baseline supports SWIM alignment.",
                        confidence=0.84,
                    )
                ],
            ),
            _contribution(
                document_id="ov-2",
                title="NAS-EA OV-2 Mid Term Operational Resource Flow",
                entities=[
                    _entity(
                        "system-nas-ea-ov",
                        "OV-2 NAS Enterprise Architecture",
                        aliases=["NAS Enterprise Architecture"],
                        evidence="OV-2 places the NAS Enterprise Architecture in the operational resource flow.",
                    ),
                    _entity(
                        "system-swim-ov",
                        "SWIM",
                        aliases=["System Wide Information Management"],
                        evidence="OV-2 shows SWIM exchanging operational information across resources.",
                    ),
                ],
                processes=[],
                relations=[
                    _relation(
                        "rel-supports",
                        "supports",
                        "OV-2 NAS Enterprise Architecture",
                        "SWIM",
                        evidence="OV-2 links the architecture object to SWIM support.",
                        confidence=0.86,
                    )
                ],
            ),
            _contribution(
                document_id="sv-1",
                title="NAS-EA SV-1 Mid Term Systems Interface Description",
                entities=[
                    _entity(
                        "system-nas-ea-sv",
                        "SV-1 NAS Enterprise Architecture",
                        aliases=["NAS Enterprise Architecture"],
                        evidence="SV-1 reuses the NAS Enterprise Architecture as the system interface context.",
                    ),
                    _entity(
                        "system-swim-sv",
                        "System Wide Information Management",
                        aliases=["SWIM"],
                        evidence="SV-1 details SWIM as the service interface layer.",
                    ),
                ],
                processes=[
                    _process(
                        "process-trajectory-sv",
                        "Trajectory Synchronization",
                        "Trajectory synchronization retires obsolete surveillance nodes from the service view.",
                        "SV evidence describes surveillance-node retirement, not flight trajectory planning.",
                    )
                ],
                relations=[
                    _relation(
                        "rel-exchanges",
                        "exchanges",
                        "SV-1 NAS Enterprise Architecture",
                        "System Wide Information Management",
                        evidence="SV-1 shows architecture-to-SWIM system interface exchange.",
                        confidence=0.82,
                    )
                ],
            ),
        ],
    )


def _contribution(
    *,
    document_id: str,
    title: str,
    entities: list[dict],
    processes: list[dict],
    relations: list[dict],
) -> dict:
    return {
        "document": {
            "id": document_id,
            "path": f"Mid Term/{title}.docx",
            "title": title,
            "file_type": "docx",
            "source_archive": "nas-ea-midterm",
            "character_count": 1200,
            "parser_name": "docling_docx",
            "segment_count": 12,
            "source_file_path": f"{title}.docx",
            "source_digest": f"sha256:{document_id}",
        },
        "entities": entities,
        "events": [],
        "processes": processes,
        "relations": relations,
        "extraction": {
            "strategy": "formal",
            "schema_version": "p1.midterm.test",
            "candidate_count": len(entities) + len(processes),
            "relation_count": len(relations),
            "runtime_trace": {
                "knowledge_resolution": {
                    "rule_execution_records": [
                        {
                            "execution_id": f"rex-{document_id}-kr",
                            "rule_id": "RL-KR-VIEW-MERGE-001",
                            "policy_package_version_id": "PKGV-MIDTERM-R1",
                            "input_hash": f"sha256:{document_id}:input",
                            "output_hash": f"sha256:{document_id}:output",
                        }
                    ]
                }
            },
        },
    }


def _entity(
    item_id: str,
    name: str,
    *,
    aliases: list[str],
    evidence: str,
) -> dict:
    return {
        "id": item_id,
        "name": name,
        "category": "system",
        "aliases": aliases,
        "evidence": [{"excerpt": evidence}],
    }


def _process(item_id: str, name: str, definition: str, evidence: str) -> dict:
    return {
        "id": item_id,
        "name": name,
        "category": "operational_process",
        "definition": definition,
        "evidence": [{"excerpt": evidence}],
    }


def _relation(
    relation_id: str,
    relation_type: str,
    source_name: str,
    target_name: str,
    *,
    evidence: str,
    confidence: float,
) -> dict:
    return {
        "id": relation_id,
        "type": relation_type,
        "source_name": source_name,
        "target_name": target_name,
        "evidence": [{"excerpt": evidence}],
        "confidence": confidence,
    }
