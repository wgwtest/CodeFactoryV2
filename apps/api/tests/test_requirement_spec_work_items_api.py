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


def test_requirement_spec_work_item_create_list_configure_and_publish() -> None:
    client = TestClient(create_app())
    templates = client.get("/api/requirement-authoring/templates")
    assert templates.status_code == 200
    template_id = templates.json()[0]["template_id"]

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
    assert item["title"] == "空域协同规划软件需求规格说明"
    assert item["status"] == "draft"
    assert item["template_id"] == template_id
    assert item["initial_description"] == "面向运行协调员和体系架构师的协同规划工具。"
    assert item["authoring_document_id"]
    assert item["analysis_session_id"] is None
    assert item["published_requirement_spec_id"] is None
    assert item["p3_consumable"] is False
    assert item["next_action"] == "enter_config"

    listed = client.get("/api/requirement-analysis/spec-items")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["spec_item_id"] == item["spec_item_id"]
    assert listed.json()["items"][0]["available_actions"] == ["enter_config", "publish"]

    configured = client.post(
        f"/api/requirement-analysis/spec-items/{item['spec_item_id']}/configure",
        json={
            "topic": "空域协同规划软件需求规格说明",
            "orchestrator_id": "brainstorm-v1",
            "provider_id": "mock",
            "model": "mock-requirement-analysis-v1",
            "template_id": "xg-template-81433-默认运算软件需求规格说明模板实例-v1-0",
            "knowledge_package_id": "airspace-domain-demo",
            "write_policy": "patch_suggestion_only",
        },
    )
    assert configured.status_code == 200
    configured_item = configured.json()
    assert configured_item["status"] == "configured"
    assert configured_item["analysis_session_id"]

    blocked = client.post(f"/api/requirement-analysis/spec-items/{item['spec_item_id']}/publish")
    assert blocked.status_code == 409
    assert "blocking gaps" in blocked.json()["detail"]

    _complete_document_for_publish(client, item["authoring_document_id"])
    published = client.post(f"/api/requirement-analysis/spec-items/{item['spec_item_id']}/publish")
    assert published.status_code == 200
    published_item = published.json()
    assert published_item["status"] == "published_to_p3"
    assert published_item["p3_consumable"] is True
    assert published_item["published_requirement_spec_id"]
    assert published_item["published_package_id"]

    specs = client.get("/api/requirements/specs")
    assert specs.status_code == 200
    assert specs.json()[0]["id"] == published_item["published_requirement_spec_id"]
    assert specs.json()[0]["application_name"] == "空域协同规划软件"


def test_requirement_spec_work_item_create_accepts_lab_template_instance_id() -> None:
    client = TestClient(create_app())
    lab_config = client.get("/api/requirement-analysis/lab-config")
    assert lab_config.status_code == 200
    lab_template_id = lab_config.json()["defaults"]["template_id"]

    created = client.post(
        "/api/requirement-analysis/spec-items",
        json={
            "title": "态势分析系统需求规格说明",
            "initial_description": "用于态势分析系统的需求分析。",
            "template_id": lab_template_id,
            "create_action": "enter_config",
        },
    )

    assert created.status_code == 200
    item = created.json()
    assert item["template_id"] == lab_template_id

    document = client.get(f"/api/requirement-authoring/documents/{item['authoring_document_id']}")
    assert document.status_code == 200
    assert document.json()["template_id"] == "tpl-81433-default"
