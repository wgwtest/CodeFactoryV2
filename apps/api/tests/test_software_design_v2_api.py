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
                "target_users": "运行协调员、体系架构师、空域规划专家",
                "main_process": "协同规划与冲突处置",
                "normal_flow": "创建规划任务、识别冲突、协同确认、形成处置记录。",
                "exception_flow": "异常流程包含超时提醒和人工确认，不扩展复杂补偿链路。",
                "non_functional": "关键告警 2 分钟内反馈，关键状态变更需留痕。",
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
            "generation_policy": {
                "architecture_preference": "统一服务优先，保留拆分点",
                "module_granularity": "3-5 个业务模块，不拆太细",
                "output_style": "按标准软设正文写，不写聊天语气",
            },
        },
    )
    assert session_response.status_code == 200
    session = session_response.json()
    assert session["status"] == "created"
    assert session["input_package"]["source_document_id"] == frozen["document_id"]

    generated = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/generate")
    assert generated.status_code == 200
    generated_session = generated.json()
    assert generated_session["status"] == "baseline_ready"
    assert generated_session["design_document"]["title"] == "空域协同规划软件设计说明"
    assert generated_session["design_baseline"]["architecture_mode"] == "unified_service"
    assert generated_session["workorder_projection"]["items"][0]["title"] == "规划任务管理模块实现"

    turned = client.post(
        f"/api/software-design-v2/sessions/{session['session_id']}/turns",
        json={"user_input": "按保守方案，增加状态机说明"},
    )
    assert turned.status_code == 200
    turn_payload = turned.json()
    assert turn_payload["turn"]["normalized_intent"] == "add_state_machine"
    assert "状态机" in turn_payload["turn"]["assistant_message"]
    assert turn_payload["session"]["design_baseline"]["pending_confirmations"]

    checked_v2 = client.post(f"/api/software-design-v2/sessions/{session['session_id']}/check")
    assert checked_v2.status_code == 200
    assert checked_v2.json()["check_result"]["blocking_count"] == 0
    assert checked_v2.json()["check_result"]["passed_count"] >= 3
