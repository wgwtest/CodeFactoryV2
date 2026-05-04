from __future__ import annotations

from typing import Literal

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.config import settings
from app.db.models.requirements import RequirementSpec
from app.requirement_exchange.requirement_spec_repository import RequirementSpecRepository
from app.requirements.schemas import RequirementSpecWrite


class RequirementSpecApplicationService:
    def __init__(self, session) -> None:
        self.repository = RequirementSpecRepository(session)

    def create_from_projected_draft(self, draft: dict) -> RequirementSpec:
        spec = RequirementSpec(
            application_name=(draft["payload"].get("application", {}) or {}).get("name", "").strip() or "未命名应用",
            domain_name=(draft["payload"].get("application", {}) or {}).get("domain", "").strip(),
            archive_id=(draft.get("archive_id") or "").strip(),
            status=draft.get("status", "frozen"),
            payload=draft["payload"],
        )
        return self.repository.add_spec(spec)

    def list_specs(self) -> list[dict]:
        return [self.serialize_summary(spec) for spec in self.repository.list_specs()]

    def get_spec(self, spec_id: str) -> dict | None:
        spec = self.repository.get_spec(spec_id)
        if spec is None:
            return None
        return self.serialize_detail(spec)

    def create_spec(self, request: RequirementSpecWrite) -> dict:
        payload = request.payload.model_dump(mode="json")
        spec = RequirementSpec(
            application_name=self._normalize_application_name(payload["application"].get("name", "")),
            domain_name=payload["application"].get("domain", "").strip(),
            archive_id=(request.archive_id or settings.default_archive_id).strip(),
            status=request.status,
            payload=payload,
        )
        return self.serialize_detail(self.repository.add_spec(spec))

    def update_spec(self, spec_id: str, request: RequirementSpecWrite) -> dict | None:
        spec = self.repository.get_spec(spec_id)
        if spec is None:
            return None
        payload = request.payload.model_dump(mode="json")
        spec.application_name = self._normalize_application_name(payload["application"].get("name", ""))
        spec.domain_name = payload["application"].get("domain", "").strip()
        spec.archive_id = (request.archive_id or spec.archive_id or settings.default_archive_id).strip()
        spec.status = request.status
        spec.payload = payload
        return self.serialize_detail(self.repository.save_spec(spec))

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

    def serialize_summary(self, spec: RequirementSpec) -> dict:
        payload = spec.payload or {}
        objects = payload.get("objects", [])
        processes = payload.get("processes", [])
        formal_object_count = len([item for item in objects if item.get("source_kind") == "formal"])
        return {
            "id": spec.id,
            "application_name": spec.application_name,
            "domain_name": spec.domain_name,
            "status": spec.status,
            "archive_id": spec.archive_id,
            "object_count": len(objects),
            "formal_object_count": formal_object_count,
            "temporary_object_count": len(objects) - formal_object_count,
            "process_count": len(processes),
            "updated_at": spec.updated_at.isoformat(),
        }

    def serialize_detail(self, spec: RequirementSpec) -> dict:
        return {
            **self.serialize_summary(spec),
            "created_at": spec.created_at.isoformat(),
            "payload": spec.payload,
        }

    @staticmethod
    def _normalize_application_name(value: str) -> str:
        normalized = value.strip()
        return normalized or "未命名应用"
