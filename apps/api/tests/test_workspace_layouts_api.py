from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _layout_payload(scale: float) -> dict:
    return {
        "activeWindowId": "software-design",
        "viewport": {"x": 120, "y": -40, "scale": scale},
        "stageLayouts": {
            "software-design": {"x": 80, "y": 160, "width": 720, "height": 480, "collapsed": False}
        },
        "designSessionId": "p3dl-1",
        "stageSignature": "requirement|conversion|software-design|projection",
    }


def _create_named_layout(client: TestClient, *, name: str, scale: float, is_default: bool = False) -> dict:
    response = client.post(
        "/api/workspace-layouts",
        json={
            "owner_user_id": "default",
            "scope_type": "p3_design_session",
            "scope_id": "p3dl-1",
            "layout_kind": "p3_design_morph_canvas@1",
            "layout_role": "named_snapshot",
            "name": name,
            "is_default": is_default,
            "payload_schema_version": "p3_design_morph_canvas.v1",
            "payload": _layout_payload(scale),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_workspace_layouts_persist_query_upsert_default_and_delete() -> None:
    client = TestClient(create_app())

    list_url = (
        "/api/workspace-layouts"
        "?scope_type=p3_design_session&scope_id=p3dl-1&layout_kind=p3_design_morph_canvas@1"
    )
    assert client.get(list_url).json() == {"items": []}

    first = _create_named_layout(client, name="软设工作区布局 A", scale=1.1, is_default=True)
    assert first["layout_id"].startswith("wsl-")
    assert first["layout_role"] == "named_snapshot"
    assert first["is_default"] is True
    assert first["payload"]["viewport"]["scale"] == 1.1

    current = client.put(
        "/api/workspace-layouts/current",
        json={
            "owner_user_id": "default",
            "scope_type": "p3_design_session",
            "scope_id": "p3dl-1",
            "layout_kind": "p3_design_morph_canvas@1",
            "name": "当前布局",
            "payload_schema_version": "p3_design_morph_canvas.v1",
            "payload": _layout_payload(1.4),
        },
    )
    assert current.status_code == 200
    current_layout = current.json()
    assert current_layout["layout_role"] == "current_auto"
    assert current_layout["payload"]["viewport"]["scale"] == 1.4

    current_update = client.put(
        "/api/workspace-layouts/current",
        json={
            "owner_user_id": "default",
            "scope_type": "p3_design_session",
            "scope_id": "p3dl-1",
            "layout_kind": "p3_design_morph_canvas@1",
            "name": "当前布局",
            "payload_schema_version": "p3_design_morph_canvas.v1",
            "payload": _layout_payload(1.8),
        },
    )
    assert current_update.status_code == 200
    assert current_update.json()["layout_id"] == current_layout["layout_id"]
    assert current_update.json()["payload"]["viewport"]["scale"] == 1.8

    second = _create_named_layout(client, name="软设工作区布局 B", scale=0.9)
    default_response = client.post(f"/api/workspace-layouts/{second['layout_id']}/default")
    assert default_response.status_code == 200
    assert default_response.json()["is_default"] is True

    listed = client.get(list_url).json()["items"]
    assert len([item for item in listed if item["layout_role"] == "current_auto"]) == 1
    assert [item["layout_id"] for item in listed if item["is_default"]] == [second["layout_id"]]

    delete_response = client.delete(f"/api/workspace-layouts/{first['layout_id']}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted_layout_id": first["layout_id"]}
    assert client.get(f"/api/workspace-layouts/{first['layout_id']}").status_code == 404
