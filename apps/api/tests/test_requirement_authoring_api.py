from fastapi.testclient import TestClient

from app.main import create_app


def test_requirement_authoring_document_lifecycle() -> None:
    client = TestClient(create_app())

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
    assert "超时提醒" in updated["document"]["sections"][2]["clauses"][2]["content"]
    assert updated["conversation"][-1]["role"] == "assistant"
    assert "可以直接回" in updated["conversation"][-1]["content"]

    form_updated = client.patch(
        f"/api/requirement-authoring/documents/{document['document_id']}/form-fields",
        json={"fields": {"acceptance_criteria": "关键流程可追溯，超时提醒可验证。"}},
    )
    assert form_updated.status_code == 200
    assert "关键流程可追溯" in form_updated.json()["document"]["sections"][4]["clauses"][0]["content"]

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
                "main_process": "协同规划与冲突处置",
                "normal_flow": "创建规划、识别冲突、协同确认、形成处置记录。",
                "non_functional": "关键告警 2 分钟内反馈。",
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
