from __future__ import annotations

from sqlalchemy import select

from app.db.models.platform_exchange import PlatformExchangeArtifact, PlatformExchangeConsumption


class PlatformExchangeRepository:
    def __init__(self, session) -> None:
        self.session = session

    def add_artifact(self, artifact: PlatformExchangeArtifact) -> PlatformExchangeArtifact:
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def save_artifact(self, artifact: PlatformExchangeArtifact) -> PlatformExchangeArtifact:
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def get_artifact(self, artifact_id: str) -> PlatformExchangeArtifact | None:
        return self.session.get(PlatformExchangeArtifact, artifact_id)

    def get_artifact_by_idempotency_key(self, idempotency_key: str) -> PlatformExchangeArtifact | None:
        return self.session.scalar(
            select(PlatformExchangeArtifact).where(PlatformExchangeArtifact.idempotency_key == idempotency_key)
        )

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        producer_stage: str | None = None,
        lifecycle_status: str | None = None,
    ) -> list[PlatformExchangeArtifact]:
        stmt = select(PlatformExchangeArtifact).order_by(PlatformExchangeArtifact.published_at.desc())
        if artifact_type is not None:
            stmt = stmt.where(PlatformExchangeArtifact.artifact_type == artifact_type)
        if producer_stage is not None:
            stmt = stmt.where(PlatformExchangeArtifact.producer_stage == producer_stage)
        if lifecycle_status is not None:
            stmt = stmt.where(PlatformExchangeArtifact.lifecycle_status == lifecycle_status)
        return self.session.scalars(stmt).all()

    def list_published_artifacts_by_source(
        self,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_ref_id: str,
    ) -> list[PlatformExchangeArtifact]:
        return self.session.scalars(
            select(PlatformExchangeArtifact)
            .where(PlatformExchangeArtifact.artifact_type == artifact_type)
            .where(PlatformExchangeArtifact.producer_stage == producer_stage)
            .where(PlatformExchangeArtifact.producer_ref_id == producer_ref_id)
            .where(PlatformExchangeArtifact.lifecycle_status == "published")
            .order_by(PlatformExchangeArtifact.published_at.desc())
        ).all()

    def add_consumption(self, consumption: PlatformExchangeConsumption) -> PlatformExchangeConsumption:
        self.session.add(consumption)
        self.session.commit()
        self.session.refresh(consumption)
        return consumption

    def list_consumptions(self, *, artifact_id: str | None = None) -> list[PlatformExchangeConsumption]:
        stmt = select(PlatformExchangeConsumption).order_by(PlatformExchangeConsumption.consumed_at.desc())
        if artifact_id is not None:
            stmt = stmt.where(PlatformExchangeConsumption.artifact_id == artifact_id)
        return self.session.scalars(stmt).all()
