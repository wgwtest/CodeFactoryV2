from fastapi.testclient import TestClient

from app.api.routes.archives import (
    get_archive_extraction_coordinator,
    get_archive_extraction_service,
    get_archive_registry_service,
)
from app.archive_knowledge.coordination import ArchiveExtractionCoordinator
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.archive_knowledge.registry import ArchiveRegistryService
from app.main import create_app


def build_registry_service(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir(exist_ok=True)
    return ArchiveRegistryService(
        tmp_path,
        default_archive_id="20161116-nas",
        default_archive_name="默认 NAS 知识库",
        default_source_dir=source_dir,
        default_extract_root=tmp_path / "legacy-extract",
        extract_root_parent=tmp_path / ".extract",
    )


def test_get_archive_policy_config_returns_default_contract(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)

    response = client.get("/api/archives/20161116-nas/policy-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["archive_id"] == "20161116-nas"
    assert payload["version_label"] == "architecture_midterm_default v1"
    assert payload["scope_label"] == "Mid Term 体系结构文档：AV-1、OV-1、OV-2、OV-5、OV-7、SV-1、SV-2、SV-4"
    assert payload["ai_autoadapt_enabled"] is True
    assert payload["stage_order"][0] == "asset_intake"
    assert payload["stages"]["asset_intake"]["label"] == "Mid Term 文档接入"
    assert payload["stages"]["quality_policy_evaluation_governance_gate"]["default_action"] == "block_return"
    assert payload["policy_package_id"] == "architecture_midterm_default"
    assert payload["policy_package_version_id"] == "20161116-nas:architecture_midterm_default:policy:v1"
    assert payload["policy_package_version_hash"].startswith("sha256:")
    assert payload["policy_contract_version"] == "p1.policy_contract.v1"
    assert payload["policy_contract_status"] == "valid"
    assert payload["policy_package_versions"][0]["version_id"] == "20161116-nas:architecture_midterm_default:policy:v1"

    first_rule = payload["stages"]["asset_intake"]["rules"][0]
    assert first_rule["rule_id"] == "architecture_midterm_default.doc-type-summary"
    assert first_rule["rule_version"]
    assert first_rule["effect_kind"]
    assert first_rule["action_mapping"]["effect_kind"] == first_rule["effect_kind"]
    assert first_rule["action_mapping"]["on_match"] == first_rule["action"]
    assert first_rule["parameters"]["conditions"]
    assert first_rule["rule_hash"].startswith("sha256:")
    assert first_rule["contract_status"] == "valid"
    assert {field["field_name"] for field in first_rule["input_schema"]} >= {"input_hash"}
    assert {field["field_name"] for field in first_rule["output_schema"]} >= {
        "affected_object_ids",
        "output_hash",
    }
    assert {"rule_id", "rule_version", "rule_hash", "input_hash", "output_hash"}.issubset(first_rule["trace_fields"])


def test_put_archive_policy_config_persists_updates(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)

    original = client.get("/api/archives/20161116-nas/policy-config")
    assert original.status_code == 200
    payload = original.json()

    payload["version_label"] = "architecture_midterm_default v2"
    payload["scope_label"] = "Mid Term 体系结构文档 / 严格模式"
    payload["ai_autoadapt_enabled"] = False
    payload["stages"]["asset_intake"]["objective"] = "先完成接入质量判断，再决定是否进入正式抽取链路。"
    payload["stages"]["asset_intake"]["default_action"] = "manual_review"
    payload["stages"]["asset_intake"]["rules"].append(
        {
            "key": "asset-extra",
            "name": "来源可追溯",
            "meaning": "来源缺失时先转人工复核。",
            "threshold": "source_label present",
            "action": "manual_review",
        }
    )

    response = client.put(
        "/api/archives/20161116-nas/policy-config",
        json={
            "version_label": payload["version_label"],
            "scope_label": payload["scope_label"],
            "ai_autoadapt_enabled": payload["ai_autoadapt_enabled"],
            "stage_order": payload["stage_order"],
            "stages": payload["stages"],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["version_label"] == "architecture_midterm_default v2"
    assert updated["scope_label"] == "Mid Term 体系结构文档 / 严格模式"
    assert updated["ai_autoadapt_enabled"] is False
    assert updated["updated_at"] is not None
    assert updated["stages"]["asset_intake"]["objective"] == "先完成接入质量判断，再决定是否进入正式抽取链路。"
    assert updated["stages"]["asset_intake"]["default_action"] == "manual_review"
    assert updated["stages"]["asset_intake"]["rules"][-1]["key"] == "asset-extra"
    assert updated["stages"]["asset_intake"]["rules"][-1]["contract_status"] == "valid"
    assert updated["policy_package_version_id"] == "20161116-nas:architecture_midterm_default:policy:v2"
    assert updated["previous_policy_package_version_id"] == "20161116-nas:architecture_midterm_default:policy:v1"

    follow_up = client.get("/api/archives/20161116-nas/policy-config")
    assert follow_up.status_code == 200
    persisted = follow_up.json()
    assert persisted["version_label"] == "architecture_midterm_default v2"
    assert persisted["stages"]["asset_intake"]["default_action"] == "manual_review"
    assert persisted["stages"]["asset_intake"]["rules"][-1]["action"] == "manual_review"
    assert {entry["version_id"] for entry in persisted["policy_package_versions"]} == {
        "20161116-nas:architecture_midterm_default:policy:v1",
        "20161116-nas:architecture_midterm_default:policy:v2",
    }


def test_put_archive_policy_config_recomputes_rule_and_package_hash(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)

    original = client.get("/api/archives/20161116-nas/policy-config")
    assert original.status_code == 200
    payload = original.json()
    original_package_hash = payload["policy_package_version_hash"]
    target_rule = payload["stages"]["asset_intake"]["rules"][0]
    original_rule_hash = target_rule["rule_hash"]

    target_rule["input_schema"].append(
        {
            "field_name": "contract_revision_reason",
            "source_artifact": "policy_editor",
            "field_type": "string",
            "required": False,
            "include_in_input_hash": True,
            "validation": "optional",
            "example": "tighten source traceability",
            "business_meaning": "why the contract changed",
            "missing_action": "warn_continue",
        }
    )

    response = client.put(
        "/api/archives/20161116-nas/policy-config",
        json={
            "policy_package_id": payload["policy_package_id"],
            "policy_package_name": payload["policy_package_name"],
            "policy_package_version_id": payload["policy_package_version_id"],
            "policy_package_version_status": payload["policy_package_version_status"],
            "policy_package_version_hash": original_package_hash,
            "version_label": payload["version_label"],
            "scope_label": payload["scope_label"],
            "ai_autoadapt_enabled": payload["ai_autoadapt_enabled"],
            "stage_order": payload["stage_order"],
            "stages": payload["stages"],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    updated_rule = updated["stages"]["asset_intake"]["rules"][0]
    assert updated_rule["rule_hash"] != original_rule_hash
    assert updated["policy_package_version_hash"] != original_package_hash
    assert updated["policy_package_version_id"] == "20161116-nas:architecture_midterm_default:policy:v2"
    assert updated["previous_policy_package_version_id"] == "20161116-nas:architecture_midterm_default:policy:v1"
    assert updated_rule["rule_version"] == "r1.1"
    assert updated_rule["contract_status"] == "valid"


def test_put_archive_policy_config_reports_missing_contract_fields(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)

    original = client.get("/api/archives/20161116-nas/policy-config")
    assert original.status_code == 200
    payload = original.json()
    target_rule = payload["stages"]["asset_intake"]["rules"][0]
    target_rule["input_schema"] = [
        field for field in target_rule["input_schema"] if field["field_name"] != "input_hash"
    ]
    target_rule["output_schema"] = [
        field for field in target_rule["output_schema"] if field["field_name"] != "affected_object_ids"
    ]
    target_rule["trace_fields"] = []

    response = client.put(
        "/api/archives/20161116-nas/policy-config",
        json={
            "policy_package_id": payload["policy_package_id"],
            "policy_package_name": payload["policy_package_name"],
            "policy_package_version_id": payload["policy_package_version_id"],
            "policy_package_version_status": payload["policy_package_version_status"],
            "version_label": payload["version_label"],
            "scope_label": payload["scope_label"],
            "ai_autoadapt_enabled": payload["ai_autoadapt_enabled"],
            "stage_order": payload["stage_order"],
            "stages": payload["stages"],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    updated_rule = updated["stages"]["asset_intake"]["rules"][0]
    assert updated["policy_contract_status"] == "invalid"
    assert updated_rule["contract_status"] == "invalid"
    assert "missing input_schema.input_hash" in updated_rule["contract_errors"]
    assert "missing output_schema.affected_object_ids" in updated_rule["contract_errors"]
    assert "missing trace_fields.rule_id" in updated_rule["contract_errors"]
    assert "missing trace_fields.rule_hash" in updated_rule["contract_errors"]
    assert updated["policy_contract_errors"][0]["rule_id"] == updated_rule["rule_id"]


def test_put_archive_policy_config_creates_candidate_only_incremental_rebuild_task(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)
    DocumentArtifactRepository(tmp_path).replace_all(
        "20161116-nas",
        [
            {
                "document": {
                    "id": "doc-1",
                    "path": "docs/doc-1.docx",
                    "title": "Document One",
                    "file_type": "docx",
                    "source_archive": "kb",
                    "character_count": 1000,
                    "parser_name": "docling_docx",
                    "segment_count": 4,
                    "source_file_path": str(tmp_path / "doc-1.docx"),
                    "source_digest": "sha256:doc-1",
                },
                "entities": [
                    {
                        "id": "entity-alpha",
                        "name": "Alpha",
                        "category": "system_or_service",
                        "aliases": [],
                        "document_ids": ["doc-1"],
                        "evidence": [{"document_id": "doc-1", "excerpt": "Alpha"}],
                    }
                ],
                "events": [],
                "processes": [],
                "relations": [
                    {
                        "type": "depends_on",
                        "source_name": "Alpha",
                        "target_name": "Beta",
                    }
                ],
                "extraction": {
                    "strategy": "formal",
                    "candidate_count": 1,
                    "relation_count": 1,
                },
            }
        ],
    )

    original = client.get("/api/archives/20161116-nas/policy-config")
    assert original.status_code == 200
    payload = original.json()
    target_rule = payload["stages"]["concept_candidate_review"]["rules"][0]
    target_rule["threshold"] = "confidence >= 0.91"

    response = client.put(
        "/api/archives/20161116-nas/policy-config",
        json={
            "policy_package_id": payload["policy_package_id"],
            "policy_package_name": payload["policy_package_name"],
            "policy_package_version_id": payload["policy_package_version_id"],
            "policy_package_version_status": payload["policy_package_version_status"],
            "version_label": payload["version_label"],
            "scope_label": payload["scope_label"],
            "ai_autoadapt_enabled": payload["ai_autoadapt_enabled"],
            "stage_order": payload["stage_order"],
            "stages": payload["stages"],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    impact_set = updated["impact_set"]
    assert impact_set["changed_rule_ids"] == [target_rule["rule_id"]]
    assert impact_set["minimum_rebuild_stage_id"] == "concept_candidate_review"
    assert impact_set["affected_document_ids"] == ["doc-1"]
    assert "concept_candidate_review" in impact_set["affected_stage_ids"]
    assert "indexes_snapshots_apis" in impact_set["affected_stage_ids"]
    assert "entity-alpha" in impact_set["affected_candidate_ids"]
    assert impact_set["affected_relation_ids"]

    task = updated["incremental_rebuild_task"]
    assert task["start_stage_id"] == "concept_candidate_review"
    assert task["affected_document_ids"] == ["doc-1"]
    assert task["writes_official_knowledge"] is False
    assert task["output_policy"] == "candidate_or_pending_confirmation_only"
    assert (tmp_path / "20161116-nas-incremental-rebuild-tasks" / f"{task['task_id']}.json").exists()
    assert (tmp_path / "20161116-nas-knowledge.json").exists() is False

    tasks_response = client.get("/api/archives/20161116-nas/incremental-rebuild-tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert tasks[0]["task_id"] == task["task_id"]
    assert tasks[0]["impact_set"]["impact_id"] == impact_set["impact_id"]

    task_response = client.get(f"/api/archives/20161116-nas/incremental-rebuild-tasks/{task['task_id']}")
    assert task_response.status_code == 200
    assert task_response.json()["writes_official_knowledge"] is False


def test_extract_archive_freezes_policy_snapshot_for_running_build(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    archive = registry_service.create_archive(
        archive_id="kb-policy",
        name="策略快照测试库",
        source_dir=tmp_path / "source",
    )
    assert archive["archive_id"] == "kb-policy"

    current_config = registry_service.get_policy_config("kb-policy")
    registry_service.update_policy_config(
        "kb-policy",
        {
            "version_label": "architecture_midterm_default v3",
            "scope_label": "Mid Term 体系结构文档 / 快照验证",
            "ai_autoadapt_enabled": True,
            "stage_order": current_config["stage_order"],
            "stages": {
                **current_config["stages"],
                "asset_intake": {
                    **current_config["stages"]["asset_intake"],
                    "default_action": "manual_review",
                },
            },
        },
    )

    class StubExtractionService(ArchiveExtractionService):
        def build_archive(self, archive_id: str, *, source_dir, extract_root, archive_name, policy_snapshot=None):
            assert archive_id == "kb-policy"
            assert archive_name == "策略快照测试库"
            assert policy_snapshot is not None
            assert policy_snapshot["version_label"] == "architecture_midterm_default v3"
            assert policy_snapshot["scope_label"] == "Mid Term 体系结构文档 / 快照验证"
            assert policy_snapshot["snapshot_id"]
            assert policy_snapshot["policy_package_version_id"] == "kb-policy:architecture_midterm_default:policy:v2"
            assert policy_snapshot["previous_policy_package_version_id"] == "kb-policy:architecture_midterm_default:policy:v1"
            assert policy_snapshot["policy_package_version_hash"].startswith("sha256:")
            assert policy_snapshot["stages"][0]["stage_id"] == "asset_intake"
            assert policy_snapshot["stages"][0]["default_action"] == "manual_review"
            assert policy_snapshot["stages"][0]["rules"]
            assert policy_snapshot["stages"][0]["rules"][0]["threshold"]
            assert policy_snapshot["stages"][0]["rules"][0]["input_schema"]
            assert policy_snapshot["stages"][0]["rules"][0]["output_schema"]
            return {
                "archive_id": archive_id,
                "source_dir": str(source_dir),
                "extract_root": str(extract_root),
                "json_path": str(tmp_path / "kb-policy-knowledge.json"),
                "curated_path": str(tmp_path / "kb-policy-knowledge-curated.json"),
                "markdown_path": str(tmp_path / "kb-policy-knowledge.md"),
                "parsed_documents_path": str(tmp_path / "kb-policy-parsed-documents.json"),
                "extraction_report_path": str(tmp_path / "kb-policy-extraction-report.json"),
                "summary": {
                    "document_count": 0,
                    "entity_count": 0,
                    "event_count": 0,
                    "process_count": 0,
                },
            }

    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    app.dependency_overrides[get_archive_extraction_service] = lambda: StubExtractionService(tmp_path)
    app.dependency_overrides[get_archive_extraction_coordinator] = lambda: ArchiveExtractionCoordinator()
    client = TestClient(app)

    response = client.post("/api/archives/kb-policy/extract")

    assert response.status_code == 200
    assert response.json()["archive_id"] == "kb-policy"
