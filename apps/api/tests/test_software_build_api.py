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

    overview = client.get("/api/software-build/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["metrics"]["order_count"] == 1


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


def test_p5_attempt_marks_supply_hits_and_pending_feedback(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    p3_order_id = _seed_frozen_p3_order(
        tmp_path,
        module_specs=[
            {
                "module_id": "module-planning",
                "name": "规划任务管理",
                "objective": "围绕规划任务实现核心流程。",
                "inputs": ["planning_request"],
                "outputs": ["planning_task"],
                "constraints": ["关键状态变更需留痕"],
                "recommended_tools": ["workflow_engine"],
            },
            {
                "module_id": "module-reporting",
                "name": "规划结果回流",
                "objective": "沉淀交付缺口和回流建议。",
                "inputs": ["planning_task"],
                "outputs": ["feedback_task"],
                "constraints": ["问题回流需可追踪"],
                "recommended_tools": ["gap_reporter"],
            },
        ],
    )
    _seed_tool_hub_tool(
        tmp_path,
        tool_id="tool-workflow-engine",
        slug="workflow-engine",
        keywords=["workflow_engine", "planning"],
    )
    created = client.post(
        "/api/software-build/orders",
        json={
            "p3_order_id": p3_order_id,
            "requested_by": "P5",
            "notes": "首轮组装",
        },
    )
    delivery_order_id = created.json()["delivery_order_id"]

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
    assert payload["feedback_tasks"][0]["status"] == "pending_confirmation"


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
    assert detail_payload["attempts"][0]["input_snapshot"]["design_input"]["source_kind"] == "demo_p3_baseline"
    assert detail_payload["attempts"][0]["input_snapshot"]["supply_input"]["source_kind"] == "demo_p4_supply"
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
    assert payload["attempts"][0]["gaps"][0]["kind"] == "supply_gap"
    assert payload["attempts"][0]["runtime_snapshot"]["recent_logs"][-1]["level"] == "warning"
    assert payload["attempts"][0]["output_preview"]["root_directory"].endswith("attempt-001")
