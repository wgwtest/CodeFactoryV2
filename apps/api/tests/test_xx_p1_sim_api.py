from fastapi.testclient import TestClient

from app.main import create_app


def test_xx_p1_sim_lists_domain_knowledge_catalog() -> None:
    client = TestClient(create_app())

    response = client.get("/api/xx-p1-sim/domains")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"]["provider_id"] == "xx-p1-sim"
    assert body["provider"]["provider_kind"] == "p1_knowledge_provider"
    assert body["provider"]["capabilities"] == ["domain_catalog", "knowledge_archive"]
    assert body["items"][0]["domain_id"] == "airspace-planning"
    assert body["items"][0]["domain_name"] == "空域规划领域知识"
    assert body["items"][0]["archive_version"] == "v1.0"
    assert "空域协同规划软件" not in str(body)
    assert "RequirementAuthoringSession" not in str(body)


def test_xx_p1_sim_registers_resets_and_records_call_logs() -> None:
    client = TestClient(create_app())

    registered = client.post("/api/xx-p1-sim/register")
    assert registered.status_code == 200
    assert registered.json()["provider_id"] == "xx-p1-sim"
    assert registered.json()["status"] == "online"

    reset = client.post("/api/xx-p1-sim/reset")
    assert reset.status_code == 200
    assert reset.json()["seed"] == "xx-p1-sim-fixed-v1"
    assert reset.json()["archive_version"] == "v1.0"

    archive = client.get("/api/xx-p1-sim/domains/airspace-planning/knowledge")
    assert archive.status_code == 200
    archive_body = archive.json()
    assert archive_body["domain_id"] == "airspace-planning"
    assert archive_body["archive_version"] == "v1.0"
    assert [concept["name"] for concept in archive_body["concepts"]] == ["空域单元", "冲突窗口", "协同任务"]
    assert archive_body["rules"][0]["name"] == "冲突窗口确认规则"
    assert archive_body["processes"][0]["name"] == "空域规划协同流程"
    assert archive_body["constraints"][0]["category"] == "traceability"
    assert archive_body["evidence_refs"][0]["source"] == "P1 发布态领域知识"
    assert "空域协同规划软件" not in str(archive_body)

    logs = client.get("/api/xx-p1-sim/logs")
    assert logs.status_code == 200
    log_items = logs.json()["items"]
    assert log_items[-1]["method"] == "GET"
    assert log_items[-1]["path"] == "/api/xx-p1-sim/domains/airspace-planning/knowledge"
    assert log_items[-1]["domain_id"] == "airspace-planning"
    assert log_items[-1]["status_code"] == 200
