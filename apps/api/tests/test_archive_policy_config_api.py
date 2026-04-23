from fastapi.testclient import TestClient

from app.api.routes.archives import (
    get_archive_extraction_coordinator,
    get_archive_extraction_service,
    get_archive_registry_service,
)
from app.archive_knowledge.coordination import ArchiveExtractionCoordinator
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
    assert payload["version_label"] == "13 阶段抽取蓝图 v1"
    assert payload["scope_label"] == "单文档抽取过程"
    assert payload["ai_autoadapt_enabled"] is True
    assert payload["stage_order"][0] == "asset_intake"
    assert payload["stages"]["asset_intake"]["label"] == "素材接入"
    assert payload["stages"]["quality_policy_evaluation_governance_gate"]["default_action"] == "block_return"


def test_put_archive_policy_config_persists_updates(tmp_path) -> None:
    app = create_app()
    registry_service = build_registry_service(tmp_path)
    app.dependency_overrides[get_archive_registry_service] = lambda: registry_service
    client = TestClient(app)

    original = client.get("/api/archives/20161116-nas/policy-config")
    assert original.status_code == 200
    payload = original.json()

    payload["version_label"] = "13 阶段抽取蓝图 v2"
    payload["scope_label"] = "单文档抽取过程 / 严格模式"
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
    assert updated["version_label"] == "13 阶段抽取蓝图 v2"
    assert updated["scope_label"] == "单文档抽取过程 / 严格模式"
    assert updated["ai_autoadapt_enabled"] is False
    assert updated["updated_at"] is not None
    assert updated["stages"]["asset_intake"]["objective"] == "先完成接入质量判断，再决定是否进入正式抽取链路。"
    assert updated["stages"]["asset_intake"]["default_action"] == "manual_review"
    assert updated["stages"]["asset_intake"]["rules"][-1]["key"] == "asset-extra"

    follow_up = client.get("/api/archives/20161116-nas/policy-config")
    assert follow_up.status_code == 200
    persisted = follow_up.json()
    assert persisted["version_label"] == "13 阶段抽取蓝图 v2"
    assert persisted["stages"]["asset_intake"]["default_action"] == "manual_review"
    assert persisted["stages"]["asset_intake"]["rules"][-1]["action"] == "manual_review"


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
            "version_label": "13 阶段抽取蓝图 v3",
            "scope_label": "单文档抽取过程 / 快照验证",
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
            assert policy_snapshot["version_label"] == "13 阶段抽取蓝图 v3"
            assert policy_snapshot["scope_label"] == "单文档抽取过程 / 快照验证"
            assert policy_snapshot["snapshot_id"]
            assert policy_snapshot["stages"][0]["stage_id"] == "asset_intake"
            assert policy_snapshot["stages"][0]["default_action"] == "manual_review"
            assert policy_snapshot["stages"][0]["rules"]
            assert policy_snapshot["stages"][0]["rules"][0]["threshold"]
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
