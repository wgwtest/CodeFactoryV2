from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.p6 import service as p6_service


def _build_client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_p6_simulator_state() -> None:
    p6_service._SIMULATOR_SUBMISSION = None
    p6_service._SIMULATOR_HISTORY.clear()


def _build_display_contract(
    stage_id: str,
    stage_name: str,
    *,
    overall_key: str,
    overall_label: str,
    overall_value: int,
    input_target: str,
    output_target: str,
    terminal_output: bool = False,
    include_input_port: bool = True,
    extra_output_ports: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    flow_ports = []
    if include_input_port:
        flow_ports.append(
            {
                "port_id": f"{stage_id.lower()}_input",
                "side": "left",
                "direction": "input",
                "label": "输入",
                "connected_target": input_target,
                "current_rate": "7 项/小时",
                "terminal": False,
            }
        )
    flow_ports.append(
        {
            "port_id": f"{stage_id.lower()}_output",
            "side": "right",
            "direction": "output",
            "label": "输出",
            "connected_target": output_target,
            "current_rate": "5 项/小时",
            "terminal": terminal_output,
        }
    )
    flow_ports.extend(extra_output_ports or [])
    return {
        "contract_version": "P6DisplayExportContract.v2",
        "stage_overview": {
            "stage_id": stage_id,
            "stage_name": stage_name,
            "stage_display_name": stage_name,
            "primary_status": "running",
            "summary": f"{stage_name} 累计支撑 {overall_value} 个对象",
            "updated_at": "2026-04-29T20:50:00+08:00",
            "freshness": "fresh",
        },
        "entry_projection": {
            "entry_route": "/portal",
            "entry_available": True,
            "entry_reason": f"{stage_name} 入口可用",
        },
        "system_overall_metrics": [
            {
                "key": overall_key,
                "label": overall_label,
                "value": overall_value,
                "unit": "个",
                "basis": "累计承载",
            }
        ],
        "live_counters": [
            {
                "key": f"{stage_id.lower()}_active_input",
                "label": "正在接入",
                "value": 7,
                "unit": "项/小时",
                "window": "1h",
                "direction": "input",
            }
        ],
        "flow_ports": flow_ports,
        "connected_users": [
            {
                "user_ref": f"role:{stage_id.lower()}-operator",
                "display_label": stage_id,
                "role_label": "接入用户",
                "activity_state": "active",
                "connected_at": "2026-04-29T20:48:00+08:00",
            }
        ],
        "queue_projection": {
            "queue_id": f"{stage_id.lower()}-queue",
            "label": f"{stage_name} 队列",
            "items": [
                {"item_id": f"{stage_id.lower()}-q-001", "label": "队列项 A", "state": "active", "order_index": 0},
                {"item_id": f"{stage_id.lower()}-q-002", "label": "队列项 B", "state": "waiting", "order_index": 1},
            ],
            "active_index": 0,
            "advance_rule": "active_done_then_shift_left",
        },
        "display_binding": {
            "prototype_refs": [
                "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/"
            ],
            "regions": {
                "top_participants": "connected_users",
                "middle_overall": "system_overall_metrics",
                "lower_realtime": "live_counters",
                "left_input_port": "flow_ports[input]",
                "right_output_port": "flow_ports[output]",
                "bottom_queue": "queue_projection",
            },
        },
        "health_projection": {
            "health_level": "healthy",
            "health_message": f"{stage_name} 模拟合同已接入",
            "health_source": "p6_contract_simulator",
            "captured_at": "2026-04-29T20:50:00+08:00",
        },
        "source_trace": [
            {
                "field": f"system_overall_metrics.{overall_key}",
                "source_doc": f"DOC/CODEX_DOC/02_设计说明/{stage_id}_{stage_name}/{stage_id}-{stage_name}设计.md",
                "source_object": overall_label,
                "calculation_basis": "模拟器显式发送",
                "freshness_policy": "mock-fresh",
                "display_reason": "绑定详情卡中段总体状态",
            }
        ],
        "stage_specific": {overall_key: overall_value},
    }


def _build_simulator_contract_payload() -> dict[str, object]:
    return {
        "scenario_id": "simulator-latest",
        "label": "合同模拟器",
        "description": "由 P6 合同模拟器发送的五阶段展示输出合同。",
        "recommended_focus_stage": "P3",
        "contracts": [
            _build_display_contract(
                "P1",
                "业务知识库",
                overall_key="published_knowledge_count",
                overall_label="已发布知识",
                overall_value=12480,
                input_target="外部资料",
                output_target="P2",
                include_input_port=False,
            ),
            _build_display_contract(
                "P2",
                "需求分析系统",
                overall_key="supported_software_count",
                overall_label="支持软件",
                overall_value=24,
                input_target="P1",
                output_target="P3",
            ),
            _build_display_contract(
                "P3",
                "软件设计系统",
                overall_key="design_baseline_count",
                overall_label="设计基线",
                overall_value=112,
                input_target="P2",
                output_target="P4",
                extra_output_ports=[
                    {
                        "port_id": "p3_p5_baseline_output",
                        "side": "right",
                        "direction": "output",
                        "label": "设计基线",
                        "connected_target": "P5",
                        "current_rate": "3 份/小时",
                        "terminal": False,
                    }
                ],
            ),
            _build_display_contract(
                "P4",
                "工具仓库",
                overall_key="tool_definition_count",
                overall_label="工具定义",
                overall_value=286,
                input_target="P3",
                output_target="P5",
            ),
            _build_display_contract(
                "P5",
                "软件构建系统",
                overall_key="delivery_version_count",
                overall_label="交付版本",
                overall_value=86,
                input_target="P4",
                output_target="交付目录",
                terminal_output=True,
            ),
        ],
    }


def test_p6_mock_scenarios_expose_small_portal_control_options() -> None:
    client = _build_client()

    response = client.get("/api/p6/mock-scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_mode"] == "mock"
    assert payload["default_scenario_id"] == "baseline"
    assert [item["scenario_id"] for item in payload["items"]] == [
        "baseline",
        "review-pressure",
        "delivery-gap",
    ]
    assert payload["items"][1]["recommended_focus_stage"] == "P3"


def test_p6_stage_snapshots_return_baseline_stage_payloads() -> None:
    client = _build_client()

    response = client.get("/api/p6/stage-snapshots", params={"source": "mock", "scenario": "baseline"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_mode"] == "mock"
    assert payload["scenario"]["scenario_id"] == "baseline"
    assert len(payload["items"]) == 5
    assert [item["stage_id"] for item in payload["items"]] == ["P1", "P2", "P3", "P4", "P5"]

    p5_snapshot = next(item for item in payload["items"] if item["stage_id"] == "P5")
    assert p5_snapshot["node_status_payload"]["headline_value"] == "支持软件 24 个，交付版本 86 个，构建尝试 412 次"
    assert p5_snapshot["entry_projection"]["entry_route"] == "/build"
    assert p5_snapshot["health_projection"]["health_level"] == "healthy"


def test_p6_mock_stage_snapshots_expose_display_contract_v2_regions() -> None:
    client = _build_client()

    response = client.get("/api/p6/stage-snapshots", params={"source": "mock", "scenario": "baseline"})

    assert response.status_code == 200
    payload = response.json()
    p1_snapshot = next(item for item in payload["items"] if item["stage_id"] == "P1")
    p2_snapshot = next(item for item in payload["items"] if item["stage_id"] == "P2")
    p5_snapshot = next(item for item in payload["items"] if item["stage_id"] == "P5")

    p1_payload = p1_snapshot["node_status_payload"]
    assert p1_payload["contract_version"] == "P6DisplayExportContract.v2"
    p1_overall_keys = {item["key"] for item in p1_payload["system_overall_metric_items"]}
    assert {"knowledge_repository_count", "published_knowledge_count", "domain_directory_count", "contributor_count"}.issubset(
        p1_overall_keys
    )
    assert p1_payload["headline_value"] == "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人"
    assert p1_payload["connected_user_items"][0]["activity_state"] == "active"
    assert p1_payload["queue_projection"]["advance_rule"] == "active_done_then_shift_left"
    assert [port["connected_target"] for port in p1_payload["flow_port_items"] if port["direction"] == "output"] == ["P2"]

    p2_keys = {item["key"] for item in p2_snapshot["node_status_payload"]["system_overall_metric_items"]}
    assert "supported_software_count" in p2_keys
    assert "active_requirement_count" not in p2_keys

    p5_output = next(port for port in p5_snapshot["node_status_payload"]["flow_port_items"] if port["direction"] == "output")
    assert p5_output["connected_target"] == "交付目录"
    assert p5_output["terminal"] is True


def test_p6_contract_simulator_submission_drives_portal_projection() -> None:
    client = _build_client()

    create_response = client.post("/api/p6/simulator/contracts", json=_build_simulator_contract_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["scenario"]["scenario_id"] == "simulator-latest"
    assert created["accepted_contract_count"] == 5
    assert created["portal_data_path"] == "/portal-data?scenario=simulator-latest"

    catalog_response = client.get("/api/p6/mock-scenarios")
    assert catalog_response.status_code == 200
    assert "simulator-latest" in [item["scenario_id"] for item in catalog_response.json()["items"]]

    portal_response = client.get("/api/p6/portal-projection", params={"source": "mock", "scenario": "simulator-latest"})

    assert portal_response.status_code == 200
    projection = portal_response.json()["projection"]
    p2_node = next(item for item in projection["node_list"] if item["stage_id"] == "P2")
    p5_node = next(item for item in projection["node_list"] if item["stage_id"] == "P5")

    assert p2_node["stage_card"]["system_overall_metric_items"][0]["key"] == "supported_software_count"
    assert p2_node["stage_card"]["system_overall_metric_items"][0]["value"] == 24
    assert p2_node["stage_card"]["connected_user_items"][0]["display_label"] == "P2"
    p5_output = next(port for port in p5_node["stage_card"]["flow_port_items"] if port["direction"] == "output")
    assert p5_output["connected_target"] == "交付目录"
    assert p5_output["terminal"] is True


def test_p6_portal_data_view_returns_five_stage_table_without_generated_history() -> None:
    client = _build_client()

    response = client.get("/api/p6/portal-data", params={"source": "mock", "scenario": "baseline"})

    assert response.status_code == 200
    payload = response.json()
    view = payload["view"]

    assert payload["source_mode"] == "mock"
    assert payload["scenario"]["scenario_id"] == "baseline"
    assert view["scenario_summary"]["stage_count"] == 5
    assert view["scenario_summary"]["flow_count"] == 6
    assert view["history_sample_count"] == 0
    assert [row["stage_id"] for row in view["stage_rows"]] == ["P1", "P2", "P3", "P4", "P5"]
    assert view["stage_rows"][0]["overall_status"] == "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人"
    assert [series["flow_id"] for series in view["flow_series"]] == [
        "p1-p2",
        "p2-p3",
        "p3-p4",
        "p3-p5",
        "p4-p5",
        "p5-delivery",
    ]
    assert all(series["points"] == [] for series in view["flow_series"])
    assert view["selected_stage_detail"]["stage_id"] == "P3"
    assert view["selected_stage_detail"]["display_contract"]["contract_version"] == "P6DisplayExportContract.v2"


def test_p6_portal_data_view_uses_simulator_history_points_after_contract_submission() -> None:
    client = _build_client()

    create_response = client.post("/api/p6/simulator/contracts", json=_build_simulator_contract_payload())
    assert create_response.status_code == 201

    response = client.get("/api/p6/portal-data", params={"source": "mock", "scenario": "simulator-latest"})

    assert response.status_code == 200
    view = response.json()["view"]
    flow_points_by_id = {series["flow_id"]: series["points"] for series in view["flow_series"]}

    assert view["history_sample_count"] == 1
    assert set(flow_points_by_id) == {"p1-p2", "p2-p3", "p3-p4", "p3-p5", "p4-p5", "p5-delivery"}
    assert flow_points_by_id["p1-p2"][0]["payload_label"] == "发布态知识"
    assert flow_points_by_id["p1-p2"][0]["value"] == 5
    assert flow_points_by_id["p3-p5"][0]["payload_label"] == "设计基线"
    assert flow_points_by_id["p3-p5"][0]["value"] == 3
    assert flow_points_by_id["p5-delivery"][0]["to_stage_id"] == "交付目录"
    assert view["selected_stage_detail"]["stage_id"] == "P3"


def test_p6_portal_projection_returns_stage_and_participant_nodes() -> None:
    client = _build_client()

    response = client.get("/api/p6/portal-projection", params={"source": "mock", "scenario": "baseline"})

    assert response.status_code == 200
    payload = response.json()
    projection = payload["projection"]

    assert payload["scenario"]["scenario_id"] == "baseline"
    assert projection["freshness"] == "fresh"
    assert len(projection["node_list"]) == 5
    assert len(projection["flow_list"]) == 6
    assert projection["artifact_list"] == []
    assert [item["flow_id"] for item in projection["flow_list"]] == [
        "p1-p2",
        "p2-p3",
        "p3-p4",
        "p3-p5",
        "p4-p5",
        "p5-delivery",
    ]

    p1_node = next(item for item in projection["node_list"] if item["node_id"] == "p1")
    p3_node = next(item for item in projection["node_list"] if item["node_id"] == "p3")
    p5_node = next(item for item in projection["node_list"] if item["node_id"] == "p5")
    assert [port for port in p1_node["stage_card"]["flow_port_items"] if port["direction"] == "input"] == []
    assert [port["connected_target"] for port in p1_node["stage_card"]["flow_port_items"] if port["direction"] == "output"] == ["P2"]
    assert any(
        port["direction"] == "output" and port["connected_target"] == "P5" and port["label"] == "设计基线"
        for port in p3_node["stage_card"]["flow_port_items"]
    )
    assert any(
        port["direction"] == "input" and port["connected_target"] == "P3" and port["label"] == "设计基线"
        for port in p5_node["stage_card"]["flow_port_items"]
    )
    assert p3_node["stage_card"]["system_overall_metric_items"][1]["label"] == "设计基线"
    assert p3_node["route"] == "/p3-design-lab"


def test_p6_observation_projection_tracks_focus_stage_and_alerts() -> None:
    client = _build_client()

    response = client.get("/api/p6/observation-projection", params={"source": "mock", "scenario": "delivery-gap"})

    assert response.status_code == 200
    payload = response.json()
    projection = payload["projection"]

    assert payload["scenario"]["scenario_id"] == "delivery-gap"
    assert projection["focus_stage_id"] == "P5"
    assert projection["alert_summary"]["blocked_stage_ids"] == ["P5"]
    assert len(projection["stage_cards"]) == 5
    assert any(item["stage_id"] == "P5" and item["route_available"] for item in projection["route_actions"])


def test_platform_config_display_baseline_exposes_node_visual_rules() -> None:
    client = _build_client()

    response = client.get("/api/platform-config/display-baseline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "p6.3-v1"
    assert payload["token_set"]["token_set_id"] == "p6-platform-token-set"
    assert payload["stage_naming_baseline"]["stage_name_map"]["P3"] == "软件设计系统"
    assert payload["status_copy_baseline"]["platform_status_map"]["blocked"] == "阻塞中"
    assert payload["node_visual_baseline"]["system_stage_card_rules"]["required_fields"] == [
        "stage_identification",
        "primary_status",
        "summary",
        "core_metrics",
        "footer_status",
    ]
    assert payload["node_visual_baseline"]["participant_user_node_rules"]["shape"] == "capsule"
    assert payload["upgrade_rules"][0]["applies_to_scope"] == "platform_page"


def test_platform_config_routes_and_legend_are_available_for_portal_consumers() -> None:
    client = _build_client()

    routes_response = client.get("/api/platform-config/routes")
    legend_response = client.get("/api/platform-config/legend")

    assert routes_response.status_code == 200
    assert legend_response.status_code == 200

    routes_payload = routes_response.json()
    legend_payload = legend_response.json()

    assert routes_payload["portal_route"]["path"] == "/portal"
    assert routes_payload["observation_route"]["path"] == "/observation"
    assert routes_payload["stage_routes"]["P1"]["path"] == "/archives"
    assert routes_payload["stage_routes"]["P2"]["path"] == "/p2-requirement-analysis-lab"
    assert routes_payload["stage_routes"]["P3"]["path"] == "/p3-design-lab"
    assert routes_payload["stage_routes"]["P4"]["path"] == "/xx-p4"
    assert routes_payload["stage_routes"]["P5"]["path"] == "/build"
    assert legend_payload["summary_copy"] == "门户只负责导览与跳转，不承载业务编辑。双击节点即可进入对应模块。"
    assert legend_payload["signal_items"][2]["label"] == "模拟源驱动"
    assert legend_payload["roadmap_items"][0]["label"] == "统一登录接入"


def test_platform_display_workbench_bootstrap_exposes_templates_presets_records_and_candidates() -> None:
    client = _build_client()

    response = client.get("/api/platform-display/workbench")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "p6.4-v1"
    assert payload["templates"][0]["template_id"] == "template-module-status"
    assert payload["bindings"][0]["source_projection_kind"] == "PortalProjection"
    assert payload["layouts"][0]["layout_id"] == "layout-single"
    assert payload["presets"][0]["preset_id"] == "preset-portal-baseline"
    assert payload["experiments"][0]["experiment_id"] == "exp-portal-baseline"
    assert payload["promotion_candidates"][0]["candidate_kind"] == "template_preset"


def test_platform_display_experiment_creation_registers_record_and_promotion_candidate() -> None:
    client = _build_client()

    create_response = client.post(
        "/api/platform-display/experiments",
        json={
            "goal": "验证 P5 卡片在观察页中的告警优先展示。",
            "projection_scope": "ObservationProjection",
            "template_refs": ["template-module-compact"],
            "binding_refs": ["binding-observation-alert"],
            "layout_refs": ["layout-compare"],
            "preset_refs": ["preset-observation-alert"],
            "result_summary": "P5 阻塞态在观察页中更易被识别。",
            "issues": ["P4 与 P5 的视觉区分还需要增强。"],
            "promotion_recommendation": "candidate",
            "target_stage_ids": ["P4", "P5"],
            "evidence_refs": ["observation:delivery-gap", "baseline:node-visual-baseline"],
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["experiment_id"].startswith("exp-")
    assert created["promotion_recommendation"] == "candidate"

    experiments_response = client.get("/api/platform-display/experiments")
    candidates_response = client.get("/api/platform-display/promotion-candidates")

    assert experiments_response.status_code == 200
    assert candidates_response.status_code == 200

    experiments_payload = experiments_response.json()
    candidates_payload = candidates_response.json()

    assert any(item["experiment_id"] == created["experiment_id"] for item in experiments_payload["items"])
    assert any(item["source_experiment_id"] == created["experiment_id"] for item in candidates_payload["items"])


def test_p6_live_source_returns_explicit_not_implemented() -> None:
    client = _build_client()

    response = client.get("/api/p6/portal-projection", params={"source": "live", "scenario": "baseline"})

    assert response.status_code == 501
    assert response.json()["detail"] == "P6 live source is not implemented yet"


def test_p6_unknown_scenario_returns_404() -> None:
    client = _build_client()

    response = client.get("/api/p6/stage-snapshots", params={"source": "mock", "scenario": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "P6 mock scenario not found: missing"
