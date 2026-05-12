from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.archives import get_archive_registry_service
from app.archive_knowledge.p1_modules.policy_rules import (
    build_architecture_midterm_policy_package_version,
    build_rule_execution_record_field_contracts,
)
from app.archive_knowledge.policy_config import build_default_archive_policy_config, build_policy_run_snapshot
from app.archive_knowledge.registry import ArchiveRegistryService
from app.archive_knowledge.runtime_policy_contract import build_policy_contract_rule_execution_records
from app.main import create_app


def _registry_service(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir(exist_ok=True)
    return ArchiveRegistryService(
        tmp_path,
        default_archive_id="midterm-architecture",
        default_archive_name="Mid Term 体系结构知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )


def test_midterm_policy_config_api_returns_architecture_default_contract(tmp_path) -> None:
    app = create_app()
    app.dependency_overrides[get_archive_registry_service] = lambda: _registry_service(tmp_path)
    client = TestClient(app)

    response = client.get("/api/archives/midterm-architecture/policy-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_package_id"] == "architecture_midterm_default"
    assert payload["policy_package_name"] == "Mid Term 体系结构默认策略包"
    assert payload["policy_package_version_id"] == "midterm-architecture:architecture_midterm_default:policy:v1"
    assert payload["policy_contract_status"] == "valid"
    assert "AV-1" in payload["scope_label"]
    assert "SV-4" in payload["scope_label"]

    rules = [
        rule
        for stage in payload["stages"].values()
        for rule in stage["rules"]
    ]
    rule_ids = {rule["rule_id"] for rule in rules}
    assert "architecture_midterm_default.section-table-paragraph" in rule_ids
    assert "architecture_midterm_default.object-operational-node" in rule_ids
    assert "architecture_midterm_default.object-information-exchange" in rule_ids
    assert "architecture_midterm_default.relation-performs" in rule_ids
    assert "architecture_midterm_default.relation-depends-on" in rule_ids
    assert "architecture_midterm_default.merge-semantic-similarity" in rule_ids
    assert "architecture_midterm_default.gate-low-confidence-ratio" in rule_ids

    for rule in rules:
        assert rule["rule_version"] == "r1.0"
        assert rule["rule_hash"].startswith("sha256:")
        assert rule["effect_kind"]
        assert rule["input_schema"]
        assert rule["output_schema"]
        assert rule["action_mapping"]["effect_kind"] == rule["effect_kind"]
        assert rule["contract_status"] == "valid"
        assert {"rule_id", "rule_version", "rule_hash", "input_hash", "output_hash"}.issubset(rule["trace_fields"])
        assert {field["field_name"] for field in rule["input_schema"]} >= {
            "archive_id",
            "document_set_id",
            "document_type_summary",
            "source_view_type",
            "input_hash",
        }
        assert {field["field_name"] for field in rule["output_schema"]} >= {
            "affected_object_ids",
            "output_hash",
        }


def test_midterm_policy_snapshot_generates_consumable_rule_execution_records() -> None:
    config = build_default_archive_policy_config("midterm-architecture")
    snapshot = build_policy_run_snapshot(
        "midterm-architecture",
        config,
        captured_at="2026-05-11T00:00:00+00:00",
    )
    contribution = {
        "document": {
            "id": "doc-ov5",
            "title": "OV-5 Operational Activity Model",
            "file_type": "docx",
            "character_count": 4200,
            "segment_count": 9,
            "parser_name": "docling_docx",
            "source_digest": "sha256:ov5",
        },
        "entities": [
            {
                "id": "node-alpha",
                "name": "Alpha Operational Node",
                "aliases": ["Alpha Node"],
                "document_ids": ["doc-ov5"],
                "evidence": [{"document_id": "doc-ov5", "excerpt": "Alpha Operational Node"}],
            }
        ],
        "events": [{"id": "activity-plan", "name": "Plan Mission", "evidence": [{"document_id": "doc-ov5"}]}],
        "processes": [],
        "relations": [{"id": "rel-performs-1", "type": "performs", "confidence": 0.9}],
        "extraction": {"candidate_count": 2, "relation_count": 1},
    }

    records = build_policy_contract_rule_execution_records(
        archive_id="midterm-architecture",
        document_id="doc-ov5",
        stage_id="concept_candidate_review",
        stage_status="completed",
        contribution=contribution,
        policy_snapshot=snapshot,
    )

    assert records
    assert records[0].source == "policy_snapshot"
    assert records[0].rule_hash.startswith("sha256:")
    assert records[0].policy_snapshot_id == snapshot["policy_snapshot_id"]
    assert records[0].policy_package_id == "architecture_midterm_default"
    assert records[0].policy_version == "midterm-architecture:architecture_midterm_default:policy:v1"
    assert records[0].input_hash.startswith("sha256:")
    assert records[0].output_hash.startswith("sha256:")
    assert records[0].affected_object_ids
    assert records[0].metrics["contract_status"] == "valid"

    package_version = build_architecture_midterm_policy_package_version("midterm-architecture", config)
    assert package_version.policy_package_version_id == "midterm-architecture:architecture_midterm_default:policy:v1"
    assert package_version.rule_contracts
    assert all(rule.contract_status == "valid" for rule in package_version.rule_contracts)
    assert "RuleExecutionRecord" in package_version.compatible_output_contracts

    record_field_names = {field.field_name for field in build_rule_execution_record_field_contracts()}
    assert {
        "execution_id",
        "rule_id",
        "rule_hash",
        "policy_snapshot_id",
        "policy_package_version_id",
        "input_hash",
        "output_hash",
        "affected_object_ids",
        "decision",
        "metrics",
    }.issubset(record_field_names)
