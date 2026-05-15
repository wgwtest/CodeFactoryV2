from __future__ import annotations

import hashlib
import json

from app.db.models.platform_exchange import PlatformExchangeArtifact, PlatformExchangeConsumption
from app.platform_exchange.models import ConsumeArtifactCommand, PublishArtifactCommand
from app.platform_exchange.repository import PlatformExchangeRepository


class PlatformExchangeService:
    STAGES = ("P1", "P2", "P3", "P4", "P5")
    EMPTY_STAGE_STATE = "暂无平台资源 / 暂无消费记录 / 未接入首版链路"

    def __init__(self, session) -> None:
        self.session = session
        self.repository = PlatformExchangeRepository(session)

    def publish_artifact(self, command: PublishArtifactCommand) -> dict:
        payload_hash = self._compute_payload_hash(command.payload)
        idempotency_key = self._build_idempotency_key(command=command, payload_hash=payload_hash)

        existing = self.repository.get_artifact_by_idempotency_key(idempotency_key)
        if existing is not None:
            return self.serialize_artifact(existing)

        same_version = self.repository.list_published_artifacts_by_source(
            artifact_type=command.artifact_type,
            producer_stage=command.producer_stage,
            producer_ref_id=command.producer_ref_id,
        )
        for artifact in same_version:
            if artifact.artifact_version == command.artifact_version and artifact.payload_hash != payload_hash:
                raise ValueError("artifact version conflict")

        for artifact in same_version:
            artifact.lifecycle_status = "superseded"
            self.repository.save_artifact(artifact)

        artifact = PlatformExchangeArtifact(
            artifact_type=command.artifact_type,
            artifact_version=command.artifact_version,
            schema_version=command.schema_version,
            producer_stage=command.producer_stage,
            producer_ref_id=command.producer_ref_id,
            producer_ref_type=command.producer_ref_type,
            lifecycle_status="published",
            payload_mode=command.payload_mode,
            payload=command.payload,
            payload_ref=command.payload_ref,
            payload_hash=payload_hash,
            parent_artifact_ids=command.parent_artifact_ids,
            source_trace=command.source_trace,
            idempotency_key=idempotency_key,
            frozen_at=command.frozen_at,
            published_by=command.published_by or "system",
        )
        return self.serialize_artifact(self.repository.add_artifact(artifact))

    def get_artifact(self, artifact_id: str) -> dict | None:
        artifact = self.repository.get_artifact(artifact_id)
        if artifact is None:
            return None
        return self.serialize_artifact(artifact)

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        producer_stage: str | None = None,
        lifecycle_status: str | None = None,
    ) -> dict:
        return {
            "items": [
                self.serialize_artifact(artifact)
                for artifact in self.repository.list_artifacts(
                    artifact_type=artifact_type,
                    producer_stage=producer_stage,
                    lifecycle_status=lifecycle_status,
                )
            ]
        }

    def consume_artifact(self, artifact_id: str, command: ConsumeArtifactCommand) -> dict:
        artifact = self.repository.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError("artifact not found")
        if artifact.lifecycle_status == "revoked":
            raise ValueError("artifact revoked")
        if artifact.schema_version != command.accepted_schema_version:
            raise ValueError("artifact schema version not accepted")

        consumption = PlatformExchangeConsumption(
            artifact_id=artifact_id,
            consumer_stage=command.consumer_stage,
            consumer_ref_id=command.consumer_ref_id,
            consumer_ref_type=command.consumer_ref_type,
            consumption_mode=command.consumption_mode,
            accepted_schema_version=command.accepted_schema_version,
            result_status=command.result_status,
            result_message=command.result_message,
        )
        return self.serialize_consumption(self.repository.add_consumption(consumption))

    def list_consumptions(self, *, artifact_id: str | None = None) -> dict:
        return {
            "items": [
                self.serialize_consumption(consumption)
                for consumption in self.repository.list_consumptions(artifact_id=artifact_id)
            ]
        }

    def get_monitor_snapshot(self) -> dict:
        artifacts = [self.serialize_artifact(artifact) for artifact in self.repository.list_artifacts()]
        consumptions = [self.serialize_consumption(consumption) for consumption in self.repository.list_consumptions()]

        stages = []
        for stage in self.STAGES:
            published = [artifact for artifact in artifacts if artifact["producer_stage"] == stage]
            consumed = [consumption for consumption in consumptions if consumption["consumer_stage"] == stage]
            stages.append(
                {
                    "stage": stage,
                    "published": published,
                    "consumed": consumed,
                    "empty_state": self.EMPTY_STAGE_STATE if not published and not consumed else None,
                }
            )

        return {
            "stages": stages,
            "base_platform": {
                "artifact_totals": {
                    "by_type": self._count_by(artifacts, "artifact_type"),
                    "by_producer_stage": self._count_by(artifacts, "producer_stage"),
                    "by_lifecycle_status": self._count_by(artifacts, "lifecycle_status"),
                },
                "consumption_totals": {
                    "by_consumer_stage": self._count_by(consumptions, "consumer_stage"),
                    "by_result_status": self._count_by(consumptions, "result_status"),
                },
                "latest_artifacts": artifacts[:5],
                "latest_consumptions": consumptions[:5],
            },
        }

    @staticmethod
    def serialize_artifact(artifact: PlatformExchangeArtifact) -> dict:
        return {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "artifact_version": artifact.artifact_version,
            "schema_version": artifact.schema_version,
            "producer_stage": artifact.producer_stage,
            "producer_ref_id": artifact.producer_ref_id,
            "producer_ref_type": artifact.producer_ref_type,
            "lifecycle_status": artifact.lifecycle_status,
            "payload_mode": artifact.payload_mode,
            "payload": artifact.payload,
            "payload_ref": artifact.payload_ref,
            "payload_hash": artifact.payload_hash,
            "parent_artifact_ids": artifact.parent_artifact_ids or [],
            "source_trace": artifact.source_trace or {},
            "idempotency_key": artifact.idempotency_key,
            "frozen_at": artifact.frozen_at,
            "published_at": artifact.published_at.isoformat(),
            "published_by": artifact.published_by,
            "created_at": artifact.created_at.isoformat(),
        }

    @staticmethod
    def serialize_consumption(consumption: PlatformExchangeConsumption) -> dict:
        return {
            "consumption_id": consumption.consumption_id,
            "artifact_id": consumption.artifact_id,
            "consumer_stage": consumption.consumer_stage,
            "consumer_ref_id": consumption.consumer_ref_id,
            "consumer_ref_type": consumption.consumer_ref_type,
            "consumption_mode": consumption.consumption_mode,
            "accepted_schema_version": consumption.accepted_schema_version,
            "result_status": consumption.result_status,
            "result_message": consumption.result_message,
            "consumed_at": consumption.consumed_at.isoformat(),
        }

    @staticmethod
    def _compute_payload_hash(payload: dict | None) -> str:
        normalized = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_idempotency_key(*, command: PublishArtifactCommand, payload_hash: str) -> str:
        return (
            f"{command.producer_stage}:"
            f"{command.artifact_type}:"
            f"{command.producer_ref_id}:"
            f"{command.artifact_version}:"
            f"{payload_hash}"
        )

    @staticmethod
    def _count_by(items: list[dict], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            value = item.get(field)
            if value is None:
                continue
            counts[str(value)] = counts.get(str(value), 0) + 1
        return counts
