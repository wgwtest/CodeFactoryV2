from fastapi.testclient import TestClient

from app.main import create_app


def _build_client() -> TestClient:
    return TestClient(create_app())


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
    assert p5_snapshot["node_status_payload"]["headline_value"] == "交付主单 DO-240421-01"
    assert p5_snapshot["entry_projection"]["entry_route"] == "/build"
    assert p5_snapshot["health_projection"]["health_level"] == "healthy"


def test_p6_portal_projection_returns_stage_and_participant_nodes() -> None:
    client = _build_client()

    response = client.get("/api/p6/portal-projection", params={"source": "mock", "scenario": "baseline"})

    assert response.status_code == 200
    payload = response.json()
    projection = payload["projection"]

    assert payload["scenario"]["scenario_id"] == "baseline"
    assert projection["freshness"] == "fresh"
    assert len(projection["node_list"]) == 6
    assert len(projection["flow_list"]) == 6
    assert len(projection["artifact_list"]) == 3

    user_node = next(item for item in projection["node_list"] if item["node_id"] == "user")
    assert user_node["node_kind"] == "user"
    assert user_node["participant_payload"]["title"] == "行业用户"

    p3_node = next(item for item in projection["node_list"] if item["node_id"] == "p3")
    assert p3_node["stage_card"]["metric_items"][1]["metric_label"] == "待评审"
    assert p3_node["route"] == "/modeling"


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
    assert routes_payload["stage_routes"]["P5"]["path"] == "/build"
    assert legend_payload["summary_copy"] == "门户只负责导览与跳转，不承载业务编辑。双击节点即可进入对应模块。"
    assert legend_payload["signal_items"][2]["label"] == "设计转化"
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
