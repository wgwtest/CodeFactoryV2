from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_quality_graph_report_consumes_runtime_snapshot_and_policy_version() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/p1/archives/archive-demo/quality-graph/report",
        params={
            "runtime_snapshot_id": "RUN-QA-001",
            "policy_package_version_id": "PKGV-QA-20260510",
        },
    )

    assert response.status_code == 200
    body = response.json()
    report = body["data"]
    assert body["contract_version"] == "p1.quality_graph_report.r0"
    assert report["archive_id"] == "archive-demo"
    assert report["run_id"] == "RUN-QA-001"
    assert report["gate_decision"]["decision"] == "block"
    assert report["gate_decision"]["output_action"] == "return_for_rebuild"
    assert report["gate_decision"]["score"] < 70
    assert report["quality_finding_report"]["summary"]["publish_blocked"] is True
    finding_codes = {finding["code"] for finding in report["quality_finding_report"]["findings"]}
    assert "item_type_invalid" in finding_codes
    assert "publication_blocked_by_object_quality" in finding_codes

    metric_ids = {metric["metric_id"] for metric in report["gate_decision"]["metric_results"]}
    assert metric_ids >= {
        "knowledge.concept_precision",
        "knowledge.evidence_coverage",
        "graph.relation_confidence_avg",
        "graph.explainability_coverage",
    }

    policy_ref = next(item for item in report["data_lineage"] if item["artifact_type"] == "PolicyRuntimeSnapshot")
    assert policy_ref["metadata"]["policy_package_version_id"] == "PKGV-QA-20260510"

    evidence_metric = next(
        metric for metric in report["knowledge_quality"]["metrics"] if metric["metric_id"] == "knowledge.evidence_coverage"
    )
    assert evidence_metric["actual"] == 0.91
    assert "anchor-A-102" in evidence_metric["evidence_anchor_ids"]


def test_quality_graph_report_requires_explicit_snapshot_and_policy_inputs() -> None:
    client = TestClient(create_app())

    response = client.get("/api/p1/archives/archive-demo/quality-graph/report")

    assert response.status_code == 422
