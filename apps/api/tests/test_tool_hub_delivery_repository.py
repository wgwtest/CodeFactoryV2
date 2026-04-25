from pathlib import Path

from sqlalchemy.orm import Session

from app.tool_hub.delivery_repository import ToolHubDeliveryRepository
from app.tool_hub.models import ToolArtifactVersion, ToolBuildRequest, ToolBuildRun, ToolValidationReport


def test_delivery_repository_persists_build_request_run_and_artifact(
    db_session: Session,
    tmp_path: Path,
) -> None:
    repository = ToolHubDeliveryRepository(db_session)

    build_request = ToolBuildRequest(
        build_request_id="build-req-1",
        tool_id="tool-query-table",
        request_type="frontend_component",
        requested_by="p3-sim",
        recipe_status="pending",
    )
    saved_request = repository.save_build_request(build_request)

    build_run = ToolBuildRun(
        build_run_id="build-run-1",
        build_request_id=saved_request.build_request_id,
        tool_id="tool-query-table",
        status="queued",
        queue_name="p4-build",
    )
    repository.save_build_run(build_run)

    artifact = ToolArtifactVersion(
        artifact_version_id="artifact-1",
        tool_id="tool-query-table",
        build_run_id="build-run-1",
        version_label="v1",
        artifact_root=str(tmp_path / "artifacts" / "artifact-1"),
        manifest_path="manifest.json",
        packaging_type="source_package",
        integration_mode="import_component",
    )
    report = ToolValidationReport(
        validation_report_id="report-1",
        build_run_id="build-run-1",
        overall_status="passed",
        checks=[{"name": "typecheck", "status": "passed"}],
    )

    repository.save_artifact_version(artifact)
    repository.save_validation_report(report)

    assert repository.get_build_request("build-req-1").tool_id == "tool-query-table"
    assert repository.get_build_run("build-run-1").status == "queued"
    assert repository.list_artifact_versions("tool-query-table")[0].integration_mode == "import_component"
    assert repository.get_validation_report("build-run-1").overall_status == "passed"
