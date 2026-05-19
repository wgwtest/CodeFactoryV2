from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

from app.design_converters.adapters.base import load_design_converter_adapter
from app.design_converters.models import (
    DesignConverterManifest,
    DesignConverterRunRequest,
    DesignConverterRunResult,
)
from app.design_converters.plugin_discovery import DesignConverterPluginDiscovery
from app.design_converters.plugin_registry import DesignConverterPluginRegistry
from app.software_design_v2.sdd_template_profile import (
    build_sdd_81435_quality_rules,
    build_sdd_81435_template_profile,
)


def _write_converter_plugin(
    root: Path,
    stage: str,
    converter: str,
    *,
    converter_id: str | None = None,
    converter_type: str = "dify_workflow",
    adapter_module: str = "adapter",
    adapter_class: str = "ExampleConverterAdapter",
    write_adapter: bool = True,
) -> Path:
    converter_dir = root / stage / converter
    converter_dir.mkdir(parents=True)
    (converter_dir / "manifest.json").write_text(
        json.dumps(
            {
                "converter_id": converter_id or converter,
                "name": converter,
                "converter_type": converter_type,
                "document_type": "software_design_description",
                "protocol": "p3-design-converter-protocol@1",
                "status": "active",
                "priority": 10,
                "capabilities": {
                    "design_document": True,
                    "design_package": True,
                    "traceability": True,
                    "gap_list": True,
                    "review_findings": True,
                    "p4_workorder_projection": True,
                },
                "requires": {"dify_api": True},
                "adapter_module": adapter_module,
                "adapter_class": adapter_class,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if write_adapter:
        (converter_dir / "adapter.py").write_text(
            "class ExampleConverterAdapter:\n"
            "    def __init__(self, *, manifest):\n"
            "        self.manifest = manifest\n",
            encoding="utf-8",
        )
    return converter_dir


def _converter_request() -> DesignConverterRunRequest:
    return DesignConverterRunRequest(
        protocol_version="p3-design-converter-protocol@1",
        session={
            "session_id": "p3dl-test",
            "design_title": "SX-DataStore 软件设计说明",
            "version_label": "v0.1",
            "generation_policy": {"output_style": "按标准软设正文写"},
        },
        input_package={
            "input_package_id": "p2pkg-test",
            "source_title": "SX-DataStore 需求规格说明",
            "standard_document": {"title": "SX-DataStore 需求规格说明", "content": "资源发现与申请。"},
            "structured_spec": {
                "application": {"name": "SX-DataStore"},
                "roles": ["消费者", "生产者", "管理者"],
                "requirements": [{"id": "REQ-FR-001", "title": "资源发现与申请"}],
            },
            "annotations": [],
            "knowledge_binding": {},
            "frozen_at": "2026-05-18T00:00:00+00:00",
        },
        target_design_profile=build_sdd_81435_template_profile(
            design_title="SX-DataStore 软件设计说明",
            version_label="v0.1",
        ),
        conversion_options={"strategy": "component_first"},
        quality_rules=build_sdd_81435_quality_rules(),
    )


def _result_payload() -> dict:
    return {
        "protocol_version": "p3-design-converter-protocol@1",
        "converter": {
            "converter_id": "requirement-to-sdd-dify-workflow",
            "converter_type": "dify_workflow",
            "observability_level": "limited",
        },
        "design_document": {
            "title": "SX-DataStore 软件设计说明",
            "version_label": "draft",
            "status": "draft",
            "sections": [
                {
                    "section_id": "architecture",
                    "title": "4. 总体架构",
                    "content": "系统围绕资源目录、申请审批和交付治理组织。",
                    "status": "generated",
                    "source_refs": ["REQ-FR-001"],
                    "children": [
                        {
                            "section_id": "architecture-context",
                            "title": "4.1 架构上下文",
                            "content": "资源消费、审批和交付治理通过统一应用服务编排。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        }
                    ],
                    "blocks": [
                        {
                            "block_id": "architecture-overview",
                            "kind": "paragraph",
                            "content": "系统围绕资源目录、申请审批和交付治理组织。",
                            "source_refs": ["REQ-FR-001"],
                        },
                        {
                            "block_id": "architecture-diagram",
                            "kind": "diagram",
                            "title": "图 4-1 总体架构图",
                            "diagram_type": "mermaid",
                            "content": "flowchart LR\n  Portal[资源门户] --> Service[申请审批服务]\n  Service --> Delivery[交付治理]",
                            "source_refs": ["REQ-FR-001"],
                        },
                    ],
                }
            ],
        },
        "design_package": {
            "package_id": "sdp-dify-test",
            "status": "draft",
            "document_projection": {},
            "functional_tree_projection": {},
            "layered_architecture_projection": {},
            "technical_implementation_projection": {},
            "api_projection": {},
            "workflow_projection": {},
            "quality_gate_projection": {},
            "p4_workorder_projection": {
                "tree": {
                    "node_id": "p4-root",
                    "title": "P4-WO-SX-DataStore",
                    "children": [],
                },
                "items": [],
            },
        },
        "traceability": [
            {
                "source_ref": "REQ-FR-001",
                "target_type": "module",
                "target_ref": "resource-request-service",
                "mapping_type": "derived_from",
                "confidence": "high",
            }
        ],
        "gap_list": [
            {
                "gap_id": "P3-GAP-001",
                "severity": "warning",
                "message": "统一身份认证接入方式需人工确认。",
            }
        ],
        "review_findings": [
            {
                "finding_id": "P3-REVIEW-001",
                "severity": "warning",
                "target": "API 设计",
                "message": "字段级接口规范仍需补充。",
                "requires_human_decision": True,
            }
        ],
        "workorder_projection_candidate": {
            "tree": {
                "node_id": "p4-root",
                "title": "P4-WO-SX-DataStore",
                "children": [],
            },
            "items": [],
        },
        "process_output": {"quality_summary": {"blocking_count": 0, "warning_count": 1, "passed_count": 3}},
        "raw_output": {"raw_workflow_trace": {"workflow_id": "p3-requirement-to-sdd-workflow"}},
        "confidence": "medium",
        "annotations": [],
        "risks": [],
    }


def test_design_converter_manifest_protocol_and_api_shape() -> None:
    manifest = DesignConverterManifest(
        converter_id="requirement-to-sdd-dify-workflow",
        name="P3 Requirement to SDD Dify Workflow",
        converter_type="dify_workflow",
        document_type="software_design_description",
        protocol="p3-design-converter-protocol@1",
        status="active",
        priority=10,
        capabilities={
            "design_document": True,
            "design_package": True,
            "traceability": True,
            "gap_list": True,
            "review_findings": True,
            "p4_workorder_projection": True,
        },
        requires={"dify_api": True},
        adapter_module="adapter",
        adapter_class="RequirementToSddDifyWorkflowAdapter",
        aliases=("p3-dify",),
    )

    assert manifest.converter_id == "requirement-to-sdd-dify-workflow"
    assert manifest.observability_level == "limited"
    assert manifest.to_api()["converter_id"] == "requirement-to-sdd-dify-workflow"
    assert manifest.to_api()["protocol"] == "p3-design-converter-protocol@1"


def test_design_converter_discovery_scans_stage_converter_level(tmp_path: Path) -> None:
    _write_converter_plugin(tmp_path, "p3", "requirement-to-sdd-dify-workflow")
    _write_converter_plugin(tmp_path, "p3", "nested/too-deep-converter")

    discovered = DesignConverterPluginDiscovery(root=tmp_path).discover()

    assert [item.manifest.converter_id for item in discovered.plugins] == ["requirement-to-sdd-dify-workflow"]
    assert discovered.errors == []
    assert discovered.plugins[0].plugin_dir == tmp_path / "p3" / "requirement-to-sdd-dify-workflow"
    assert discovered.plugins[0].adapter_path == tmp_path / "p3" / "requirement-to-sdd-dify-workflow" / "adapter.py"


def test_repository_design_converter_plugin_is_discoverable() -> None:
    discovered = DesignConverterPluginDiscovery().discover()
    converter_ids = {item.manifest.converter_id for item in discovered.plugins}

    assert "requirement-to-sdd-dify-workflow" in converter_ids
    assert discovered.errors == []

    registry = DesignConverterPluginRegistry()
    default_converter = registry.default_converter()
    assert default_converter.converter_id == "requirement-to-sdd-dify-workflow"
    assert default_converter.converter_type == "dify_workflow"


def test_design_converter_adapter_loader_imports_plugin_adapter() -> None:
    registry = DesignConverterPluginRegistry()
    manifest = registry.require("requirement-to-sdd-dify-workflow")

    adapter = load_design_converter_adapter(manifest)

    assert adapter.manifest.converter_id == "requirement-to-sdd-dify-workflow"


def test_dify_design_converter_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    monkeypatch.delenv("CODEFACTORY_P3_DIFY_API_KEY", raising=False)
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))

    with pytest.raises(ValueError, match="DIFY_API_KEY"):
        adapter.run(_converter_request())


def test_dify_design_converter_normalizes_remote_result(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        assert url == "http://dify.local/v1/workflows/run"
        assert headers["Authorization"] == "Bearer test-dify-key"
        assert json["inputs"]["requirement_document_title"] == "SX-DataStore 需求规格说明"
        assert json["inputs"]["expected_output"] == "design_package_with_document"
        target_profile = json_module.loads(json["inputs"]["target_design_profile_json"])
        quality_rules = json_module.loads(json["inputs"]["quality_rules_json"])
        assert target_profile["template_id"] == "81435-sdd-quasi-template-v1"
        assert target_profile["minimum_total_chars"] == 12000
        assert len(target_profile["required_sections"]) == 15
        assert target_profile["required_sections"][5]["title"] == "后端软件设计"
        assert target_profile["required_sections"][5]["minimum_chars"] == 1500
        assert target_profile["document_structure"]["section_children_field"] == "children"
        assert target_profile["document_structure"]["block_field"] == "blocks"
        assert target_profile["diagram_requirements"]["minimum_diagram_count"] == 4
        assert quality_rules["minimum_total_chars"] == 12000
        assert quality_rules["section_coverage"] == {"level_1_required": 1.0, "level_2_required": 0.9}
        assert quality_rules["document_structure"]["require_structured_blocks"] is True
        assert quality_rules["diagram_requirements"]["required_diagrams"][0]["diagram_id"] == "D1"
        assert [table["table_id"] for table in quality_rules["required_tables"]] == [
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
            "T6",
            "T7",
            "T8",
            "T9",
            "T10",
            "T11",
            "T12",
            "T13",
            "T14",
            "T15",
        ]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-p3-dify-001",
                "data": {
                    "id": "run-p3-dify-001",
                    "status": "succeeded",
                    "outputs": {"result_json": json_module.dumps(_result_payload(), ensure_ascii=False)},
                },
            },
        )

    json_module = json
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))
    adapter_module = sys.modules["_codefactory_design_converter_requirement_to_sdd_dify_workflow.adapter"]
    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    result = adapter.run(_converter_request())

    assert isinstance(result, DesignConverterRunResult)
    assert result.converter["converter_id"] == "requirement-to-sdd-dify-workflow"
    assert result.design_document["title"] == "SX-DataStore 软件设计说明"
    assert result.design_document["sections"][0]["children"][0]["title"] == "4.1 架构上下文"
    assert result.design_document["sections"][0]["blocks"][1]["kind"] == "diagram"
    assert result.design_package["package_id"] == "sdp-dify-test"
    assert result.traceability[0]["source_ref"] == "REQ-FR-001"
    assert result.gap_list[0]["severity"] == "warning"
    assert result.review_findings[0]["requires_human_decision"] is True
    assert result.raw_output["raw_workflow_trace"]["workflow_run_id"] == "run-p3-dify-001"


def test_dify_design_converter_prefers_codefactory_p3_environment_and_published_workflow_path(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        assert url == "http://localhost/v1/workflows/f599fabf-5e84-427a-acd9-0b57f782ea94/run"
        assert headers["Authorization"] == "Bearer p3-specific-key"
        assert timeout == 60.0
        assert json["user"] == "codefactory-p3-session"
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-published-p3",
                "data": {
                    "id": "run-published-p3",
                    "status": "succeeded",
                    "outputs": {"result_json": json_module.dumps(_result_payload(), ensure_ascii=False)},
                },
            },
        )

    json_module = json
    monkeypatch.setenv("DIFY_BASE_URL", "http://legacy-dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "legacy-key")
    monkeypatch.setenv("CODEFACTORY_P3_DIFY_BASE_URL", "http://localhost/v1")
    monkeypatch.setenv("CODEFACTORY_P3_DIFY_API_KEY", "p3-specific-key")
    monkeypatch.setenv("CODEFACTORY_P3_DIFY_WORKFLOW_ID", "f599fabf-5e84-427a-acd9-0b57f782ea94")
    monkeypatch.setenv("CODEFACTORY_P3_DIFY_TIMEOUT_SECONDS", "60")
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))
    adapter_module = sys.modules["_codefactory_design_converter_requirement_to_sdd_dify_workflow.adapter"]
    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    result = adapter.run(_converter_request())

    assert result.raw_output["raw_workflow_trace"]["workflow_id"] == "f599fabf-5e84-427a-acd9-0b57f782ea94"
    assert result.raw_output["raw_workflow_trace"]["workflow_run_id"] == "run-published-p3"


def test_dify_design_converter_rejects_missing_result_json(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"workflow_run_id": "run-bad", "data": {"id": "run-bad", "status": "succeeded", "outputs": {}}},
        )

    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))
    adapter_module = sys.modules["_codefactory_design_converter_requirement_to_sdd_dify_workflow.adapter"]
    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    with pytest.raises(ValueError, match="result_json"):
        adapter.run(_converter_request())


def test_dify_design_converter_rejects_flat_text_only_design_document(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        payload = _result_payload()
        for section in payload["design_document"]["sections"]:
            section.pop("children", None)
            section.pop("blocks", None)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-flat-document",
                "data": {
                    "id": "run-flat-document",
                    "status": "succeeded",
                    "outputs": {"result_json": json_module.dumps(payload, ensure_ascii=False)},
                },
            },
        )

    json_module = json
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))
    adapter_module = sys.modules["_codefactory_design_converter_requirement_to_sdd_dify_workflow.adapter"]
    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    with pytest.raises(ValueError, match="structured blocks"):
        adapter.run(_converter_request())


def test_dify_design_converter_normalizes_string_review_findings(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout, trust_env):
        payload = _result_payload()
        payload["review_findings"] = [
            "核心对象模型仅列出对象名称，需人工补齐字段级定义。",
            "API 设计缺少请求响应结构、错误码和鉴权策略。",
        ]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-review-strings",
                "data": {
                    "id": "run-review-strings",
                    "status": "succeeded",
                    "outputs": {"result_json": json_module.dumps(payload, ensure_ascii=False)},
                },
            },
        )

    json_module = json
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.local")
    monkeypatch.setenv("DIFY_API_KEY", "test-dify-key")
    registry = DesignConverterPluginRegistry()
    adapter = load_design_converter_adapter(registry.require("requirement-to-sdd-dify-workflow"))
    adapter_module = sys.modules["_codefactory_design_converter_requirement_to_sdd_dify_workflow.adapter"]
    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    result = adapter.run(_converter_request())

    assert result.review_findings == [
        {
            "finding_id": "P3-REVIEW-001",
            "severity": "warning",
            "target": "software_design_description",
            "message": "核心对象模型仅列出对象名称，需人工补齐字段级定义。",
            "requires_human_decision": True,
        },
        {
            "finding_id": "P3-REVIEW-002",
            "severity": "warning",
            "target": "software_design_description",
            "message": "API 设计缺少请求响应结构、错误码和鉴权策略。",
            "requires_human_decision": True,
        },
    ]
