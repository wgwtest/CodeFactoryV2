from fastapi.testclient import TestClient

from app.main import create_app


def _complete_document_for_publish(client: TestClient, document_id: str) -> None:
    response = client.patch(
        f"/api/requirement-authoring/documents/{document_id}/form-fields",
        json={
            "fields": {
                "application_name": "空域协同规划软件",
                "domain_scope": "国家空域管理",
                "target_users": "运行协调员、体系架构师",
                "application_scope": "空域协同规划任务链",
                "business_goals": "支撑协同规划和冲突处置闭环。",
                "main_scenarios": "规划任务创建、冲突识别、协同确认和处置复核。",
                "usage_modes": "运行协调员主用，体系架构师复核配置。",
                "in_scope": "规划任务、冲突识别、协同确认和处置记录。",
                "out_of_scope": "不包含自动生成最优处置方案。",
                "main_process": "协同规划与冲突处置",
                "normal_flow": "创建规划、识别冲突、协同确认、形成处置记录。",
                "exception_flow": "冲突识别超时后提醒运行协调员人工确认，并保留处置原因。",
                "situational_display": "展示规划任务、冲突状态和处置进展。",
                "gis_analysis_tools": "支持基础地图定位、空间查询和冲突区域查看。",
                "deployment_analysis": "支持规划方案影响范围辅助分析。",
                "result_outputs": "输出处置记录、冲突清单和简化报告。",
                "collaboration_mode": "支持运行协调员提交、体系架构师复核。",
                "input_data_sources": "空域基础数据、规划任务、冲突规则和处置记录。",
                "input_data_mode": "人工录入和文件导入结合。",
                "performance_requirements": "关键告警 2 分钟内反馈。",
                "reliability_requirements": "关键状态变更需留痕。",
                "security_requirements": "按用户身份和任务范围授权。",
                "permission_model": "运行协调员可编辑，体系架构师可复核，其他用户只读。",
                "deployment_environment": "内网环境部署。",
                "accuracy_constraints": "辅助规划级精度，不承诺工程测绘精度。",
                "acceptance_scenarios": "完成规划任务创建、冲突识别、协同确认和处置记录导出。",
                "acceptance_criteria": "关键流程可追溯，超时提醒和处置导出结果可验证。",
            }
        },
    )
    assert response.status_code == 200


def test_p2_publish_registers_platform_artifact_and_p3_consumes_it() -> None:
    client = TestClient(create_app())
    template_id = client.get("/api/requirement-authoring/templates").json()[0]["template_id"]

    created = client.post(
        "/api/requirement-analysis/spec-items",
        json={
            "title": "空域协同规划软件需求规格说明",
            "initial_description": "面向运行协调员和体系架构师的协同规划工具。",
            "template_id": template_id,
            "knowledge_binding": {
                "editor_badge": "领域知识：空域规划",
                "domain": {"domain_id": "airspace-planning", "domain_name": "空域规划领域知识"},
            },
            "create_action": "enter_config",
        },
    )
    assert created.status_code == 200
    item = created.json()

    _complete_document_for_publish(client, item["authoring_document_id"])
    published = client.post(f"/api/requirement-analysis/spec-items/{item['spec_item_id']}/publish")
    assert published.status_code == 200
    published_item = published.json()

    artifacts = client.get(
        "/api/platform-exchange/artifacts",
        params={"artifact_type": "requirement_spec_package", "producer_stage": "P2"},
    )
    assert artifacts.status_code == 200
    artifact_items = artifacts.json()["items"]
    assert len(artifact_items) == 1
    artifact = artifact_items[0]
    assert published_item["published_package_id"] == artifact["artifact_id"]
    assert artifact["artifact_type"] == "requirement_spec_package"
    assert artifact["producer_ref_id"] == item["spec_item_id"]
    assert artifact["payload"]["structured_spec"]["application"]["name"] == "空域协同规划软件"
    assert artifact["payload"]["p3_consumable"] is True
    assert artifact["payload"]["source_trace"]["authoring_document_id"] == item["authoring_document_id"]
    assert artifact["payload_hash"]

    input_packages = client.get("/api/software-design-v2/input-packages")
    assert input_packages.status_code == 200
    assert input_packages.json()["items"][0]["input_package_id"] == artifact["artifact_id"]
    assert input_packages.json()["items"][0]["source_document_id"] == item["authoring_document_id"]

    session_response = client.post(
        "/api/software-design-v2/sessions",
        json={
            "input_package_id": artifact["artifact_id"],
            "generation_policy": {
                "architecture_preference": "统一服务优先，保留拆分点",
                "module_granularity": "3-5 个业务模块，不拆太细",
                "output_style": "按标准软设正文写，不写聊天语气",
            },
        },
    )
    assert session_response.status_code == 200
    design_session = session_response.json()

    consumptions = client.get("/api/platform-exchange/consumptions", params={"artifact_id": artifact["artifact_id"]})
    assert consumptions.status_code == 200
    consumption_items = consumptions.json()["items"]
    assert len(consumption_items) == 1
    assert consumption_items[0]["artifact_id"] == artifact["artifact_id"]
    assert consumption_items[0]["consumer_stage"] == "P3"
    assert consumption_items[0]["consumer_ref_id"] == design_session["session_id"]
    assert consumption_items[0]["result_status"] == "accepted"

    monitor = client.get("/api/platform-exchange/monitor")
    assert monitor.status_code == 200
    monitor_data = monitor.json()
    stage_keys = [stage["stage"] for stage in monitor_data["stages"]]
    assert stage_keys == ["P1", "P2", "P3", "P4", "P5"]

    p1_panel = next(stage for stage in monitor_data["stages"] if stage["stage"] == "P1")
    p2_panel = next(stage for stage in monitor_data["stages"] if stage["stage"] == "P2")
    p3_panel = next(stage for stage in monitor_data["stages"] if stage["stage"] == "P3")
    p4_panel = next(stage for stage in monitor_data["stages"] if stage["stage"] == "P4")
    p5_panel = next(stage for stage in monitor_data["stages"] if stage["stage"] == "P5")

    assert p2_panel["published"][0]["artifact_id"] == artifact["artifact_id"]
    assert p2_panel["published"][0]["artifact_type"] == "requirement_spec_package"
    assert p2_panel["published"][0]["payload_hash"] == artifact["payload_hash"]
    assert p3_panel["consumed"][0]["artifact_id"] == artifact["artifact_id"]
    assert p3_panel["consumed"][0]["consumer_ref_id"] == design_session["session_id"]
    assert p1_panel["empty_state"] == "暂无平台资源 / 暂无消费记录 / 未接入首版链路"
    assert p4_panel["empty_state"] == "暂无平台资源 / 暂无消费记录 / 未接入首版链路"
    assert p5_panel["empty_state"] == "暂无平台资源 / 暂无消费记录 / 未接入首版链路"

    base_platform = monitor_data["base_platform"]
    assert base_platform["artifact_totals"]["by_type"]["requirement_spec_package"] == 1
    assert base_platform["artifact_totals"]["by_producer_stage"]["P2"] == 1
    assert base_platform["artifact_totals"]["by_lifecycle_status"]["published"] == 1
    assert base_platform["consumption_totals"]["by_consumer_stage"]["P3"] == 1
    assert base_platform["latest_artifacts"][0]["artifact_id"] == artifact["artifact_id"]
    assert base_platform["latest_consumptions"][0]["artifact_id"] == artifact["artifact_id"]
