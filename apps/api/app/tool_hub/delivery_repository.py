from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.tool_hub_delivery import (
    ToolArtifactVersionRecord,
    ToolBuildRequestRecord,
    ToolBuildRunRecord,
    ToolValidationReportRecord,
)
from app.tool_hub.models import ToolArtifactVersion, ToolBuildRequest, ToolBuildRun, ToolValidationReport


class ToolHubDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_build_request(self, build_request: ToolBuildRequest) -> ToolBuildRequest:
        record = ToolBuildRequestRecord(
            id=build_request.build_request_id,
            tool_id=build_request.tool_id,
            request_type=build_request.request_type,
            requested_by=build_request.requested_by,
            recipe_status=build_request.recipe_status,
            payload=build_request.model_dump(mode="json"),
        )
        self.session.merge(record)
        self.session.commit()
        return build_request

    def get_build_request(self, build_request_id: str) -> ToolBuildRequest | None:
        record = self.session.get(ToolBuildRequestRecord, build_request_id)
        if record is None:
            return None
        return ToolBuildRequest.model_validate(record.payload)

    def save_build_run(self, build_run: ToolBuildRun) -> ToolBuildRun:
        record = ToolBuildRunRecord(
            id=build_run.build_run_id,
            build_request_id=build_run.build_request_id,
            tool_id=build_run.tool_id,
            status=build_run.status,
            queue_name=build_run.queue_name,
            payload=build_run.model_dump(mode="json"),
        )
        self.session.merge(record)
        self.session.commit()
        return build_run

    def get_build_run(self, build_run_id: str) -> ToolBuildRun | None:
        record = self.session.get(ToolBuildRunRecord, build_run_id)
        if record is None:
            return None
        return ToolBuildRun.model_validate(record.payload)

    def save_artifact_version(self, artifact: ToolArtifactVersion) -> ToolArtifactVersion:
        record = ToolArtifactVersionRecord(
            id=artifact.artifact_version_id,
            tool_id=artifact.tool_id,
            build_run_id=artifact.build_run_id,
            version_label=artifact.version_label,
            artifact_root=artifact.artifact_root,
            manifest_path=artifact.manifest_path,
            packaging_type=artifact.packaging_type,
            integration_mode=artifact.integration_mode,
            payload=artifact.model_dump(mode="json"),
        )
        self.session.merge(record)
        self.session.commit()
        return artifact

    def list_artifact_versions(self, tool_id: str) -> list[ToolArtifactVersion]:
        records = (
            self.session.query(ToolArtifactVersionRecord)
            .filter(ToolArtifactVersionRecord.tool_id == tool_id)
            .order_by(ToolArtifactVersionRecord.created_at.desc())
            .all()
        )
        return [ToolArtifactVersion.model_validate(record.payload) for record in records]

    def save_validation_report(self, report: ToolValidationReport) -> ToolValidationReport:
        record = ToolValidationReportRecord(
            id=report.validation_report_id,
            build_run_id=report.build_run_id,
            overall_status=report.overall_status,
            payload=report.model_dump(mode="json"),
        )
        self.session.merge(record)
        self.session.commit()
        return report

    def get_validation_report(self, build_run_id: str) -> ToolValidationReport | None:
        record = (
            self.session.query(ToolValidationReportRecord)
            .filter(ToolValidationReportRecord.build_run_id == build_run_id)
            .one_or_none()
        )
        if record is None:
            return None
        return ToolValidationReport.model_validate(record.payload)
