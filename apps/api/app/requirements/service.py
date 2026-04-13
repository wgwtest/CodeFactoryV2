from __future__ import annotations

from typing import Literal

from sqlalchemy import select

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.db.models.requirements import RequirementSpec
from app.requirements.schemas import RequirementSpecWrite


class RequirementSpecService:
    def __init__(self, session) -> None:
        self.session = session

    def list_specs(self) -> list[dict]:
        specs = self.session.scalars(select(RequirementSpec).order_by(RequirementSpec.updated_at.desc())).all()
        return [self._serialize_summary(spec) for spec in specs]

    def get_spec(self, spec_id: str) -> dict | None:
        spec = self.session.get(RequirementSpec, spec_id)
        if spec is None:
            return None
        return self._serialize_detail(spec)

    def create_spec(self, request: RequirementSpecWrite) -> dict:
        payload = request.payload.model_dump(mode="json")
        spec = RequirementSpec(
            application_name=self._normalize_application_name(payload["application"].get("name", "")),
            domain_name=payload["application"].get("domain", "").strip(),
            archive_id=(request.archive_id or settings.default_archive_id).strip(),
            status=request.status,
            payload=payload,
        )
        self.session.add(spec)
        self.session.commit()
        self.session.refresh(spec)
        return self._serialize_detail(spec)

    def update_spec(self, spec_id: str, request: RequirementSpecWrite) -> dict | None:
        spec = self.session.get(RequirementSpec, spec_id)
        if spec is None:
            return None

        payload = request.payload.model_dump(mode="json")
        spec.application_name = self._normalize_application_name(payload["application"].get("name", ""))
        spec.domain_name = payload["application"].get("domain", "").strip()
        spec.archive_id = (request.archive_id or spec.archive_id or settings.default_archive_id).strip()
        spec.status = request.status
        spec.payload = payload
        self.session.commit()
        self.session.refresh(spec)
        return self._serialize_detail(spec)

    def list_formal_elements(
        self,
        *,
        item_type: Literal["entity", "process"],
        archive_id: str,
        archive_service: ArchiveKnowledgeService,
    ) -> list[dict]:
        if item_type == "entity":
            entities = archive_service.get_entities(archive_id)
            return [
                {
                    "id": entity["id"],
                    "name": entity["name"],
                    "item_type": "entity",
                    "category": entity.get("category"),
                    "aliases": entity.get("aliases", []),
                    "document_count": entity.get("document_count", 0),
                    "summary": entity.get("interpretation", {}).get("summary", ""),
                    "source_archive_id": archive_id,
                }
                for entity in entities
            ]

        processes = archive_service.get_processes(archive_id)
        serialized_processes = []
        for process in processes:
            evidence = process.get("evidence", [])
            serialized_processes.append(
                {
                    "id": process["id"],
                    "name": process["name"],
                    "item_type": "process",
                    "category": process.get("category"),
                    "aliases": process.get("aliases", []),
                    "document_count": len(process.get("document_ids", [])),
                    "summary": evidence[0].get("excerpt", f"{process['name']} 是流程类正式元素。")
                    if evidence
                    else f"{process['name']} 是流程类正式元素。",
                    "source_archive_id": archive_id,
                }
            )
        return sorted(serialized_processes, key=lambda item: (-item["document_count"], item["name"]))

    def _serialize_summary(self, spec: RequirementSpec) -> dict:
        counts = self._compute_counts(spec.payload)
        return {
            "id": spec.id,
            "application_name": spec.application_name,
            "domain_name": spec.domain_name,
            "status": spec.status,
            "archive_id": spec.archive_id,
            "object_count": counts["object_count"],
            "formal_object_count": counts["formal_object_count"],
            "temporary_object_count": counts["temporary_object_count"],
            "process_count": counts["process_count"],
            "updated_at": spec.updated_at.isoformat(),
        }

    def _serialize_detail(self, spec: RequirementSpec) -> dict:
        return {
            **self._serialize_summary(spec),
            "created_at": spec.created_at.isoformat(),
            "payload": spec.payload,
        }

    def _compute_counts(self, payload: dict) -> dict:
        objects = payload.get("objects", [])
        processes = payload.get("processes", [])
        formal_object_count = len([item for item in objects if item.get("source_kind") == "formal"])
        return {
            "object_count": len(objects),
            "formal_object_count": formal_object_count,
            "temporary_object_count": len(objects) - formal_object_count,
            "process_count": len(processes),
        }

    def _normalize_application_name(self, value: str) -> str:
        normalized = value.strip()
        return normalized or "未命名应用"
