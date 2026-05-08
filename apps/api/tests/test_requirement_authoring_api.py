from fastapi.testclient import TestClient

from app.main import create_app


def test_requirement_authoring_document_lifecycle() -> None:
    client = TestClient(create_app())

    workbench_config = client.get("/api/requirement-authoring/workbench-config")
    assert workbench_config.status_code == 200
    config = workbench_config.json()
    assert config["page"]["title"] == "P2 专家需求规格编写工作台"
    assert config["defaults"]["document_title"] == "未命名软件需求规格说明"
    assert config["defaults"]["layout_ratio"] == "2:3"
    assert config["layout_options"] == [
        {"ratio": "2:3", "label": "2:3"},
        {"ratio": "1:1", "label": "1:1"},
    ]
    assert next(item for item in config["document_statuses"] if item["status"] == "draft")["label"] == "草稿"
    assert [item["action_id"] for item in config["actions"]] == [
        "create_document",
        "open_document",
        "save_draft",
        "delete_document",
        "run_check",
        "freeze",
    ]
    assert config["document_surface"]["ribbon"] == ["页面 A4", "样式 标准正文", "段落 1.5 倍行距", "导出 DOCX / PDF"]

    templates = client.get("/api/requirement-authoring/templates")
    assert templates.status_code == 200
    assert templates.json()[0]["template_code"] == "81433"
    assert templates.json()[0]["status"] == "active"

    created = client.post(
        "/api/requirement-authoring/documents",
        json={
            "title": "空域协同规划软件需求规格说明",
            "template_id": templates.json()[0]["template_id"],
            "archive_ids": ["20161116-nas"],
        },
    )
    assert created.status_code == 200
    document = created.json()
    assert document["layout_ratio"] == "2:3"
    assert document["status"] == "draft"
    assert document["document"]["sections"][2]["clauses"][0]["clause_id"] == "REQ-3.1"
    assert "待补齐" in document["document"]["sections"][2]["clauses"][1]["content"]

    replied = client.post(
        f"/api/requirement-authoring/documents/{document['document_id']}/messages",
        json={"content": "加超时，别写太复杂"},
    )
    assert replied.status_code == 200
    updated = replied.json()
    assert updated["semantic_state"]["fields"]["exception_flow"] == "包含超时提醒和人工确认，不扩展复杂补偿链路。"
    assert "超时提醒" in updated["document"]["sections"][2]["clauses"][6]["content"]
    assert updated["conversation"][-1]["role"] == "assistant"
    assert "可以直接回" in updated["conversation"][-1]["content"]

    form_updated = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
        json={"fields": {"acceptance_criteria": "关键流程可追溯，超时提醒可验证。"}},
    )
    assert form_updated.status_code == 200
    assert "关键流程可追溯" in form_updated.json()["document"]["sections"][5]["clauses"][1]["content"]

    renamed = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
        json={"fields": {"application_name": "空域态势研判软件"}},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "空域协同规划软件需求规格说明"
    assert renamed.json()["document"]["title"] == "空域态势研判软件需求规格说明"

    saved = client.post(
        f"/api/requirement-authoring/documents/{document['document_id']}/save",
        json={
            "title": "专家评审草稿 A",
            "template_id": templates.json()[1]["template_id"],
            "archive_ids": ["airspace-planning-archive"],
            "knowledge_binding": {
                "editor_badge": "领域知识：空域规划",
                "domain": {"domain_id": "airspace-planning", "domain_name": "空域规划领域知识"},
            },
        },
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "draft"
    assert saved.json()["title"] == "专家评审草稿 A"
    assert saved.json()["template_id"] == templates.json()[1]["template_id"]
    assert saved.json()["archive_ids"] == ["airspace-planning-archive"]
    assert saved.json()["semantic_state"]["knowledge_binding"]["editor_badge"] == "领域知识：空域规划"
    assert saved.json()["document"]["title"] == "空域态势研判软件需求规格说明"

    cleared_context = client.post(
        f"/api/requirement-authoring/documents/{document['document_id']}/save",
        json={"title": "专家评审草稿 A", "archive_ids": [], "knowledge_binding": None},
    )
    assert cleared_context.status_code == 200
    assert cleared_context.json()["archive_ids"] == []
    assert cleared_context.json()["semantic_state"]["knowledge_binding"] is None

    restored_context = client.post(
        f"/api/requirement-authoring/documents/{document['document_id']}/save",
        json={
            "title": "专家评审草稿 A",
            "template_id": templates.json()[1]["template_id"],
            "archive_ids": ["airspace-planning-archive"],
            "knowledge_binding": {
                "editor_badge": "领域知识：空域规划",
                "domain": {"domain_id": "airspace-planning", "domain_name": "空域规划领域知识"},
            },
        },
    )
    assert restored_context.status_code == 200
    assert "关键流程可追溯" in saved.json()["document"]["sections"][5]["clauses"][1]["content"]
    assert saved.json()["conversation"][-1]["role"] == "assistant"

    checked = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/check")
    assert checked.status_code == 200
    assert checked.json()["check_result"]["blocking_count"] > 0

    freeze_blocked = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/freeze")
    assert freeze_blocked.status_code == 409

    completed = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
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
            }
        },
    )
    assert completed.status_code == 200

    checked_ready = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/check")
    assert checked_ready.json()["status"] == "ready_to_freeze"

    frozen = client.post(f"/api/requirement-authoring/documents/{document['document_id']}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"
    assert frozen.json()["frozen_package"]["p3_consumable"] is True
    assert frozen.json()["frozen_package"]["structured_spec"]["application"]["name"] == "空域协同规划软件"

    deleted = client.delete(f"/api/requirement-authoring/documents/{document['document_id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "document_id": document["document_id"]}

    missing = client.get(f"/api/requirement-authoring/documents/{document['document_id']}")
    assert missing.status_code == 404
