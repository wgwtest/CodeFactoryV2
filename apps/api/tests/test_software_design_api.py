from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.software_design import get_software_design_service
from app.main import create_app
from app.software_design.service import SoftwareDesignService


def _create_requirement_spec(client: TestClient) -> str:
    response = client.post(
        "/api/requirements/specs",
        json={
            "archive_id": "20161116-nas",
            "status": "ready",
            "payload": {
                "application": {
                    "name": "空域协同规划软件",
                    "domain": "国家空域管理",
                    "summary": "围绕规划任务和审批流形成协同规划能力。",
                    "target_users": ["规划员", "审核员"],
                },
                "objects": [
                    {
                        "id": "planning-task",
                        "name": "规划任务",
                        "object_kind": "business",
                        "source_kind": "temporary",
                        "category": "domain_object",
                        "aliases": [],
                        "summary": "描述一次规划活动。",
                        "description": "用于承载规划状态、审批记录和输出。",
                        "source_archive_id": None,
                        "source_item_type": None,
                        "source_item_id": None,
                    }
                ],
                "processes": [],
                "rules": [],
                "metrics": [],
                "non_functional_constraints": [
                    {
                        "id": "constraint-audit",
                        "name": "全链路留痕",
                        "category": "audit",
                        "description": "关键审批和状态变更必须可追溯。",
                    }
                ],
            },
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _build_client(tmp_path: Path) -> TestClient:
    app = create_app()
    service = SoftwareDesignService(root=tmp_path / "software-design")
    app.dependency_overrides[get_software_design_service] = lambda: service
    return TestClient(app)


def test_software_design_order_lifecycle(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    spec_id = _create_requirement_spec(client)

    created = client.post(
        "/api/software-design/orders",
        json={
            "requirement_spec_id": spec_id,
            "requested_by": "架构组",
            "notes": "请先生成统一服务版本的软设草案。",
        },
    )
    assert created.status_code == 201
    order_id = created.json()["order_id"]
    assert created.json()["status"] == "pending_approval"

    overview = client.get("/api/software-design/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["pending_approval_count"] == 1

    approved = client.post(f"/api/software-design/orders/{order_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved_for_generation"

    generated = client.post(f"/api/software-design/orders/{order_id}/generate-draft")
    assert generated.status_code == 200
    assert generated.json()["status"] == "draft_ready"
    assert generated.json()["design_description"]["sections"][0]["title"] == "1. 设计目标与范围"

    thread = client.post(
        f"/api/software-design/orders/{order_id}/review-threads",
        json={
            "topic": "统一服务是否满足首版性能要求",
            "anchor": "section:architecture",
            "message": "请保留统一服务建议，但补充后续微服务拆分条件。",
        },
    )
    assert thread.status_code == 201
    assert thread.json()["status"] == "open"

    frozen = client.post(f"/api/software-design/orders/{order_id}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "frozen"

    batch = client.post(f"/api/software-design/orders/{order_id}/workorder-batch")
    assert batch.status_code == 201
    assert batch.json()["package_overview"]["architecture_recommendation"] == "unified_service"
    assert len(batch.json()["items"]) >= 1

    pushed = client.post(f"/api/software-design/orders/{order_id}/push-to-p4")
    assert pushed.status_code == 200
    assert pushed.json()["push_status"] == "pushed"


def test_software_design_reference_center_exposes_templates_and_standard_search(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    center = client.get("/api/software-design/reference-center")
    assert center.status_code == 200
    assert len(center.json()["templates"]) >= 2
    assert center.json()["templates"][0]["document_type"] == "software_design_description"
    assert center.json()["templates"][0]["pdf_url"] is None
    assert center.json()["standards"][0]["doc_id"].startswith("DI-IPSC-")

    search = client.get("/api/software-design/standards/search", params={"q": "design description"})
    assert search.status_code == 200
    matched_ids = {item["doc_id"] for item in search.json()["items"]}
    assert "DI-IPSC-82284" in matched_ids
    assert "DI-IPSC-81435" in matched_ids


def test_software_design_order_can_be_rejected(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    spec_id = _create_requirement_spec(client)

    created = client.post(
        "/api/software-design/orders",
        json={
            "requirement_spec_id": spec_id,
            "requested_by": "架构组",
            "notes": "暂不进入本轮设计。",
        },
    )
    order_id = created.json()["order_id"]

    rejected = client.post(f"/api/software-design/orders/{order_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_requirement_spec_can_only_create_one_p3_order(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    spec_id = _create_requirement_spec(client)

    first = client.post(
        "/api/software-design/orders",
        json={
            "requirement_spec_id": spec_id,
            "requested_by": "架构组",
            "notes": "首轮受理。",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/software-design/orders",
        json={
            "requirement_spec_id": spec_id,
            "requested_by": "架构组",
            "notes": "重复提交。",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == f"P3 order already exists for requirement spec {spec_id}"
