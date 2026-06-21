from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from app.db.models.stage_artifacts import StageWorkArtifactRecord
from app.platform_exchange.models import PublishArtifactCommand
from app.platform_exchange.service import PlatformExchangeService
from app.stage_artifacts.models import (
    StageArtifactCurrentCommand,
    StageArtifactPublishCommand,
    StageArtifactSnapshotCommand,
)
from app.stage_artifacts.repository import StageArtifactRepository


class StageArtifactService:
    IMMUTABLE_STATUSES = {"snapshot", "frozen", "published", "superseded"}

    def __init__(self, session) -> None:
        self.session = session
        self.repository = StageArtifactRepository(session)
        self.platform_exchange_service = PlatformExchangeService(session)

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
    ) -> dict:
        return {
            "items": [
                self.serialize_artifact(artifact)
                for artifact in self.repository.list_artifacts(
                    owner_user_id=owner_user_id,
                    producer_stage=producer_stage,
                    artifact_type=artifact_type,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    lifecycle_status=lifecycle_status,
                    parent_artifact_id=parent_artifact_id,
                )
            ]
        }

    def get_artifact(self, artifact_id: str) -> dict | None:
        artifact = self.repository.get_artifact(artifact_id)
        if artifact is None:
            return None
        return self.serialize_artifact(artifact)

    def upsert_current_artifact(self, command: StageArtifactCurrentCommand) -> dict:
        payload_hash = self.compute_payload_hash(command.payload)
        existing = (
            self.repository.get_artifact(command.artifact_id)
            if command.artifact_id
            else self.repository.get_current_artifact(
                owner_user_id=command.owner_user_id,
                producer_stage=command.producer_stage,
                artifact_type=command.artifact_type,
                scope_type=command.scope_type,
                scope_id=command.scope_id,
            )
        )

        now = datetime.now(UTC)
        if existing is None:
            artifact_values = {
                "owner_user_id": command.owner_user_id,
                "producer_stage": command.producer_stage,
                "artifact_type": command.artifact_type,
                "artifact_version": command.artifact_version,
                "schema_version": command.schema_version,
                "scope_type": command.scope_type,
                "scope_id": command.scope_id,
                "source_artifact_ids": list(command.source_artifact_ids),
                "lifecycle_status": command.lifecycle_status,
                "payload_mode": command.payload_mode,
                "payload": command.payload,
                "payload_ref": command.payload_ref,
                "payload_hash": payload_hash,
                "parent_artifact_id": command.parent_artifact_id,
                "source_trace": command.source_trace,
                "created_at": now,
                "updated_at": now,
            }
            if command.artifact_id:
                artifact_values["artifact_id"] = command.artifact_id
            artifact = StageWorkArtifactRecord(**artifact_values)
            return self.serialize_artifact(self.repository.add_artifact(artifact))

        if existing.lifecycle_status in self.IMMUTABLE_STATUSES:
            raise ValueError(f"{existing.lifecycle_status} stage artifact cannot be overwritten")

        existing.owner_user_id = command.owner_user_id
        existing.producer_stage = command.producer_stage
        existing.artifact_type = command.artifact_type
        existing.artifact_version = command.artifact_version
        existing.schema_version = command.schema_version
        existing.scope_type = command.scope_type
        existing.scope_id = command.scope_id
        existing.source_artifact_ids = list(command.source_artifact_ids)
        existing.lifecycle_status = command.lifecycle_status
        existing.payload_mode = command.payload_mode
        existing.payload = command.payload
        existing.payload_ref = command.payload_ref
        existing.payload_hash = payload_hash
        existing.parent_artifact_id = command.parent_artifact_id
        existing.source_trace = command.source_trace
        existing.updated_at = now
        return self.serialize_artifact(self.repository.save_artifact(existing))

    def create_snapshot(self, artifact_id: str, command: StageArtifactSnapshotCommand) -> dict:
        parent = self.repository.get_artifact(artifact_id)
        if parent is None:
            raise ValueError("stage artifact not found")
        now = datetime.now(UTC)
        source_trace = dict(parent.source_trace or {})
        if command.source_trace:
            source_trace.update(command.source_trace)
        source_trace.setdefault("parent_artifact_id", parent.artifact_id)
        snapshot = StageWorkArtifactRecord(
            owner_user_id=parent.owner_user_id,
            producer_stage=parent.producer_stage,
            artifact_type=command.artifact_type or parent.artifact_type,
            artifact_version=command.artifact_version or parent.artifact_version,
            schema_version=command.schema_version or parent.schema_version,
            scope_type=parent.scope_type,
            scope_id=parent.scope_id,
            source_artifact_ids=list(parent.source_artifact_ids or []),
            lifecycle_status=command.lifecycle_status,
            payload_mode=parent.payload_mode,
            payload=parent.payload or {},
            payload_ref=parent.payload_ref,
            payload_hash=parent.payload_hash,
            parent_artifact_id=parent.artifact_id,
            source_trace=source_trace,
            created_at=now,
            updated_at=now,
        )
        return self.serialize_artifact(self.repository.add_artifact(snapshot))

    def freeze_artifact(self, artifact_id: str) -> dict:
        artifact = self.repository.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError("stage artifact not found")
        if artifact.lifecycle_status == "published":
            raise ValueError("published stage artifact cannot be frozen")
        if artifact.lifecycle_status != "frozen":
            artifact.lifecycle_status = "frozen"
            artifact.frozen_at = datetime.now(UTC)
            artifact.updated_at = artifact.frozen_at
            artifact = self.repository.save_artifact(artifact)
        return self.serialize_artifact(artifact)

    def publish_artifact(self, artifact_id: str, command: StageArtifactPublishCommand) -> dict:
        artifact = self.repository.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError("stage artifact not found")
        if artifact.lifecycle_status not in {"snapshot", "frozen"}:
            raise ValueError("only snapshot or frozen stage artifacts can be published")

        published = self.platform_exchange_service.publish_artifact(
            PublishArtifactCommand(
                artifact_type=command.artifact_type or artifact.artifact_type,
                artifact_version=command.artifact_version or artifact.artifact_version,
                schema_version=command.schema_version or artifact.schema_version,
                producer_stage=artifact.producer_stage,
                producer_ref_id=artifact.artifact_id,
                producer_ref_type="StageWorkArtifact",
                payload_mode=artifact.payload_mode,
                payload=artifact.payload,
                payload_ref=artifact.payload_ref,
                parent_artifact_ids=[parent_id for parent_id in [artifact.parent_artifact_id] if parent_id],
                source_trace=artifact.source_trace or {},
                frozen_at=artifact.frozen_at.isoformat() if artifact.frozen_at else None,
                published_by=command.published_by,
            )
        )
        artifact.lifecycle_status = "published"
        artifact.published_artifact_id = published["artifact_id"]
        artifact.updated_at = datetime.now(UTC)
        self.repository.save_artifact(artifact)
        return {"stage_artifact": self.serialize_artifact(artifact), "platform_artifact": published}

    @staticmethod
    def serialize_artifact(artifact: StageWorkArtifactRecord) -> dict:
        return {
            "artifact_id": artifact.artifact_id,
            "owner_user_id": artifact.owner_user_id,
            "producer_stage": artifact.producer_stage,
            "artifact_type": artifact.artifact_type,
            "artifact_version": artifact.artifact_version,
            "schema_version": artifact.schema_version,
            "scope_type": artifact.scope_type,
            "scope_id": artifact.scope_id,
            "source_artifact_ids": artifact.source_artifact_ids or [],
            "lifecycle_status": artifact.lifecycle_status,
            "payload_mode": artifact.payload_mode,
            "payload": artifact.payload or {},
            "payload_ref": artifact.payload_ref,
            "payload_hash": artifact.payload_hash,
            "parent_artifact_id": artifact.parent_artifact_id,
            "source_trace": artifact.source_trace or {},
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat(),
            "frozen_at": artifact.frozen_at.isoformat() if artifact.frozen_at else None,
            "published_artifact_id": artifact.published_artifact_id,
        }

    @staticmethod
    def compute_payload_hash(payload: dict | None) -> str:
        normalized = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
