from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes.software_build import get_software_build_service
from app.main import create_app
from app.software_build.service import SoftwareBuildService
from app.software_design.models import DesignModule, DesignSection, P3Order, SoftwareDesignBaseline, now_iso
from app.software_design.repository import SoftwareDesignRepository
from app.tool_hub.models import ToolDefinition, ToolVerification
from app.tool_hub.repository import ToolHubRepository


def _seed_frozen_p3_order(
    tmp_path: Path,
    module_specs: list[dict[str, object]] | None = None,
) -> str:
    repository = SoftwareDesignRepository(tmp_path / "software-design")
    timestamp = now_iso()
    if module_specs is None:
        module_specs = [
            {
                "module_id": "module-planning",
                "name": "规划任务管理",
                "objective": "围绕规划任务实现核心流程。",
                "inputs": ["planning_request"],
                "outputs": ["planning_task"],
                "constraints": ["关键状态变更需留痕"],
                "recommended_tools": ["workflow_engine"],
            }
        ]
    order = repository.save_order(
        P3Order(
            order_id="p3-order-frozen-001",
            requirement_spec_id="spec-001",
            application_name="空域协同规划软件",
            domain_name="国家空域管理",
            requirement_spec_status="ready",
            requested_by="架构组",
            notes="冻结后进入 P5",
            status="frozen",
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    repository.save_baseline(
        SoftwareDesignBaseline(
            baseline_id="baseline-001",
            order_id=order.order_id,
            requirement_spec_id=order.requirement_spec_id,
            sections=[
                DesignSection(
                    id="modules",
                    title="3. 模块划分与职责",
                    summary="描述核心模块。",
                    body="首版围绕规划任务管理模块交付。",
                )
            ],
            modules=[
                DesignModule.model_validate(module_spec) for module_spec in module_specs
            ],
        )
    )
    return order.order_id


def _seed_tool_hub_tool(tmp_path: Path, tool_id: str, slug: str, keywords: list[str] | None = None) -> None:
    repository = ToolHubRepository(tmp_path / "tool-hub")
    repository.save_tool(
        ToolDefinition(
            tool_id=tool_id,
            name="工作流引擎",
            slug=slug,
            status="active",
            summary="用于承载审批流与状态机执行。",
            problem_statement="解决流程驱动型业务模块的编排问题。",
            primary_domain_id="workflow_approval",
            tool_form_id="service_endpoint",
            runtime_platform_ids=["agent_runtime"],
            tags=["domain:workflow_approval", "form:service_endpoint"],
            lifecycle_stage_ids=["solution_design"],
            input_types=["structured_json"],
            output_types=["structured_json"],
            supported_sources=["tool_hub_snapshot"],
            usage_notes="供 P5 装配绑定验证使用。",
            keywords=keywords or [],
            verification=ToolVerification(status="verified"),
        )
    )


def _build_client(tmp_path: Path) -> TestClient:
    app = create_app()
    service = SoftwareBuildService(
        root=tmp_path / "software-build",
        software_design_root=tmp_path / "software-design",
        tool_hub_root=tmp_path / "tool-hub",
    )
    app.dependency_overrides[get_software_build_service] = lambda: service
    return TestClient(app)


def _create_design_input_sim(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/software-build/design-inputs/sim",
        json={
            "application_name": "基于地理信息系统的通视分析软件",
            "requirement_spec_id": "spec-gis-los-analysis-001",
            "baseline_id": "baseline-gis-los-analysis-001",
            "notes": "基于地理信息系统的通视分析软件冻结设计样例",
            "module_specs": [
                {
                    "module_id": "module-ui",
                    "name": "构建工作台",
                    "objective": "渲染 P5 工作台前端。",
                    "inputs": ["delivery_order"],
                    "outputs": ["workspace_ui"],
                    "constraints": ["必须保留独立工作台壳层"],
                    "recommended_tools": ["ui_shell"],
                },
                {
                    "module_id": "module-feedback",
                    "name": "缺口评审留痕",
                    "objective": "沉淀缺口与待确认反馈任务。",
                    "inputs": ["attempt_manifest"],
                    "outputs": ["feedback_task"],
                    "constraints": ["评审状态必须可回看"],
                    "recommended_tools": ["feedback_console"],
                },
                {
                    "module_id": "module-docs",
                    "name": "交付文档生成",
                    "objective": "生成 delivery report 和 gap list。",
                    "inputs": ["attempt_manifest"],
                    "outputs": ["delivery_docs"],
                    "constraints": ["输出目录必须包含 docs"],
                    "recommended_tools": ["doc_builder"],
                },
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_supply_input_sim(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/software-build/supply-inputs/sim",
        json={
            "snapshot_name": "通视分析软件供给样例快照",
            "notes": "供通视分析软件样例命中使用",
            "tools": [
                {
                    "tool_id": "tool-ui-shell",
                    "tool_name": "UI Shell",
                    "tool_slug": "ui-shell",
                    "verification_status": "verified",
                    "keywords": ["ui_shell", "workspace", "frontend"],
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_p5_delivery_order_can_be_created_from_frozen_p3_order(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _seed_frozen_p3_order(tmp_path)

    created = client.post(
        "/api/software-build/orders",
        json={
            "p3_order_id": p3_order_id,
            "requested_by": "P5",
            "notes": "首轮组装",
        },
    )

    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert created.json()["active_input_binding"]["is_confirmed"] is False

    overview = client.get("/api/software-build/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["order_count"] == 1


def test_p5_attempt_requires_confirmed_input_binding(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    design_input = _create_design_input_sim(client)
    created = client.post(
        "/api/software-build/orders",
        json={
            "design_input_id": design_input["design_input_id"],
            "requested_by": "P5",
            "notes": "最小闭环",
        },
    )

    assert created.status_code == 201
    delivery_order_id = created.json()["delivery_order_id"]

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )

    assert attempt.status_code == 400
    assert attempt.json()["detail"] == "P5 input binding is not confirmed"

    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": design_input["design_input_id"],
            "supply_mode": "empty",
            "confirmed_by": "P5",
        },
    )

    assert binding.status_code == 200
    assert binding.json()["is_confirmed"] is True
    assert binding.json()["supply_mode"] == "empty"


def test_p5_attempt_exports_directory_and_gap_files(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _seed_frozen_p3_order(tmp_path)
    created = client.post(
        "/api/software-build/orders",
        json={
            "p3_order_id": p3_order_id,
            "requested_by": "P5",
            "notes": "首轮组装",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]
    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": created.json()["active_input_binding"]["design_input_id"],
            "supply_mode": "empty",
            "confirmed_by": "P5",
        },
    )
    assert binding.status_code == 200

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )

    assert attempt.status_code == 201
    payload = attempt.json()
    assert payload["sequence"] == 1
    assert payload["validation_report"]["structure_status"] == "passed"
    export_directory = Path(payload["export_directory"])
    assert export_directory.joinpath("frontend").is_dir()
    assert export_directory.joinpath("backend").is_dir()
    assert export_directory.joinpath("deploy").is_dir()
    assert export_directory.joinpath("docs", "delivery-report.md").exists()
    assert export_directory.joinpath("docs", "gap-list.md").exists()
    assert export_directory.joinpath("build-manifest.json").exists()
    assert payload["runtime_snapshot"]["executor_status"] == "completed"
    assert payload["runtime_snapshot"]["stages"][0]["stage_id"] == "intake"
    assert payload["output_preview"]["directories"] == ["frontend", "backend", "deploy", "docs"]
    assert payload["output_preview"]["key_files"][0]["path"] == "build-manifest.json"
    assert payload["input_snapshot"]["design_input"]["module_count"] == 1
    assert payload["input_snapshot"]["supply_input"]["source_kind"] == "empty_supply"


def test_p5_attempt_marks_supply_hits_and_pending_feedback(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    design_input = _create_design_input_sim(client)
    supply_input = _create_supply_input_sim(client)
    created = client.post(
        "/api/software-build/orders",
        json={
            "design_input_id": design_input["design_input_id"],
            "requested_by": "P5",
            "notes": "首轮组装",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]
    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": design_input["design_input_id"],
            "supply_input_id": supply_input["supply_input_id"],
            "supply_mode": "snapshot",
            "confirmed_by": "P5",
        },
    )
    assert binding.status_code == 200

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )

    assert attempt.status_code == 201
    payload = attempt.json()
    assert payload["assembly_plan"]["modules"][0]["binding_status"] == "bound"
    assert payload["assembly_plan"]["modules"][1]["binding_status"] == "placeholder"
    assert payload["assembly_plan"]["modules"][2]["binding_status"] == "placeholder"
    assert payload["feedback_tasks"][0]["status"] == "pending_confirmation"
    assert payload["input_snapshot"]["supply_input"]["source_kind"] == "xx_p4_supply_sim"


def test_p5_manual_module_binding_and_feedback_review_are_persisted(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    design_input = _create_design_input_sim(client)
    supply_input = _create_supply_input_sim(client)
    created = client.post(
        "/api/software-build/orders",
        json={
            "design_input_id": design_input["design_input_id"],
            "requested_by": "P5",
            "notes": "最小闭环",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]
    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": design_input["design_input_id"],
            "supply_input_id": supply_input["supply_input_id"],
            "supply_mode": "snapshot",
            "confirmed_by": "P5",
        },
    )
    assert binding.status_code == 200

    rebound = client.post(
        f"/api/software-build/orders/{delivery_order_id}/module-bindings/module-feedback",
        json={
            "tool_id": "tool-ui-shell",
            "updated_by": "P5",
        },
    )

    assert rebound.status_code == 200
    assert rebound.json()["module_bindings"][0]["module_id"] == "module-feedback"

    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )

    assert attempt.status_code == 201
    payload = attempt.json()
    assert payload["assembly_plan"]["modules"][1]["binding_status"] == "bound"
    review = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts/{payload['attempt_id']}/feedback-tasks/{payload['feedback_tasks'][0]['task_id']}/review",
        json={
            "decision": "confirmed",
            "reviewed_by": "评审人",
            "review_note": "进入回流确认",
        },
    )
    assert review.status_code == 200
    assert review.json()["status"] == "confirmed"
    assert review.json()["reviewed_by"] == "评审人"


def test_p5_bootstrap_demo_creates_operable_minimal_loop(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    bootstrap = client.post(
        "/api/software-build/workspace/bootstrap-demo",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "demo",
            "attempt_note": "bootstrap-demo",
        },
    )

    assert bootstrap.status_code == 201
    payload = bootstrap.json()
    assert payload["delivery_order_id"].startswith("p5-order-")
    assert payload["attempt_id"].startswith("attempt-")
    assert payload["created_demo_inputs"] is True

    overview = client.get("/api/software-build/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["order_count"] == 1

    detail = client.get(f"/api/software-build/orders/{payload['delivery_order_id']}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["active_input_binding"]["is_confirmed"] is True
    assert detail_payload["attempts"][0]["input_snapshot"]["design_input"]["source_kind"] == "xx_p3_doc_sim"
    assert detail_payload["attempts"][0]["input_snapshot"]["supply_input"]["source_kind"] == "xx_p4_supply_sim"
    assert detail_payload["attempts"][0]["runtime_snapshot"]["progress_percent"] == 100
    assert detail_payload["attempts"][0]["output_preview"]["key_files"][-1]["path"] == "docs/gap-list.md"


def test_p5_order_detail_returns_attempt_history(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _seed_frozen_p3_order(tmp_path)
    created = client.post(
        "/api/software-build/orders",
        json={
            "p3_order_id": p3_order_id,
            "requested_by": "P5",
            "notes": "首轮组装",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]
    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": created.json()["active_input_binding"]["design_input_id"],
            "supply_mode": "empty",
            "confirmed_by": "P5",
        },
    )
    assert binding.status_code == 200
    client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )

    detail = client.get(f"/api/software-build/orders/{delivery_order_id}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["delivery_order_id"] == delivery_order_id
    assert payload["attempts"][0]["sequence"] == 1
    assert payload["active_input_binding"]["is_confirmed"] is True
    assert payload["attempts"][0]["gaps"][0]["kind"] == "supply_gap"
    assert payload["attempts"][0]["runtime_snapshot"]["recent_logs"][-1]["level"] == "warning"
    assert payload["attempts"][0]["output_preview"]["root_directory"].endswith("attempt-001")


def test_p5_testing_endpoint_can_clear_delivery_runtime_without_touching_input_sources(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    design_input = _create_design_input_sim(client)
    supply_input = _create_supply_input_sim(client)
    created = client.post(
        "/api/software-build/orders",
        json={
            "design_input_id": design_input["design_input_id"],
            "requested_by": "P5",
            "notes": "测试清空交付运行态",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]
    binding = client.post(
        f"/api/software-build/orders/{delivery_order_id}/binding/confirm",
        json={
            "design_input_id": design_input["design_input_id"],
            "supply_input_id": supply_input["supply_input_id"],
            "supply_mode": "snapshot",
            "confirmed_by": "P5",
        },
    )
    assert binding.status_code == 200
    attempt = client.post(
        f"/api/software-build/orders/{delivery_order_id}/attempts",
        json={
            "export_root": str(tmp_path / "exports"),
            "build_profile": "baseline",
            "attempt_note": "attempt-1",
        },
    )
    assert attempt.status_code == 201
    export_directory = Path(attempt.json()["export_directory"])
    assert export_directory.exists()

    clear_response = client.post("/api/software-build/testing/clear-deliveries")

    assert clear_response.status_code == 200
    assert clear_response.json() == {
        "cleared_order_count": 1,
        "cleared_attempt_count": 1,
        "cleared_export_directory_count": 1,
    }
    assert client.get("/api/software-build/orders").json()["data"]["items"] == []
    assert client.get("/api/software-build/overview").json()["data"]["metrics"]["order_count"] == 0
    assert client.get("/api/software-build/design-inputs").json()["data"]["items"][0]["design_input_id"] == design_input["design_input_id"]
    assert client.get("/api/software-build/supply-inputs").json()["data"]["items"][0]["supply_input_id"] == supply_input["supply_input_id"]
    assert not export_directory.exists()
