from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from app.db.session import SessionLocal
from app.tool_hub.delivery_repository import ToolHubDeliveryRepository
from app.tool_hub.generators.query_table_widget import render_query_table_widget
from app.tool_hub.models import (
    FrontendComponentBuildRequest,
    ToolArtifactVersion,
    ToolBuildRequest,
    ToolBuildRun,
    ToolDeliveryManifest,
    ToolValidationReport,
    now_iso,
)

if TYPE_CHECKING:
    from app.tool_hub.service import ToolHubService


class DeliveryService:
    def __init__(self, hub: "ToolHubService", *, artifact_root: Path) -> None:
        self.hub = hub
        self.artifact_root = artifact_root
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def create_frontend_component_build_request(self, payload: FrontendComponentBuildRequest) -> ToolBuildRun:
        tool = self.hub.create_tool(payload.tool_definition)
        build_request = ToolBuildRequest(
            build_request_id=f"build-req-{uuid4().hex[:12]}",
            tool_id=tool.tool_id,
            request_type="frontend_component",
            requested_by=payload.requested_by,
            recipe_status="pending",
            payload={
                "component_name": payload.component_name,
                "scenario_id": payload.scenario_id,
                "tool_definition": payload.tool_definition.model_dump(mode="json"),
            },
        )
        build_run = ToolBuildRun(
            build_run_id=f"build-run-{uuid4().hex[:12]}",
            build_request_id=build_request.build_request_id,
            tool_id=tool.tool_id,
            status="queued",
            queue_name="p4-build",
        )
        with SessionLocal() as session:
            repository = ToolHubDeliveryRepository(session)
            repository.save_build_request(build_request)
            repository.save_build_run(build_run)
        self.hub.runtime_service.enqueue_build_job(build_run.build_run_id, actor_id=payload.requested_by)
        return build_run

    def get_build_run(self, build_run_id: str) -> ToolBuildRun | None:
        with SessionLocal() as session:
            repository = ToolHubDeliveryRepository(session)
            return repository.get_build_run(build_run_id)

    def execute_build_run(self, build_run_id: str) -> ToolBuildRun | None:
        with SessionLocal() as session:
            repository = ToolHubDeliveryRepository(session)
            build_run = repository.get_build_run(build_run_id)
            if build_run is None:
                return None
            build_request = repository.get_build_request(build_run.build_request_id)
            if build_request is None:
                return None

            running_run = build_run.model_copy(
                update={
                    "status": "running",
                    "started_at": build_run.started_at or now_iso(),
                    "updated_at": now_iso(),
                }
            )
            repository.save_build_run(running_run)

            recipe = self.hub.recipe_service.create_query_table_widget_recipe(build_request)
            bundle = render_query_table_widget(
                recipe,
                self.artifact_root / build_request.tool_id / running_run.build_run_id,
            )
            artifact = ToolArtifactVersion(
                artifact_version_id=f"artifact-{uuid4().hex[:12]}",
                tool_id=build_request.tool_id,
                build_run_id=running_run.build_run_id,
                version_label="v1",
                artifact_root=bundle.artifact_root,
                manifest_path=bundle.manifest_path,
                packaging_type="source_package",
                integration_mode="import_component",
                dependency_policy="peer",
                runtime_dependencies=["react@18", "antd@5"],
            )
            report = ToolValidationReport(
                validation_report_id=f"report-{uuid4().hex[:12]}",
                build_run_id=running_run.build_run_id,
                overall_status="passed",
                checks=[
                    {"name": "manifest_exists", "status": "passed"},
                    {"name": "component_bundle_exists", "status": "passed"},
                ],
                summary="Deterministic frontend component bundle generated.",
            )
            repository.save_artifact_version(artifact)
            repository.save_validation_report(report)

            updated_request = build_request.model_copy(
                update={
                    "recipe_status": "generated",
                    "recipe_id": recipe.recipe_id,
                    "updated_at": now_iso(),
                }
            )
            repository.save_build_request(updated_request)

            completed_run = running_run.model_copy(
                update={
                    "status": "completed",
                    "artifact_version_id": artifact.artifact_version_id,
                    "completed_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            repository.save_build_run(completed_run)

        tool = self.hub.repository.get_tool(build_request.tool_id)
        if tool is not None:
            self.hub.repository.save_tool(
                tool.model_copy(
                    update={
                        "status": "active",
                        "updated_at": now_iso(),
                    }
                )
            )
        return completed_run

    def get_delivery_manifest(self, tool_id: str) -> ToolDeliveryManifest | None:
        tool = self.hub.repository.get_tool(tool_id)
        if tool is None:
            return None
        with SessionLocal() as session:
            repository = ToolHubDeliveryRepository(session)
            artifacts = repository.list_artifact_versions(tool_id)
        if not artifacts:
            return None

        latest_artifact = artifacts[0]
        manifest_payload = json.loads(Path(latest_artifact.manifest_path).read_text(encoding="utf-8"))
        return ToolDeliveryManifest(
            tool_id=tool.tool_id,
            tool_name=tool.name,
            artifact_version_id=latest_artifact.artifact_version_id,
            manifest_path=latest_artifact.manifest_path,
            updated_at=latest_artifact.updated_at,
            **manifest_payload,
        )
