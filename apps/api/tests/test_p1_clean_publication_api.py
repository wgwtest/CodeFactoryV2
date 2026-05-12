from fastapi.testclient import TestClient

from app.main import create_app


def test_p1_clean_publication_candidate_consumes_runtime_snapshot_and_quality_decision() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/p1/archives/kb-demo/publication-candidates/latest",
        params={"runtime_snapshot_id": "RS-P1-R0-001", "policy_package_version_id": "PKGV-20260508-R0"},
    )

    assert response.status_code == 200
    body = response.json()
    candidate = body["data"]

    assert body["contract_version"] == "p1.publication_candidate.r1"
    assert body["source_kind"] == "live"
    assert candidate["archive_id"] == "kb-demo"
    assert candidate["publication_candidate_snapshot_id"] == "PCS-kb-demo-RS-P1-R0-001"
    assert candidate["publication_snapshot_id"] is None
    assert candidate["runtime_snapshot_id"] == "RS-P1-R0-001"
    assert candidate["policy_package_version_id"] == "PKGV-20260508-R0"
    assert candidate["resolution_snapshot_id"] == "RESOLVE-P1-R0-001"
    assert candidate["status"] == "blocked_by_quality"
    assert candidate["candidate_summary"]["publication_snapshot_id"] is None
    assert candidate["candidate_summary"]["generated_from_runtime_snapshot_id"] == "RS-P1-R0-001"
    assert candidate["candidate_summary"]["status_label"] == "质量门禁未放行候选"
    assert candidate["candidate_objects"][0]["object_id"] == "CK-contract-amount"
    assert candidate["candidate_objects"][0]["canonical_name"] == "合同总金额"
    assert candidate["candidate_objects"][0]["quality_status"] == "blocked"
    assert candidate["candidate_relations"] == []
    assert candidate["quality_decision_summary"]["decision"] == "block"
    assert candidate["quality_decision"]["decision"] == "block"
    assert candidate["quality_decision_summary"]["output_action"] == "return_for_rebuild"
    assert candidate["quality_finding_report"]["summary"]["publish_blocked"] is True
    finding_codes = {finding["code"] for finding in candidate["quality_finding_report"]["findings"]}
    assert "publication_blocked_by_object_quality" in finding_codes
    assert candidate["governance_projection"]["governance_confirmation_status"] == "not_ready"
    assert candidate["governance_projection"]["formal_entry_label"] == "尚未正式入库"
    assert all(
        path.startswith("/api/p1/candidates/") or path == "/api/p1/archives/{archive_id}/publication-candidates/latest"
        for path in candidate["api_exposure_scope"]["readonly_candidate_api_paths"]
    )
    assert candidate["api_exposure_scope"]["readonly_formal_api_paths"] == []
    assert candidate["api_exposure_scope"]["exposure_mode"] == "blocked"
    assert "不代表正式入库结果" in body["warnings"][0]
