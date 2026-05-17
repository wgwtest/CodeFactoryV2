from fastapi.testclient import TestClient

from app.main import create_app


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
