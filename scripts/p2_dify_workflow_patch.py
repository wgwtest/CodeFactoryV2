#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


DEFAULT_APP_ID = "e5444ba7-7134-4f0d-9258-fbd5f162e4f1"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_node(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in graph.get("nodes") or []:
        if isinstance(node, dict) and node.get("id") == node_id:
            return node
    raise SystemExit(f"node not found in workflow graph: {node_id}")


def _login(client: httpx.Client, *, base_url: str, email: str, password: str) -> None:
    encoded_password = base64.b64encode(password.encode("utf-8")).decode("ascii")
    response = client.post(
        f"{base_url}/console/api/login",
        json={"email": email, "password": encoded_password, "remember_me": True},
    )
    response.raise_for_status()


def _get_draft(client: httpx.Client, *, base_url: str, app_id: str) -> dict[str, Any]:
    response = client.get(f"{base_url}/console/api/apps/{app_id}/workflows/draft")
    response.raise_for_status()
    return response.json()


def _sync_draft(
    client: httpx.Client,
    *,
    base_url: str,
    app_id: str,
    draft: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        f"{base_url}/console/api/apps/{app_id}/workflows/draft",
        json={
            "graph": graph,
            "features": draft.get("features") or {},
            "hash": draft.get("hash") or draft.get("unique_hash"),
            "environment_variables": draft.get("environment_variables") or [],
            "conversation_variables": draft.get("conversation_variables") or [],
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"sync draft failed: {response.status_code} {response.text}")
    response.raise_for_status()
    return response.json()


def _publish(client: httpx.Client, *, base_url: str, app_id: str, title: str, release_notes: str) -> dict[str, Any]:
    csrf_token = client.cookies.get("csrf_token") or client.cookies.get("__Host-csrf_token") or ""
    response = client.post(
        f"{base_url}/console/api/apps/{app_id}/workflows/publish",
        headers={"X-CSRF-Token": csrf_token} if csrf_token else None,
        json={"marked_name": title, "marked_comment": release_notes},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"publish workflow failed: {response.status_code} {response.text}")
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch and publish the P2 Brainstorm v1 Dify workflow draft.")
    parser.add_argument("--base-url", default=os.environ.get("DIFY_CONSOLE_BASE_URL", "http://localhost").rstrip("/"))
    parser.add_argument("--app-id", default=os.environ.get("DIFY_CONSOLE_APP_ID", DEFAULT_APP_ID))
    parser.add_argument("--document-projection-code", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, default=Path(".run-logs"))
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--title", default="P2 round1 anchor projection remediation")
    parser.add_argument(
        "--release-notes",
        default="Align document_projection with current 81433 template anchors and split nonfunctional projections.",
    )
    args = parser.parse_args()

    email = _require_env("DIFY_CONSOLE_EMAIL")
    password = _require_env("DIFY_CONSOLE_PASSWORD")
    document_projection_code = _read_text(args.document_projection_code)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False) as client:
        _login(client, base_url=args.base_url, email=email, password=password)
        draft = _get_draft(client, base_url=args.base_url, app_id=args.app_id)
        backup_path = args.backup_dir / f"dify-brainstorm-v1-draft-before-patch-{timestamp}.json"
        _write_json(backup_path, draft)

        graph = dict(draft.get("graph") or {})
        node = _find_node(graph, "document_projection")
        node_data = node.setdefault("data", {})
        old_code = str(node_data.get("code") or "")
        node_data["code"] = document_projection_code

        sync_result = _sync_draft(client, base_url=args.base_url, app_id=args.app_id, draft=draft, graph=graph)
        result: dict[str, Any] = {
            "backup_path": str(backup_path),
            "old_document_projection_code_chars": len(old_code),
            "new_document_projection_code_chars": len(document_projection_code),
            "sync_result": sync_result,
        }
        if args.publish:
            result["publish_result"] = _publish(
                client,
                base_url=args.base_url,
                app_id=args.app_id,
                title=args.title,
                release_notes=args.release_notes,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
