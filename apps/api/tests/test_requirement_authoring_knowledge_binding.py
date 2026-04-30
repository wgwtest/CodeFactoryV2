from fastapi.testclient import TestClient

from app.main import create_app


def test_p2_binds_xx_p1_sim_domain_knowledge() -> None:
    client = TestClient(create_app())

    providers = client.get("/api/requirement-authoring/knowledge-providers")
    assert providers.status_code == 200
    provider_body = providers.json()
    assert provider_body["items"][0]["provider_id"] == "xx-p1-sim"
    assert provider_body["items"][0]["provider_name"] == "XX-P1-Sim"
    assert provider_body["items"][0]["status"] == "online"
    assert provider_body["items"][0]["domains"][0]["domain_name"] == "空域规划领域知识"

    bound = client.post(
        "/api/requirement-authoring/knowledge-bindings",
        json={"provider_id": "xx-p1-sim", "domain_id": "airspace-planning"},
    )

    assert bound.status_code == 200
    binding = bound.json()
    assert binding["binding_id"] == "binding-xx-p1-sim-airspace-planning"
    assert binding["provider"]["provider_id"] == "xx-p1-sim"
    assert binding["domain"]["domain_id"] == "airspace-planning"
    assert binding["domain"]["domain_name"] == "空域规划领域知识"
    assert binding["knowledge_archive"]["archive_version"] == "v1.0"
    assert len(binding["knowledge_archive"]["concepts"]) >= 3
    assert len(binding["knowledge_archive"]["rules"]) >= 1
    assert len(binding["knowledge_archive"]["processes"]) >= 1
    assert len(binding["knowledge_archive"]["constraints"]) >= 1
    assert len(binding["knowledge_archive"]["evidence_refs"]) >= 1
    assert binding["editor_badge"] == "领域知识已绑定"
    assert binding["created_document"] is None
    assert binding["frozen_package"] is None
    assert "空域协同规划软件" not in str(binding)
    assert "RequirementAuthoringSession" not in str(binding)
