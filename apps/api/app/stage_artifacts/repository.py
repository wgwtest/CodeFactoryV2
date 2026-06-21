from __future__ import annotations

from sqlalchemy import select

from app.db.models.stage_artifacts import StageWorkArtifactRecord


class StageArtifactRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add_artifact(self, artifact: StageWorkArtifactRecord) -> StageWorkArtifactRecord:
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def save_artifact(self, artifact: StageWorkArtifactRecord) -> StageWorkArtifactRecord:
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def get_artifact(self, artifact_id: str) -> StageWorkArtifactRecord | None:
        return self.session.get(StageWorkArtifactRecord, artifact_id)

    def get_current_artifact(
        self,
        *,
        owner_user_id: str,
        producer_stage: str,
        artifact_type: str,
        scope_type: str,
        scope_id: str,
    ) -> StageWorkArtifactRecord | None:
        return self.session.scalar(
            select(StageWorkArtifactRecord)
            .where(StageWorkArtifactRecord.owner_user_id == owner_user_id)
            .where(StageWorkArtifactRecord.producer_stage == producer_stage)
            .where(StageWorkArtifactRecord.artifact_type == artifact_type)
            .where(StageWorkArtifactRecord.scope_type == scope_type)
            .where(StageWorkArtifactRecord.scope_id == scope_id)
            .where(StageWorkArtifactRecord.lifecycle_status.notin_(["snapshot", "frozen", "published", "deleted"]))
            .order_by(StageWorkArtifactRecord.updated_at.desc())
        )

    def list_artifacts(
        self,
        *,
        owner_user_id: str | None = None,
        producer_stage: str | None = None,
        artifact_type: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        lifecycle_status: str | None = None,
        parent_artifact_id: str | None = None,
    ) -> list[StageWorkArtifactRecord]:
        stmt = select(StageWorkArtifactRecord).order_by(StageWorkArtifactRecord.updated_at.desc())
        if owner_user_id is not None:
            stmt = stmt.where(StageWorkArtifactRecord.owner_user_id == owner_user_id)
        if producer_stage is not None:
            stmt = stmt.where(StageWorkArtifactRecord.producer_stage == producer_stage)
        if artifact_type is not None:
            stmt = stmt.where(StageWorkArtifactRecord.artifact_type == artifact_type)
        if scope_type is not None:
            stmt = stmt.where(StageWorkArtifactRecord.scope_type == scope_type)
        if scope_id is not None:
            stmt = stmt.where(StageWorkArtifactRecord.scope_id == scope_id)
        if lifecycle_status is not None:
            stmt = stmt.where(StageWorkArtifactRecord.lifecycle_status == lifecycle_status)
        if parent_artifact_id is not None:
            stmt = stmt.where(StageWorkArtifactRecord.parent_artifact_id == parent_artifact_id)
        return self.session.scalars(stmt).all()
