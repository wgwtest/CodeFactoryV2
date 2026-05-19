from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.design_converters.models import DesignConverterRunResult


@pytest.fixture(autouse=True)
def fake_design_converter_loader(monkeypatch):
    from app.software_design_v2 import service as service_module

    class FakeDesignConverterAdapter:
        def __init__(self, converter_id: str) -> None:
            self.converter_id = converter_id

        def run(self, request) -> DesignConverterRunResult:
            app_name = (
                request.input_package.get("structured_spec", {})
                .get("application", {})
                .get("name")
                or "未命名软件"
            )
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": self.converter_id,
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": request.session["version_label"],
                    "status": "draft",
                    "sections": [
                        {
                            "section_id": "goal",
                            "title": "1. 设计目标与范围",
                            "content": f"本设计面向{app_name}首版交付，覆盖规划任务创建、冲突识别、协同确认、处置记录和状态追溯能力。",
                            "status": "generated",
                            "source_refs": ["REQ-3.2"],
                        },
                        {
                            "section_id": "architecture",
                            "title": "2. 总体架构",
                            "content": "首版采用统一服务架构，前端以 B/S 工作台承载协同规划视图，后端以任务、冲突、确认和审计四类服务对象组织核心能力。",
                            "status": "generated",
                            "source_refs": ["REQ-3.2"],
                        },
                        {
                            "section_id": "modules",
                            "title": "3. 模块划分",
                            "content": "系统划分为规划任务管理、冲突识别与告警、协同确认、审计追溯四个模块。",
                            "status": "generated",
                            "source_refs": ["REQ-3.2", "REQ-4.1"],
                        },
                    ],
                },
                design_package={
                    "package_id": "sdb2-test-converter",
                    "status": "draft",
                    "document_projection": {},
                    "functional_tree_projection": {
                        "modules": [
                            {"module_id": "planning-task", "name": "规划任务管理", "source_refs": ["REQ-3.2"]},
                            {"module_id": "conflict-alert", "name": "冲突识别与告警", "source_refs": ["REQ-3.2", "REQ-4.1"]},
                            {"module_id": "collaboration-confirm", "name": "协同确认", "source_refs": ["REQ-3.2"]},
                            {"module_id": "audit-trace", "name": "审计追溯", "source_refs": ["REQ-4.1"]},
                        ]
                    },
                    "layered_architecture_projection": {"architecture_mode": "unified_service"},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[
                    {"source_ref": "REQ-3.2", "target_ref": "3. 模块划分", "mapping_type": "derived_from"},
                    {"source_ref": "REQ-4.1", "target_ref": "4. 状态机与接口约束", "mapping_type": "derived_from"},
                ],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 4}},
                raw_output={"raw_workflow_trace": {"mock": True}},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    def loader(manifest, **_kwargs):
        return FakeDesignConverterAdapter(manifest.converter_id)

    monkeypatch.setattr(service_module, "load_design_converter_adapter", loader, raising=False)


def _create_frozen_requirement_authoring_document(client: TestClient) -> dict:
    templates = client.get("/api/requirement-authoring/templates")
    assert templates.status_code == 200
    template_id = templates.json()[0]["template_id"]

    created = client.post(
        "/api/requirement-authoring/documents",
        json={
            "title": "空域协同规划软件需求规格说明",
            "template_id": template_id,
            "archive_ids": ["20161116-nas"],
        },
    )
    assert created.status_code == 200
    document_id = created.json()["document_id"]

    completed = client.patch(
        f"/api/requirement-authoring/documents/{document_id}/form-fields",
        json={
            "fields": {
                "application_name": "空域协同规划软件",
                "domain_scope": "国家空域管理",
                "application_scope": "空域协同规划任务链",
                "business_goals": "支撑协同规划与冲突处置闭环。",
                "main_scenarios": "规划任务创建、冲突识别、协同确认和处置复核。",
                "usage_modes": "运行协调员主用，体系架构师复核配置。",
                "in_scope": "规划任务、冲突识别、协同确认和处置记录。",
                "out_of_scope": "不包含自动生成最优处置方案。",
                "target_users": "运行协调员、体系架构师、空域规划专家",
                "main_process": "协同规划与冲突处置",
                "normal_flow": "创建规划任务、识别冲突、协同确认、形成处置记录。",
                "situational_display": "展示规划任务、冲突状态和处置进展。",
                "gis_analysis_tools": "支持基础地图定位、空间查询和冲突区域查看。",
                "deployment_analysis": "支持规划方案影响范围辅助分析。",
                "result_outputs": "输出处置记录、冲突清单和简化报告。",
                "collaboration_mode": "支持运行协调员提交、体系架构师复核。",
                "exception_flow": "异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。",
                "input_data_sources": "空域基础数据、规划任务、冲突规则和处置记录。",
                "input_data_mode": "人工录入和文件导入结合。",
                "performance_requirements": "关键告警 2 分钟内反馈。",
                "reliability_requirements": "关键状态变更需留痕。",
                "security_requirements": "按用户身份和任务范围授权。",
                "permission_model": "运行协调员可编辑，体系架构师可复核，其他用户只读。",
                "deployment_environment": "内网环境部署。",
                "accuracy_constraints": "辅助规划级精度，不承诺工程测绘精度。",
                "acceptance_scenarios": "完成规划任务创建、冲突识别、协同确认和处置记录导出。",
                "acceptance_criteria": "关键流程可追溯，超时提醒可验证。",
            }
        },
    )
    assert completed.status_code == 200

    checked = client.post(f"/api/requirement-authoring/documents/{document_id}/check")
    assert checked.status_code == 200
    assert checked.json()["status"] == "ready_to_freeze"

    frozen = client.post(f"/api/requirement-authoring/documents/{document_id}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["frozen_package"]["p3_consumable"] is True
    return frozen.json()


def test_software_design_v2_consumes_only_p2_authoring_frozen_packages() -> None:
    client = TestClient(create_app())
    frozen = _create_frozen_requirement_authoring_document(client)

    packages = client.get("/api/software-design-v2/input-packages")
    assert packages.status_code == 200
    assert [item["source_document_id"] for item in packages.json()["items"]] == [frozen["document_id"]]
    assert packages.json()["items"][0]["source_title"] == "空域协同规划软件需求规格说明"
    assert packages.json()["items"][0]["p3_consumable"] is True

    session_response = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": packages.json()["items"][0]["input_package_id"],
            "design_title": "空域协同规划软件设计说明 - 初版架构",
            "version_label": "v0.1",
            "generation_policy": {
                "architecture_preference": "统一服务优先，保留拆分点",
                "module_granularity": "3-5 个业务模块，不拆太细",
                "output_style": "按标准软设正文写，不写聊天语气",
            },
        },
    )
    assert session_response.status_code == 200
    session = session_response.json()
    assert session["status"] == "conversion_pending"
    assert session["design_title"] == "空域协同规划软件设计说明 - 初版架构"
    assert session["version_label"] == "v0.1"
    assert session["design_document"] is None
    assert session["conversion"]["status"] == "conversion_pending"
    assert [step["title"] for step in session["conversion"]["steps"]] == [
        "读取需规冻结包",
        "抽取设计对象",
        "生成软设草稿",
        "建立追溯映射",
    ]
    assert session["input_package"]["source_document_id"] == frozen["document_id"]

    old_generate = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/generate")
    assert old_generate.status_code == 404

    premature_turn = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/turns",
        json={"user_input": "先补充总体架构"},
    )
    assert premature_turn.status_code == 400
    assert "conversion" in premature_turn.json()["detail"]

    converted = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/conversion",
        json={"strategy": "component_first"},
    )
    assert converted.status_code == 200
    converted_session = converted.json()
    assert converted_session["status"] == "draft_ready"
    assert converted_session["conversion"]["status"] == "draft_ready"
    assert converted_session["conversion"]["strategy"] == "component_first"
    assert all(step["status"] == "done" for step in converted_session["conversion"]["steps"])
    assert converted_session["conversion"]["draft_preview"]["title"] == "空域协同规划软件设计说明 - 初版架构"
    assert converted_session["conversion"]["traceability_summary"]["mapped_clause_count"] >= 2
    assert converted_session["design_document"]["title"] == "空域协同规划软件设计说明 - 初版架构"
    assert converted_session["design_document"]["version_label"] == "v0.1"
    assert converted_session["design_baseline"]["architecture_mode"] == "unified_service"
    assert converted_session["design_baseline"]["function_tree"]["root"]["children"][0]["title"] == "规划任务管理"
    assert converted_session["workorder_projection"] is None
    packages_after_conversion = client.get("/api/software-design-v2/input-packages")
    related_designs = packages_after_conversion.json()["items"][0]["related_designs"]
    assert related_designs == [
        {
            "software_design_id": session["session_id"],
            "title": "空域协同规划软件设计说明 - 初版架构",
            "version_label": "v0.1",
            "status": "draft_ready",
            "created_at": session["created_at"],
            "updated_at": converted_session["updated_at"],
        }
    ]

    turned = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/turns",
        json={"user_input": "按保守方案，增加状态机说明"},
    )
    assert turned.status_code == 200
    turn_payload = turned.json()
    assert turn_payload["turn"]["normalized_intent"] == "add_state_machine"
    assert "状态机" in turn_payload["turn"]["assistant_message"]
    assert turn_payload["session"]["design_baseline"]["pending_confirmations"]

    saved = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/save")
    assert saved.status_code == 200
    assert saved.json()["status"] == "draft_saved"
    assert saved.json()["runtime_events"][-1]["event_type"] == "save"

    projected = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/projection")
    assert projected.status_code == 200
    assert projected.json()["workorder_projection"]["tree"]["title"] == "P4-WO-StageLab-Workbench"
    assert projected.json()["workorder_projection"]["tree"]["children"][1]["title"] == "B. P3 适配工具包"
    assert projected.json()["runtime_events"][-1]["event_type"] == "projection"

    checked_v2 = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/check")
    assert checked_v2.status_code == 200
    assert checked_v2.json()["check_result"]["blocking_count"] == 0
    assert checked_v2.json()["check_result"]["passed_count"] >= 3

    frozen_response = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/freeze")
    assert frozen_response.status_code == 200
    frozen_session = frozen_response.json()
    assert frozen_session["status"] == "frozen"
    assert frozen_session["frozen_package"]["package_id"] == f"sdp-{session['session_id']}"
    assert frozen_session["frozen_package"]["version_label"] == "v0.1"
    assert frozen_session["workorder_projection"]["tree"]["children"][1]["children"][0]["title"] == "WO-B1 DTO -> ViewModel Adapter"
    assert frozen_session["runtime_events"][-1]["event_type"] == "freeze"

    delete_frozen = client.delete(f"/api/software-design-v2/sessions/{session['session_id']}")
    assert delete_frozen.status_code == 400
    assert "frozen" in delete_frozen.json()["detail"]


def test_software_design_v2_lists_available_design_converters() -> None:
    client = TestClient(create_app())

    converters = client.get("/api/software-design-v2/converters")

    assert converters.status_code == 200
    items = converters.json()["items"]
    assert items[0]["converter_id"] == "requirement-to-sdd-dify-workflow"
    assert items[0]["converter_type"] == "dify_workflow"
    assert items[0]["protocol"] == "p3-design-converter-protocol@1"
    assert items[0]["observability_level"] == "limited"
    assert items[0]["capabilities"]["design_document"] is True


def test_software_design_v2_input_packages_bootstraps_default_published_requirement_when_empty() -> None:
    client = TestClient(create_app())

    packages = client.get("/api/software-design-v2/input-packages")

    assert packages.status_code == 200
    items = packages.json()["items"]
    assert len(items) == 1
    input_package = items[0]
    assert input_package["source_title"] == "空域协同规划软件需求规格说明"
    assert input_package["p3_consumable"] is True
    assert input_package["input_package_id"].startswith("art-")

    spec_items = client.get("/api/requirement-analysis/spec-items")
    assert spec_items.status_code == 200
    default_item = spec_items.json()["items"][0]
    assert default_item["status"] == "published_to_p3"
    assert default_item["published_package_id"] == input_package["input_package_id"]


def test_software_design_v2_input_packages_publishes_existing_default_draft_requirement() -> None:
    client = TestClient(create_app())

    from app.db.session import SessionLocal
    from app.requirement_spec_work_items.service import RequirementSpecWorkItemService

    with SessionLocal() as session:
        default_item = RequirementSpecWorkItemService(session)._bootstrap_default_publishable_item()
        assert default_item.status == "draft"
        assert default_item.p3_consumable is False

    packages = client.get("/api/software-design-v2/input-packages")
    assert packages.status_code == 200
    input_package = packages.json()["items"][0]
    assert input_package["source_title"] == "空域协同规划软件需求规格说明"
    assert input_package["input_package_id"].startswith("art-")

    republished_items = client.get("/api/requirement-analysis/spec-items")
    republished_default = republished_items.json()["items"][0]
    assert republished_default["status"] == "published_to_p3"
    assert republished_default["published_package_id"] == input_package["input_package_id"]


def test_software_design_v2_supports_multiple_related_designs_and_deletes_unfrozen_drafts() -> None:
    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]

    first = _create_and_convert_design_session(client, input_package_id)
    second = _create_and_convert_design_session(client, input_package_id)

    packages = client.get("/api/software-design-v2/input-packages")
    related_design_ids = [item["software_design_id"] for item in packages.json()["items"][0]["related_designs"]]
    assert related_design_ids == [second["session_id"], first["session_id"]]

    fetched = client.get(f"/api/software-design-v2/sessions/{first['session_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == first["session_id"]

    deleted = client.delete(f"/api/software-design-v2/sessions/{first['session_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_session_id"] == first["session_id"]

    packages_after_delete = client.get("/api/software-design-v2/input-packages")
    remaining_design_ids = [item["software_design_id"] for item in packages_after_delete.json()["items"][0]["related_designs"]]
    assert remaining_design_ids == [second["session_id"]]


def test_software_design_v2_conversion_runs_through_design_converter_adapter_loader(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    calls: list[dict] = []

    class FakeDesignConverterAdapter:
        def __init__(self, converter_id: str) -> None:
            self.converter_id = converter_id

        def run(self, request) -> DesignConverterRunResult:
            calls.append(
                {
                    "converter_id": self.converter_id,
                    "strategy": request.conversion_options["strategy"],
                    "input_package_id": request.input_package["input_package_id"],
                    "design_title": request.session["design_title"],
                    "template_id": request.target_design_profile["template_id"],
                    "template_name": request.target_design_profile["template_name"],
                    "minimum_total_chars": request.target_design_profile["minimum_total_chars"],
                    "required_section_count": len(request.target_design_profile["required_sections"]),
                    "core_section_minimum_chars": {
                        section["title"]: section["minimum_chars"]
                        for section in request.target_design_profile["required_sections"]
                        if section.get("section_id") in {"sdd-04", "sdd-06", "sdd-08"}
                    },
                    "required_table_ids": [table["table_id"] for table in request.quality_rules["required_tables"]],
                    "quality_minimum_total_chars": request.quality_rules["minimum_total_chars"],
                    "coverage": request.quality_rules["section_coverage"],
                }
            )
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": self.converter_id,
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": request.session["version_label"],
                    "status": "draft",
                    "sections": [
                        {
                            "section_id": "architecture",
                            "title": "4. 总体架构",
                            "content": "adapter loader sentinel",
                            "status": "generated",
                            "source_refs": ["REQ-3.2"],
                            "children": [
                                {
                                    "section_id": "architecture-context",
                                    "title": "4.1 架构上下文",
                                    "content": "前端工作台、后端转换服务和 Dify 工作流通过明确边界协作。",
                                    "status": "generated",
                                    "source_refs": ["REQ-3.2"],
                                }
                            ],
                            "blocks": [
                                {
                                    "block_id": "architecture-summary",
                                    "kind": "paragraph",
                                    "content": "adapter loader sentinel",
                                    "source_refs": ["REQ-3.2"],
                                },
                                {
                                    "block_id": "architecture-flow",
                                    "kind": "diagram",
                                    "title": "图 4-1 需规转软设转换链路",
                                    "diagram_type": "mermaid",
                                    "content": "flowchart LR\n  P2[P2 冻结需规] --> P3[P3 转换器]\n  P3 --> Dify[Dify 工作流]\n  Dify --> SDD[软设草稿]",
                                    "source_refs": ["REQ-3.2"],
                                },
                            ],
                        }
                    ],
                },
                design_package={
                    "package_id": "sdp-adapter-loader-sentinel",
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
                            "title": "P4-WO-Adapter-Sentinel",
                            "children": [],
                        },
                        "items": [],
                    },
                },
                traceability=[
                    {
                        "source_ref": "REQ-3.2",
                        "target_type": "section",
                        "target_ref": "architecture",
                        "mapping_type": "derived_from",
                        "confidence": "high",
                    }
                ],
                gap_list=[
                    {
                        "gap_id": "P3-GAP-ADAPTER-001",
                        "severity": "warning",
                        "message": "adapter loader sentinel gap",
                    }
                ],
                review_findings=[
                    {
                        "finding_id": "P3-REVIEW-ADAPTER-001",
                        "severity": "warning",
                        "target": "总体架构",
                        "message": "adapter loader sentinel finding",
                        "requires_human_decision": True,
                    }
                ],
                workorder_projection_candidate={
                    "tree": {
                        "node_id": "p4-root",
                        "title": "P4-WO-Adapter-Sentinel",
                        "children": [],
                    },
                    "items": [],
                },
                process_output={
                    "annotations": ["adapter loader was used"],
                    "quality_summary": {"blocking_count": 0, "warning_count": 1, "passed_count": 3},
                },
                raw_output={"raw_workflow_trace": {"sentinel": True}},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    def fake_loader(manifest, **_kwargs):
        return FakeDesignConverterAdapter(manifest.converter_id)

    monkeypatch.setattr(service_module, "load_design_converter_adapter", fake_loader, raising=False)

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]

    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 转换器分支",
            "version_label": "v0.1",
            "generation_policy": {
                "architecture_preference": "统一服务优先，保留拆分点",
                "module_granularity": "3-5 个业务模块，不拆太细",
                "output_style": "按标准软设正文写，不写聊天语气",
            },
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={
            "converter_id": "requirement-to-sdd-dify-workflow",
            "strategy": "component_first",
            "options": {"expected_output": "design_package_with_document"},
        },
    )

    assert converted.status_code == 200
    converted_session = converted.json()
    assert calls == [
        {
            "converter_id": "requirement-to-sdd-dify-workflow",
            "strategy": "component_first",
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 转换器分支",
            "template_id": "81435-sdd-quasi-template-v1",
            "template_name": "81435-软件设计说明准模板-v1",
            "minimum_total_chars": 12000,
            "required_section_count": 15,
            "core_section_minimum_chars": {
                "总体架构": 1200,
                "后端软件设计": 1500,
                "API 设计": 1500,
            },
            "required_table_ids": [
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
            ],
            "quality_minimum_total_chars": 12000,
            "coverage": {"level_1_required": 1.0, "level_2_required": 0.9},
        }
    ]
    assert converted_session["status"] == "draft_ready"
    assert converted_session["conversion"]["converter"]["converter_id"] == "requirement-to-sdd-dify-workflow"
    assert converted_session["conversion"]["converter"]["converter_type"] == "dify_workflow"
    assert converted_session["conversion"]["traceability_summary"]["mapped_clause_count"] == 1
    assert converted_session["design_document"]["sections"][0]["content"] == "adapter loader sentinel"
    assert converted_session["design_document"]["sections"][0]["children"][0]["title"] == "4.1 架构上下文"
    assert converted_session["design_document"]["sections"][0]["blocks"][1]["kind"] == "diagram"
    assert converted_session["design_baseline"]["baseline_id"] == "sdp-adapter-loader-sentinel"
    assert converted_session["design_baseline"]["pending_confirmations"] == ["adapter loader sentinel gap"]
    assert converted_session["workorder_projection"]["tree"]["title"] == "P4-WO-Adapter-Sentinel"
    assert converted_session["check_result"]["warning_count"] == 1
    assert converted_session["runtime_events"][-1]["event_type"] == "conversion"


def test_software_design_v2_normalizes_real_dify_projection_shape_for_frontend(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    class FakeDesignConverterAdapter:
        def run(self, request) -> DesignConverterRunResult:
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": "requirement-to-sdd-dify-workflow",
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": "draft",
                    "status": "draft",
                    "sections": [
                        {
                            "section_id": "purpose",
                            "title": "1. 文档目的与设计口径",
                            "content": "真实 Dify 形态回归。",
                            "status": "generated",
                            "source_refs": ["REQ-AC"],
                        }
                    ],
                },
                design_package={
                    "package_id": "SDP-REAL-DIFY-SHAPE",
                    "status": "draft",
                    "document_projection": {},
                    "functional_tree_projection": {
                        "modules": [
                            {
                                "id": "module-portal",
                                "title": "资源消费门户模块",
                                "description": "承接消费者资源发现、资源篮和申请提交。",
                                "source_refs": ["REQ-FR"],
                            }
                        ]
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {
                        "candidate_batches": [
                            {
                                "batch_id": "P4-CANDIDATE-P3-DESIGN",
                                "title": "P3 设计包派生工单候选",
                                "modules": ["资源消费门户模块"],
                                "status": "candidate",
                            }
                        ]
                    },
                },
                traceability=[
                    {
                        "source_ref": "REQ-FR",
                        "target_type": "module",
                        "target_ref": "module-portal",
                        "target_title": "资源消费门户模块",
                    }
                ],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={
                    "candidate_batches": [
                        {
                            "batch_id": "P4-CANDIDATE-P3-DESIGN",
                            "title": "P3 设计包派生工单候选",
                            "modules": ["资源消费门户模块"],
                            "status": "candidate",
                        }
                    ]
                },
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
                raw_output={"raw_workflow_trace": {"real_dify_shape": True}},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    monkeypatch.setattr(
        service_module,
        "load_design_converter_adapter",
        lambda *_args, **_kwargs: FakeDesignConverterAdapter(),
        raising=False,
    )

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "真实 Dify 形态软设",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 200
    session = converted.json()
    assert session["design_baseline"]["modules"] == [
        {
            "module_id": "module-portal",
            "name": "资源消费门户模块",
            "source_refs": ["REQ-FR"],
            "description": "承接消费者资源发现、资源篮和申请提交。",
        }
    ]
    assert session["workorder_projection"]["tree"]["node_id"] == "P4-CANDIDATE-P3-DESIGN"
    assert session["workorder_projection"]["tree"]["title"] == "P3 设计包派生工单候选"
    assert session["workorder_projection"]["items"] == [
        {
            "item_id": "module-portal",
            "title": "资源消费门户模块",
            "module_id": "module-portal",
            "description": "由转换器候选批次 P4-CANDIDATE-P3-DESIGN 派生。",
            "readiness": "candidate",
        }
    ]


def test_software_design_v2_preserves_converter_function_tree_projection(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    class FakeDesignConverterAdapter:
        def run(self, request) -> DesignConverterRunResult:
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": "requirement-to-sdd-dify-workflow",
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": request.session["version_label"],
                    "status": "draft",
                    "sections": [
                        {
                            "section_id": "purpose",
                            "title": "1. 文档目的与设计口径",
                            "content": "只作为软设章节，不进入功能树。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        }
                    ],
                },
                design_package={
                    "package_id": "SDP-FUNCTION-TREE",
                    "status": "draft",
                    "document_projection": {},
                    "functional_tree_projection": {
                        "tree_id": "ft-real",
                        "title": "资源服务系统功能树",
                        "root": {
                            "node_id": "ft-root",
                            "title": "资源服务系统",
                            "node_type": "root",
                            "children": [
                                {
                                    "node_id": "module-resource",
                                    "title": "资源目录模块",
                                    "node_type": "module",
                                    "module_id": "module-resource",
                                    "source_refs": ["REQ-FR-001"],
                                    "design_refs": ["sdd-06"],
                                    "children": [
                                        {
                                            "node_id": "capability-search",
                                            "title": "资源检索能力",
                                            "node_type": "capability",
                                            "source_refs": ["REQ-FR-001"],
                                            "design_refs": ["sdd-06-01"],
                                            "children": [],
                                        }
                                    ],
                                }
                            ],
                        },
                    },
                    "layered_architecture_projection": {"architecture_mode": "unified_service"},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[
                    {
                        "source_ref": "REQ-FR-001",
                        "target_type": "function_tree_node",
                        "target_ref": "capability-search",
                        "target_title": "资源检索能力",
                    }
                ],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
                raw_output={"raw_workflow_trace": {"function_tree": True}},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    monkeypatch.setattr(
        service_module,
        "load_design_converter_adapter",
        lambda *_args, **_kwargs: FakeDesignConverterAdapter(),
        raising=False,
    )

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "功能树保留测试软设",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 200
    function_tree = converted.json()["design_baseline"]["function_tree"]
    assert function_tree["tree_id"] == "ft-real"
    assert function_tree["root"]["children"][0]["title"] == "资源目录模块"
    assert function_tree["root"]["children"][0]["children"][0]["title"] == "资源检索能力"
    assert function_tree["root"]["children"][0]["children"][0]["design_refs"] == ["sdd-06-01"]


def test_software_design_v2_warns_on_mechanical_placeholder_function_tree(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    class FakeDesignConverterAdapter:
        def run(self, request) -> DesignConverterRunResult:
            modules = ["规划任务管理模块", "空间分析模块", "协同确认模块"]
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": "requirement-to-sdd-dify-workflow",
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": request.session["version_label"],
                    "status": "draft",
                    "sections": [
                        {
                            "section_id": "modules",
                            "title": "6. 模块划分",
                            "content": "转换器返回机械占位功能树。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        }
                    ],
                },
                design_package={
                    "package_id": "SDP-MECHANICAL-FUNCTION-TREE",
                    "status": "draft",
                    "document_projection": {},
                    "functional_tree_projection": {
                        "tree_id": "ft-mechanical",
                        "title": "空域协同规划软件功能树",
                        "root": {
                            "node_id": "ft-root",
                            "title": "空域协同规划软件",
                            "node_type": "root",
                            "children": [
                                {
                                    "node_id": f"module-{index}",
                                    "title": module_title,
                                    "node_type": "module",
                                    "module_id": f"module-{index}",
                                    "source_refs": ["REQ-FR-001"],
                                    "children": [
                                        {
                                            "node_id": f"capability-{index}",
                                            "title": f"{module_title.removesuffix('模块')}能力",
                                            "node_type": "capability",
                                            "source_refs": ["REQ-FR-001"],
                                            "description": f"承接{module_title}下的核心业务能力。",
                                            "children": [
                                                {
                                                    "node_id": f"function-{index}",
                                                    "title": f"处理{module_title.removesuffix('模块')}业务",
                                                    "node_type": "function",
                                                    "source_refs": ["REQ-FR-001"],
                                                    "description": "从需求对象推导的待细化功能项。",
                                                    "children": [],
                                                }
                                            ],
                                        }
                                    ],
                                }
                                for index, module_title in enumerate(modules, start=1)
                            ],
                        },
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[
                    {
                        "source_ref": "REQ-FR-001",
                        "target_type": "module",
                        "target_ref": "module-1",
                        "target_title": "规划任务管理模块",
                    }
                ],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
                raw_output={"raw_workflow_trace": {"mechanical_function_tree": True}},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    monkeypatch.setattr(
        service_module,
        "load_design_converter_adapter",
        lambda *_args, **_kwargs: FakeDesignConverterAdapter(),
        raising=False,
    )

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "机械占位功能树检测软设",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 200
    session = converted.json()
    quality = session["design_baseline"]["function_tree_quality"]
    assert quality["status"] == "warning"
    assert quality["metrics"]["module_count"] == 3
    assert quality["metrics"]["single_chain_module_count"] == 3
    assert quality["metrics"]["mechanical_chain_module_count"] == 3
    assert quality["findings"][0]["finding_id"] == "P3-FT-QUALITY-MECHANICAL-SHALLOW"
    assert session["design_baseline"]["review_findings"][0]["target"] == "功能树"
    assert "机械占位结构" in session["design_baseline"]["pending_confirmations"][0]
    assert session["check_result"]["warning_count"] == 1
    assert session["check_result"]["items"][-1]["scope"] == "function_tree"


def test_software_design_v2_adds_function_tree_quality_warning_to_converter_warnings(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    class FakeDesignConverterAdapter:
        def run(self, request) -> DesignConverterRunResult:
            return DesignConverterRunResult(
                protocol_version=request.protocol_version,
                converter={
                    "converter_id": "requirement-to-sdd-dify-workflow",
                    "converter_type": "dify_workflow",
                    "observability_level": "limited",
                },
                design_document={
                    "title": request.session["design_title"],
                    "version_label": request.session["version_label"],
                    "status": "draft",
                    "sections": [],
                },
                design_package={
                    "package_id": "SDP-MECHANICAL-WITH-WARNING",
                    "status": "draft",
                    "document_projection": {},
                    "functional_tree_projection": {
                        "root": {
                            "node_id": "ft-root",
                            "title": "功能树",
                            "node_type": "root",
                            "children": [
                                {
                                    "node_id": f"module-{index}",
                                    "title": module_title,
                                    "node_type": "module",
                                    "children": [
                                        {
                                            "node_id": f"capability-{index}",
                                            "title": f"{module_title}能力",
                                            "node_type": "capability",
                                            "children": [
                                                {
                                                    "node_id": f"function-{index}",
                                                    "title": f"处理{module_title}业务",
                                                    "node_type": "function",
                                                    "children": [],
                                                }
                                            ],
                                        }
                                    ],
                                }
                                for index, module_title in enumerate(["任务", "空间"], start=1)
                            ],
                        },
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[],
                gap_list=[
                    {
                        "gap_id": "P3-GAP-EXISTING",
                        "severity": "warning",
                        "message": "已有转换器警告。",
                    }
                ],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 1, "passed_count": 3}},
                raw_output={},
                confidence="medium",
                annotations=[],
                risks=[],
            )

    monkeypatch.setattr(
        service_module,
        "load_design_converter_adapter",
        lambda *_args, **_kwargs: FakeDesignConverterAdapter(),
        raising=False,
    )

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "功能树警告计数测试软设",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 200
    session = converted.json()
    assert session["check_result"]["warning_count"] == 2
    assert [item["scope"] for item in session["check_result"]["items"] if item.get("scope") == "function_tree"] == ["function_tree"]


def test_software_design_v2_records_converter_failure_detail(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    class FailingDesignConverterAdapter:
        def run(self, request):
            raise ValueError("remote dify workflow failed (run-bad): output result_json missing")

    monkeypatch.setattr(
        service_module,
        "load_design_converter_adapter",
        lambda *_args, **_kwargs: FailingDesignConverterAdapter(),
        raising=False,
    )

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 失败观测",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 400
    assert "result_json missing" in converted.json()["detail"]
    failed_session = client.get(f"/api/software-design-v2/sessions/{created.json()['session_id']}").json()
    assert failed_session["status"] == "conversion_failed"
    assert failed_session["conversion"]["status"] == "conversion_failed"
    assert failed_session["conversion"]["process_output"]["error"]["message"] == converted.json()["detail"]
    assert failed_session["conversion"]["steps"][0]["status"] == "failed"
    assert failed_session["runtime_events"][-1]["event_type"] == "conversion_failed"
    assert "result_json missing" in failed_session["runtime_events"][-1]["message"]


def test_software_design_v2_rejects_unsupported_design_converter() -> None:
    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 转换器分支",
            "version_label": "v0.1",
            "generation_policy": {},
        },
    )
    assert created.status_code == 200

    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"converter_id": "missing-converter", "strategy": "standard_sdd_draft"},
    )

    assert converted.status_code == 400
    assert converted.json()["detail"] == "unsupported P3 design converter"


def _create_and_convert_design_session(client: TestClient, input_package_id: str) -> dict:
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 测试分支",
            "version_label": "v0.1",
            "generation_policy": {
                "architecture_preference": "统一服务优先，保留拆分点",
                "module_granularity": "3-5 个业务模块，不拆太细",
                "output_style": "按标准软设正文写，不写聊天语气",
            },
        },
    )
    assert created.status_code == 200
    converted = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/conversion",
        json={"strategy": "standard_sdd_draft"},
    )
    assert converted.status_code == 200
    return converted.json()
