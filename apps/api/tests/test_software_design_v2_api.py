import json

from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import create_app
from app.design_converters.models import DesignConverterRunResult


@pytest.fixture(autouse=True)
def fake_design_converter_loader(monkeypatch):
    from app.software_design_v2 import service as service_module

    for env_name in (
        "CODEFACTORY_P3_SCOPED_DIFY_BASE_URL",
        "CODEFACTORY_P3_SCOPED_DIFY_API_KEY",
        "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID",
        "CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS",
        "CODEFACTORY_P3_SCOPED_DIFY_RESPONSE_MODE",
    ):
        monkeypatch.delenv(env_name, raising=False)

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


def _complete_module_design(module_id: str, name: str) -> dict:
    module_label = name.removesuffix("模块")
    service_name = f"{module_id.title().replace('-', '')}Service"
    data_name = f"{module_id.title().replace('-', '')}Record"
    return {
        "module_id": module_id,
        "name": name,
        "responsibility": f"负责{module_label}的业务对象管理、状态留痕和规则校验。",
        "source_refs": ["REQ-FR-001"],
        "owned_objects": [module_label, f"{module_label}状态"],
        "capabilities": [
            {
                "name": f"{module_label}登记与校验",
                "functions": [f"创建{module_label}", f"校验{module_label}范围"],
                "interfaces": [f"POST /{module_id}"],
                "states": ["draft", "submitted", "checked"],
            }
        ],
        "frontend_interactions": [f"{name}表单", f"{name}校验提示"],
        "backend_services": [service_name],
        "data_objects": [data_name],
        "interfaces": [f"POST /{module_id}"],
        "state_transitions": ["draft -> submitted -> checked"],
        "quality_constraints": ["关键状态变化必须审计留痕"],
        "traceability": ["REQ-FR-001"],
    }


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

    scoped_turn = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/turns",
        json={
            "turn_type": "scoped_design_edit",
            "user_input": "这一段写得太散，拆成两段，并补充接口边界。",
            "interaction_mode": "propose_patch",
            "scope_anchor": {
                "anchor_type": "design_block",
                "section_id": "goal",
                "block_id": "goal-body",
                "design_revision_id": "v0.1",
                "selection_snapshot": {
                    "title": "1. 设计目标与范围",
                    "excerpt": "覆盖规划任务创建、冲突识别、协同确认、处置记录和状态追溯能力。",
                },
            },
            "expected_output": ["document_patch", "traceability_update", "quality_note"],
        },
    )
    assert scoped_turn.status_code == 200
    scoped_payload = scoped_turn.json()
    assert scoped_payload["turn"]["turn_type"] == "scoped_design_edit"
    assert scoped_payload["turn"]["scope_anchor"]["block_id"] == "goal-body"
    assert scoped_payload["turn"]["context_receipt"]["session_summary_id"].startswith("ctxsum-")
    assert scoped_payload["turn"]["provider_call_audit"]["provider"] == "local_scoped_patch"
    assert scoped_payload["turn"]["patch_proposal"]["base_revision_id"] == "v0.1"
    assert scoped_payload["turn"]["patch_proposal"]["target_anchor"]["section_id"] == "goal"
    assert scoped_payload["turn"]["patch_proposal"]["operations"][0]["op"] == "split_block"
    assert scoped_payload["turn"]["patch_proposal"]["operations"][1]["op"] == "update_trace_refs"
    assert scoped_payload["turn"]["assistant_message"].startswith("已生成局部补丁提案")
    assert scoped_payload["session"]["turns"][-1]["turn_id"] == scoped_payload["turn"]["turn_id"]
    assert scoped_payload["session"]["context_summaries"]["global"]["summary"]
    assert scoped_payload["session"]["context_summaries"]["scoped"]["design_block:goal:goal-body"]["summary"]

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


def test_software_design_v2_scoped_turn_uses_scoped_dify_workflow(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    captured_calls: list[dict] = []

    def fake_post(url, *, headers, json, timeout, trust_env):
        captured_calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
                "trust_env": trust_env,
            }
        )
        inputs = json["inputs"]
        scope_anchor = json_module.loads(inputs["scope_anchor_json"])
        assert inputs["session_id"].startswith("p3dl-")
        assert inputs["design_title"] == "空域协同规划软件设计说明 - 局部修正"
        assert inputs["version_label"] == "v0.1"
        assert inputs["user_input"] == "这一段写得太散，拆成职责边界和接口约束两段。"
        assert scope_anchor["block_id"] == "goal-body"
        assert "design_document" in inputs["design_context_json"]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "workflow_run_id": "run-scoped-p3-001",
                "data": {
                    "id": "run-scoped-p3-001",
                    "status": "succeeded",
                    "outputs": {
                        "result_json": json_module.dumps(
                            {
                                "normalized_intent": "scoped_design_edit",
                                "assistant_message": "已生成局部补丁提案：建议拆分职责边界和接口约束。",
                                "patch_proposal": {
                                    "proposal_id": "patch-remote-001",
                                    "base_revision_id": "v0.1",
                                    "target_anchor": {
                                        "anchor_type": "design_block",
                                        "section_id": "goal",
                                        "block_id": "goal-body",
                                    },
                                    "operations": [
                                        {
                                            "op": "split_block",
                                            "target_block_id": "goal-body",
                                            "new_blocks": [
                                                {"title": "职责边界", "content": "围绕规划任务管理能力重写职责边界。"},
                                                {"title": "接口约束", "content": "补充输入输出、状态约束和追溯要求。"},
                                            ],
                                        }
                                    ],
                                    "quality_notes": ["应用后需复核追溯链。"],
                                    "status": "proposed",
                                },
                                "context_receipt": {
                                    "included_context": ["input_package_summary", "design_document_anchor"],
                                },
                                "provider_call_audit": {
                                    "provider": "dify_scoped_patch",
                                },
                            },
                            ensure_ascii=False,
                        )
                    },
                },
            },
        )

    json_module = json
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_BASE_URL", "http://localhost/v1")
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_API_KEY", "scoped-api-key")
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID", "f2413e20-7cfc-4188-ae7f-7c23eaa353ff")
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS", "180")
    monkeypatch.setattr(service_module.httpx, "post", fake_post, raising=False)

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    created = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": input_package_id,
            "design_title": "空域协同规划软件设计说明 - 局部修正",
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

    scoped_turn = client.post(
        f"/api/software-design-v2/sessions/{created.json()['session_id']}/turns",
        json={
            "turn_type": "scoped_design_edit",
            "user_input": "这一段写得太散，拆成职责边界和接口约束两段。",
            "interaction_mode": "propose_patch",
            "scope_anchor": {
                "anchor_type": "design_block",
                "section_id": "goal",
                "block_id": "goal-body",
                "design_revision_id": "v0.1",
                "selection_snapshot": {
                    "title": "1. 设计目标与范围",
                    "excerpt": "覆盖规划任务创建、冲突识别、协同确认、处置记录和状态追溯能力。",
                },
            },
            "expected_output": ["document_patch", "traceability_update", "quality_note"],
        },
    )

    assert scoped_turn.status_code == 200
    payload = scoped_turn.json()
    assert captured_calls[0]["url"] == "http://localhost/v1/workflows/f2413e20-7cfc-4188-ae7f-7c23eaa353ff/run"
    assert captured_calls[0]["headers"]["Authorization"] == "Bearer scoped-api-key"
    assert captured_calls[0]["timeout"] == 180.0
    assert captured_calls[0]["trust_env"] is False
    assert payload["turn"]["turn_type"] == "scoped_design_edit"
    assert payload["turn"]["normalized_intent"] == "scoped_design_edit"
    assert payload["turn"]["assistant_message"] == "已生成局部补丁提案：建议拆分职责边界和接口约束。"
    assert payload["turn"]["patch_proposal"]["proposal_id"] == "patch-remote-001"
    assert payload["turn"]["patch_proposal"]["operations"][0]["op"] == "split_block"
    assert payload["turn"]["context_receipt"]["context_receipt_id"].startswith("ctx-")
    assert payload["turn"]["provider_call_audit"]["provider"] == "dify_scoped_patch"
    assert payload["turn"]["provider_call_audit"]["workflow_id"] == "f2413e20-7cfc-4188-ae7f-7c23eaa353ff"
    assert payload["turn"]["provider_call_audit"]["run_id"] == "run-scoped-p3-001"
    assert payload["session"]["turns"][-1]["turn_id"] == payload["turn"]["turn_id"]
    assert payload["session"]["status"] == "patch_ready"


def test_software_design_v2_scoped_turn_rejects_missing_dify_result_json(monkeypatch) -> None:
    from app.software_design_v2 import service as service_module

    def fake_post(url, *, headers, json, timeout, trust_env):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"workflow_run_id": "run-scoped-bad", "data": {"id": "run-scoped-bad", "status": "succeeded", "outputs": {}}},
        )

    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_BASE_URL", "http://localhost/v1")
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_API_KEY", "scoped-api-key")
    monkeypatch.setenv("CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID", "f2413e20-7cfc-4188-ae7f-7c23eaa353ff")
    monkeypatch.setattr(service_module.httpx, "post", fake_post, raising=False)

    client = TestClient(create_app())
    _create_frozen_requirement_authoring_document(client)
    input_package_id = client.get("/api/software-design-v2/input-packages").json()["items"][0]["input_package_id"]
    session = _create_and_convert_design_session(client, input_package_id)

    scoped_turn = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/turns",
        json={
            "turn_type": "scoped_design_edit",
            "user_input": "补充接口约束。",
            "interaction_mode": "propose_patch",
            "scope_anchor": {
                "anchor_type": "design_block",
                "section_id": "goal",
                "block_id": "goal-body",
                "design_revision_id": "v0.1",
            },
        },
    )

    assert scoped_turn.status_code == 400
    assert "result_json" in scoped_turn.json()["detail"]
    failed_session = client.get(f"/api/software-design-v2/sessions/{session['session_id']}").json()
    assert failed_session["status"] == "draft_ready"
    assert failed_session["turns"] == []


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
                    "module_designs": [
                        _complete_module_design("module-1", "规划任务管理模块"),
                        _complete_module_design("module-2", "空间分析模块"),
                        _complete_module_design("module-3", "协同确认模块"),
                    ],
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
                    "module_designs": [
                        _complete_module_design("module-1", "任务模块"),
                        _complete_module_design("module-2", "空间模块"),
                    ],
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


def test_software_design_v2_warns_when_modules_are_not_explained_as_vertical_slices(monkeypatch) -> None:
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
                            "section_id": "frontend",
                            "title": "7. 前端软件设计",
                            "content": "前端采用 B/S 架构，提供任务管理和空间分析页面。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        },
                        {
                            "section_id": "backend",
                            "title": "8. 后端软件设计",
                            "content": "后端采用统一服务，提供任务、空间和协同服务。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        },
                    ],
                },
                design_package={
                    "package_id": "SDP-MODULE-SHALLOW",
                    "status": "draft",
                    "document_projection": {},
                    "module_designs": [
                        {
                            "module_id": "planning-task",
                            "name": "规划任务管理模块",
                            "responsibility": "负责规划任务管理。",
                            "source_refs": ["REQ-FR-001"],
                        },
                        {
                            "module_id": "space-analysis",
                            "name": "空间分析模块",
                            "responsibility": "负责空间分析。",
                            "source_refs": ["REQ-FR-002"],
                        },
                    ],
                    "functional_tree_projection": {
                        "modules": [
                            {"module_id": "planning-task", "name": "规划任务管理模块", "source_refs": ["REQ-FR-001"]},
                            {"module_id": "space-analysis", "name": "空间分析模块", "source_refs": ["REQ-FR-002"]},
                        ]
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
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
            "design_title": "模块纵切片质量检测软设",
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
    quality = session["design_baseline"]["module_design_quality"]
    assert quality["status"] == "warning"
    assert quality["metrics"]["module_design_count"] == 2
    assert quality["metrics"]["underexplained_module_count"] == 2
    assert quality["metrics"]["frontend_backend_section_count"] == 2
    assert session["design_baseline"]["module_designs"][0]["module_id"] == "planning-task"
    assert session["design_baseline"]["review_findings"][0]["finding_id"] == "P3-MODULE-DESIGN-UNDEREXPLAINED"
    assert "模块纵切片设计不足" in session["design_baseline"]["pending_confirmations"][0]
    assert session["check_result"]["warning_count"] == 2
    assert [
        item["scope"]
        for item in session["check_result"]["items"]
        if item.get("scope") in {"module_design", "design_document"}
    ] == ["module_design", "design_document"]


def test_software_design_v2_accepts_complete_module_vertical_slices(monkeypatch) -> None:
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
                            "section_id": "module-planning",
                            "title": "6.1 规划任务管理模块",
                            "content": "围绕规划任务对象说明职责、能力、页面、服务、数据、接口、状态和追溯。",
                            "status": "generated",
                            "source_refs": ["REQ-FR-001"],
                        }
                    ],
                },
                design_package={
                    "package_id": "SDP-MODULE-COMPLETE",
                    "status": "draft",
                    "document_projection": {},
                    "module_designs": [
                        {
                            "module_id": "planning-task",
                            "name": "规划任务管理模块",
                            "responsibility": "负责规划任务登记、校验、提交和状态留痕。",
                            "source_refs": ["REQ-FR-001"],
                            "owned_objects": ["规划任务", "任务附件", "任务状态"],
                            "capabilities": [
                                {
                                    "name": "任务登记与校验",
                                    "functions": ["创建规划任务", "校验规划时段", "校验任务范围"],
                                    "interfaces": ["POST /planning-tasks"],
                                    "states": ["draft", "submitted", "checked"],
                                }
                            ],
                            "frontend_interactions": ["任务创建表单", "任务校验结果提示"],
                            "backend_services": ["PlanningTaskService"],
                            "data_objects": ["PlanningTask", "PlanningTaskAttachment"],
                            "state_transitions": ["draft -> submitted -> checked"],
                            "quality_constraints": ["任务状态变化必须审计留痕"],
                            "traceability": ["REQ-FR-001"],
                        }
                    ],
                    "functional_tree_projection": {
                        "modules": [
                            {"module_id": "planning-task", "name": "规划任务管理模块", "source_refs": ["REQ-FR-001"]}
                        ]
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
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
            "design_title": "完整模块纵切片软设",
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
    quality = session["design_baseline"]["module_design_quality"]
    assert quality["status"] == "passed"
    assert quality["metrics"]["complete_module_count"] == 1
    assert session["design_baseline"]["module_designs"][0]["capabilities"][0]["functions"] == [
        "创建规划任务",
        "校验规划时段",
        "校验任务范围",
    ]
    assert not [finding for finding in session["design_baseline"]["review_findings"] if finding["target"] == "模块设计"]


def test_software_design_v2_warns_when_document_outline_uses_frontend_backend_as_primary_sections(monkeypatch) -> None:
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
                        {"section_id": "sdd-01", "title": "1. 文档目的与设计口径", "content": "设计口径。"},
                        {"section_id": "sdd-02", "title": "2. 系统定位", "content": "系统定位。"},
                        {"section_id": "sdd-03", "title": "3. 业务目标与边界", "content": "业务边界。"},
                        {"section_id": "sdd-04", "title": "4. 总体架构", "content": "总体架构。"},
                        {"section_id": "sdd-05", "title": "5. 前端软件设计", "content": "前端工作台。"},
                        {"section_id": "sdd-06", "title": "6. 后端软件设计", "content": "后端服务。"},
                        {"section_id": "sdd-07", "title": "7. 核心对象模型", "content": "对象模型。"},
                    ],
                },
                design_package={
                    "package_id": "SDP-DOC-OUTLINE-HORIZONTAL",
                    "status": "draft",
                    "document_projection": {},
                    "module_designs": [
                        _complete_module_design("planning-task", "规划任务管理"),
                        _complete_module_design("space-analysis", "空间分析"),
                        _complete_module_design("collaboration-confirm", "协同确认"),
                    ],
                    "functional_tree_projection": {
                        "modules": [
                            {"module_id": "planning-task", "name": "规划任务管理", "source_refs": ["REQ-FR-001"]},
                            {"module_id": "space-analysis", "name": "空间分析", "source_refs": ["REQ-FR-002"]},
                            {"module_id": "collaboration-confirm", "name": "协同确认", "source_refs": ["REQ-FR-003"]},
                        ]
                    },
                    "layered_architecture_projection": {},
                    "technical_implementation_projection": {},
                    "api_projection": {},
                    "workflow_projection": {},
                    "quality_gate_projection": {},
                    "p4_workorder_projection": {},
                },
                traceability=[],
                gap_list=[],
                review_findings=[],
                workorder_projection_candidate={},
                process_output={"quality_summary": {"blocking_count": 0, "warning_count": 0, "passed_count": 3}},
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
            "design_title": "横切目录质量检测软设",
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
    assert session["design_baseline"]["module_design_quality"]["status"] == "passed"
    quality = session["design_baseline"]["document_outline_quality"]
    assert quality["status"] == "warning"
    assert quality["metrics"]["module_section_count"] == 0
    assert quality["metrics"]["frontend_backend_section_count"] == 2
    assert session["design_baseline"]["review_findings"][0]["finding_id"] == "P3-DOC-OUTLINE-HORIZONTAL-SPLIT"
    assert "软设正文目录" in session["design_baseline"]["pending_confirmations"][0]
    assert session["check_result"]["warning_count"] == 1
    assert session["check_result"]["items"][-1]["scope"] == "design_document"


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
