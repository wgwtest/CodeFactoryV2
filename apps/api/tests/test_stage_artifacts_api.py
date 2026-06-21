from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _stage_artifact_payload(revision: int) -> dict:
    return {
        "session_id": "p3dl-stage-artifact-test",
        "design_title": "阶段产物持久化测试软设",
        "revision": revision,
        "design_document": {
            "title": "阶段产物持久化测试软设",
            "sections": [{"section_id": "overview", "title": "1. 概述", "content": "测试正文"}],
        },
    }


def test_stage_artifacts_upsert_query_snapshot_freeze_and_reject_frozen_overwrite() -> None:
    client = TestClient(create_app())

    list_url = (
        "/api/stage-artifacts"
        "?producer_stage=P3&artifact_type=software_design_session"
        "&scope_type=p3_design_input&scope_id=art-p2-input-1"
    )
    assert client.get(list_url).json() == {"items": []}

    created = client.put(
        "/api/stage-artifacts/current",
        json={
            "artifact_id": "p3dl-stage-artifact-test",
            "owner_user_id": "default",
            "producer_stage": "P3",
            "artifact_type": "software_design_session",
            "artifact_version": "v0.1",
            "schema_version": "p3_software_design_session.v1",
            "scope_type": "p3_design_input",
            "scope_id": "art-p2-input-1",
            "lifecycle_status": "working",
            "payload": _stage_artifact_payload(1),
            "source_artifact_ids": ["art-p2-input-1"],
            "source_trace": {"input_package_id": "art-p2-input-1"},
        },
    )
    assert created.status_code == 200
    created_artifact = created.json()
    assert created_artifact["artifact_id"] == "p3dl-stage-artifact-test"
    assert created_artifact["lifecycle_status"] == "working"
    assert created_artifact["payload"]["revision"] == 1
    assert len(created_artifact["payload_hash"]) == 64

    updated = client.put(
        "/api/stage-artifacts/current",
        json={
            "artifact_id": "p3dl-stage-artifact-test",
            "owner_user_id": "default",
            "producer_stage": "P3",
            "artifact_type": "software_design_session",
            "artifact_version": "v0.1",
            "schema_version": "p3_software_design_session.v1",
            "scope_type": "p3_design_input",
            "scope_id": "art-p2-input-1",
            "lifecycle_status": "draft_saved",
            "payload": _stage_artifact_payload(2),
            "source_artifact_ids": ["art-p2-input-1"],
            "source_trace": {"input_package_id": "art-p2-input-1"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["artifact_id"] == created_artifact["artifact_id"]
    assert updated.json()["payload"]["revision"] == 2
    assert updated.json()["lifecycle_status"] == "draft_saved"

    listed = client.get(list_url).json()["items"]
    assert [item["artifact_id"] for item in listed] == ["p3dl-stage-artifact-test"]
    assert listed[0]["payload"]["revision"] == 2

    snapshot = client.post(
        "/api/stage-artifacts/p3dl-stage-artifact-test/snapshots",
        json={
            "artifact_type": "software_design_package",
            "artifact_version": "v0.1-freeze-candidate",
            "schema_version": "p3_software_design_package.v1",
            "lifecycle_status": "snapshot",
        },
    )
    assert snapshot.status_code == 200
    snapshot_artifact = snapshot.json()
    assert snapshot_artifact["artifact_id"] != "p3dl-stage-artifact-test"
    assert snapshot_artifact["artifact_type"] == "software_design_package"
    assert snapshot_artifact["parent_artifact_id"] == "p3dl-stage-artifact-test"
    assert snapshot_artifact["payload"]["revision"] == 2
    assert snapshot_artifact["lifecycle_status"] == "snapshot"

    frozen = client.post(f"/api/stage-artifacts/{snapshot_artifact['artifact_id']}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["lifecycle_status"] == "frozen"
    assert frozen.json()["frozen_at"]

    rejected = client.put(
        "/api/stage-artifacts/current",
        json={
            "artifact_id": snapshot_artifact["artifact_id"],
            "owner_user_id": "default",
            "producer_stage": "P3",
            "artifact_type": "software_design_package",
            "artifact_version": "v0.1-freeze-candidate",
            "schema_version": "p3_software_design_package.v1",
            "scope_type": "p3_design_input",
            "scope_id": "art-p2-input-1",
            "lifecycle_status": "working",
            "payload": _stage_artifact_payload(3),
            "source_artifact_ids": ["art-p2-input-1"],
            "source_trace": {"input_package_id": "art-p2-input-1"},
        },
    )
    assert rejected.status_code == 409
    assert "frozen" in rejected.json()["detail"]
