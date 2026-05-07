from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.archive_knowledge.runtime_asset_intake import build_asset_intake_snapshot
from app.archive_knowledge.runtime_canonical_knowledge import (
    build_canonical_knowledge_snapshot,
)
from app.archive_knowledge.runtime_concept_candidate_review import (
    build_concept_candidate_review_snapshot,
)
from app.archive_knowledge.runtime_definition_summary_conflict_consolidation import (
    build_definition_summary_conflict_consolidation_snapshot,
)
from app.archive_knowledge.runtime_evidence_constructor import (
    build_evidence_constructor_snapshot,
)
from app.archive_knowledge.runtime_evidence_graph_chunk_layer import (
    build_evidence_graph_chunk_layer_snapshot,
)
from app.archive_knowledge.runtime_evidence_pack import build_evidence_pack_snapshot
from app.archive_knowledge.runtime_indexes_snapshots_apis import (
    build_indexes_snapshots_apis_snapshot,
)
from app.archive_knowledge.runtime_parser_execution import (
    build_parser_execution_snapshot,
    parsed_document_from_source_document,
)
from app.archive_knowledge.runtime_parser_router import build_parser_router_snapshot
from app.archive_knowledge.runtime_contract import RuntimeStatus
from app.archive_knowledge.runtime_quality_gate import build_quality_gate_snapshot
from app.archive_knowledge.runtime_relation_review_family_normalization import (
    build_relation_review_family_normalization_snapshot,
)
from app.archive_knowledge.runtime_repository import DocumentRuntimeRepository
from app.archive_knowledge.runtime_unified_document_object import (
    build_unified_document_object_snapshot,
)
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.parsing.service import ParsingService

RUNTIME_SNAPSHOT_CONTRACT_VERSION = 5


class DocumentRuntimeSnapshotService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.runtime_repository = DocumentRuntimeRepository(self.output_root)
        self.knowledge_service = ArchiveKnowledgeService(self.output_root)

    def persist_document_runtime_snapshots(
        self,
        *,
        archive_id: str,
        archive_name: str,
        document_source: dict[str, Any],
        contribution: dict[str, Any] | None = None,
        source_dir: Path | None = None,
        mode: str = "archive_extract",
        intake_timestamp: str | None = None,
        parsed_document=None,
        included_in_archive: bool | None = None,
    ) -> list[str]:
        document_payload = self._normalize_document_payload(document_source, contribution)
        document_id = document_payload["document_id"]
        runtime_trace = ((contribution or {}).get("extraction") or {}).get("runtime_trace", {})
        source_dir = source_dir or self._resolve_source_dir(document_payload)
        intake_timestamp = intake_timestamp or datetime.now(UTC).isoformat()
        included_in_archive = (
            document_payload.get("included_in_archive", True)
            if included_in_archive is None
            else included_in_archive
        )

        persisted_stage_ids: list[str] = []
        persisted_stage_ids.append(
            self.persist_asset_intake_snapshot(
                archive_id,
                archive_name=archive_name,
                document_id=document_id,
                document_title=document_payload["title"],
                document_path=document_payload.get("path"),
                source_dir=source_dir,
                source_file_path=document_payload.get("source_file_path"),
                file_type=document_payload.get("file_type"),
                source_archive=document_payload.get("source_archive"),
                source_digest=document_payload.get("source_digest"),
                included_in_archive=included_in_archive,
                mode=mode,
                intake_timestamp=intake_timestamp,
            )
        )

        resolved_parsed_document = parsed_document or self.load_or_derive_parsed_document(document_payload)
        if resolved_parsed_document is not None:
            persisted_stage_ids.extend(
                [
                    self.persist_parser_router_snapshot(
                        archive_id,
                        document_id=document_id,
                        document_title=document_payload["title"],
                        file_type=document_payload.get("file_type"),
                        source_file_path=document_payload.get("source_file_path"),
                        parser_name=resolved_parsed_document.parser_name,
                        parser_version=resolved_parsed_document.parser_version,
                    ),
                    self.persist_parser_execution_snapshot(
                        archive_id,
                        document_id=document_id,
                        document_title=document_payload["title"],
                        file_type=document_payload.get("file_type"),
                        parsed_document=resolved_parsed_document,
                    ),
                    self.persist_unified_document_object_snapshot(
                        archive_id,
                        document_id=document_id,
                        document_title=document_payload["title"],
                        file_type=document_payload.get("file_type"),
                        parsed_document=resolved_parsed_document,
                        runtime_trace=runtime_trace.get("unified_document_object"),
                    ),
                ]
            )

        if contribution is not None and resolved_parsed_document is not None:
            persisted_stage_ids.extend(
                [
                    self.persist_evidence_constructor_snapshot(
                        archive_id,
                        contribution=contribution,
                        parsed_document=resolved_parsed_document,
                        runtime_trace=runtime_trace.get("evidence_constructor"),
                    ),
                    self.persist_evidence_graph_chunk_layer_snapshot(
                        archive_id,
                        contribution=contribution,
                        parsed_document=resolved_parsed_document,
                        runtime_trace=runtime_trace.get("evidence_graph_chunk_layer"),
                    ),
                ]
            )

        if contribution is not None:
            persisted_stage_ids.extend(
                [
                    self.persist_evidence_pack_snapshot(archive_id, contribution=contribution),
                    self.persist_concept_candidate_review_snapshot(
                        archive_id,
                        contribution=contribution,
                    ),
                    self.persist_relation_review_family_normalization_snapshot(
                        archive_id,
                        contribution=contribution,
                    ),
                    self.persist_definition_summary_conflict_consolidation_snapshot(
                        archive_id,
                        contribution=contribution,
                    ),
                    self.persist_canonical_knowledge_snapshot(
                        archive_id,
                        contribution=contribution,
                    ),
                    self.persist_quality_gate_snapshot(
                        archive_id,
                        contribution=contribution,
                        runtime_trace=runtime_trace.get("quality_policy_evaluation_governance_gate"),
                    ),
                    self.persist_indexes_snapshots_apis_snapshot(
                        archive_id,
                        contribution=contribution,
                    ),
                ]
            )

        deduplicated_stage_ids: list[str] = []
        for stage_id in persisted_stage_ids:
            if stage_id not in deduplicated_stage_ids:
                deduplicated_stage_ids.append(stage_id)
        return deduplicated_stage_ids

    def refresh_runtime_stage_snapshots(
        self,
        *,
        archive_id: str,
        contribution: dict[str, Any],
        stage_ids: list[str],
    ) -> list[str]:
        runtime_trace = ((contribution or {}).get("extraction") or {}).get("runtime_trace", {})
        refreshed_stage_ids: list[str] = []

        for stage_id in stage_ids:
            if stage_id == "evidence_pack":
                refreshed_stage_ids.append(self.persist_evidence_pack_snapshot(archive_id, contribution=contribution))
            elif stage_id == "concept_candidate_review":
                refreshed_stage_ids.append(
                    self.persist_concept_candidate_review_snapshot(archive_id, contribution=contribution)
                )
            elif stage_id == "relation_review_family_normalization":
                refreshed_stage_ids.append(
                    self.persist_relation_review_family_normalization_snapshot(
                        archive_id,
                        contribution=contribution,
                    )
                )
            elif stage_id == "definition_summary_conflict_consolidation":
                refreshed_stage_ids.append(
                    self.persist_definition_summary_conflict_consolidation_snapshot(
                        archive_id,
                        contribution=contribution,
                    )
                )
            elif stage_id == "canonical_knowledge":
                refreshed_stage_ids.append(
                    self.persist_canonical_knowledge_snapshot(
                        archive_id,
                        contribution=contribution,
                    )
                )
            elif stage_id == "quality_policy_evaluation_governance_gate":
                refreshed_stage_ids.append(
                    self.persist_quality_gate_snapshot(
                        archive_id,
                        contribution=contribution,
                        runtime_trace=runtime_trace.get("quality_policy_evaluation_governance_gate"),
                    )
                )
            elif stage_id == "indexes_snapshots_apis":
                refreshed_stage_ids.append(
                    self.persist_indexes_snapshots_apis_snapshot(
                        archive_id,
                        contribution=contribution,
                    )
                )

        deduplicated_stage_ids: list[str] = []
        for stage_id in refreshed_stage_ids:
            if stage_id not in deduplicated_stage_ids:
                deduplicated_stage_ids.append(stage_id)
        return deduplicated_stage_ids

    def load_or_derive_parsed_document(self, document_source: dict[str, Any]):
        parsed_document = self._load_parsed_document_from_source_file(
            document_source.get("source_file_path")
        )
        if parsed_document is not None:
            return parsed_document
        if document_source.get("parser_name") or document_source.get("segment_count"):
            return parsed_document_from_source_document(
                parser_name=document_source.get("parser_name"),
                segment_count=int(document_source.get("segment_count") or 0),
                segments=None,
                source_file_path=document_source.get("source_file_path"),
                source_digest=document_source.get("source_digest"),
            )
        return None

    def persist_asset_intake_snapshot(
        self,
        archive_id: str,
        *,
        archive_name: str,
        document_id: str,
        document_title: str,
        document_path: str | None,
        source_dir: Path,
        source_file_path: str | None,
        file_type: str | None,
        source_archive: str | None,
        source_digest: str | None,
        included_in_archive: bool,
        mode: str,
        intake_timestamp: str,
    ) -> str:
        snapshot = build_asset_intake_snapshot(
            archive_id=archive_id,
            archive_name=archive_name,
            document_id=document_id,
            document_title=document_title,
            document_path=document_path,
            source_dir=source_dir,
            source_file_path=source_file_path,
            file_type=file_type,
            source_archive=source_archive,
            source_digest=source_digest,
            included_in_archive=included_in_archive,
            mode=mode,
            intake_timestamp=intake_timestamp,
        )
        self._save_stage_snapshot(archive_id, document_id, snapshot)
        return snapshot.stage_id

    def persist_evidence_pack_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        snapshot = build_evidence_pack_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_concept_candidate_review_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        snapshot = build_concept_candidate_review_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_relation_review_family_normalization_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        snapshot = build_relation_review_family_normalization_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_definition_summary_conflict_consolidation_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        snapshot = build_definition_summary_conflict_consolidation_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_canonical_knowledge_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        knowledge_items = ArchiveKnowledgeService._build_document_knowledge_items_from_contribution(
            contribution,
            document,
        )
        snapshot = build_canonical_knowledge_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
            knowledge_items=knowledge_items,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_parser_router_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        source_file_path: str | None,
        parser_name: str | None,
        parser_version: str | None,
    ) -> str:
        snapshot = build_parser_router_snapshot(
            archive_id=archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            source_file_path=source_file_path,
            parser_name=parser_name,
            parser_version=parser_version,
        )
        self._save_stage_snapshot(archive_id, document_id, snapshot)
        return snapshot.stage_id

    def persist_parser_execution_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        parsed_document,
    ) -> str:
        snapshot = build_parser_execution_snapshot(
            archive_id=archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            parsed_document=parsed_document,
        )
        self._save_stage_snapshot(archive_id, document_id, snapshot)
        return snapshot.stage_id

    def persist_unified_document_object_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        parsed_document,
        runtime_trace: dict[str, Any] | None = None,
        status_override: RuntimeStatus | None = None,
    ) -> str:
        snapshot = build_unified_document_object_snapshot(
            archive_id=archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            parsed_document=parsed_document,
            runtime_trace=runtime_trace,
            status_override=status_override,
        )
        self._save_stage_snapshot(archive_id, document_id, snapshot)
        return snapshot.stage_id

    def persist_evidence_constructor_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
        parsed_document,
        runtime_trace: dict[str, Any] | None = None,
        status_override: RuntimeStatus | None = None,
    ) -> str:
        document = contribution["document"]
        snapshot = build_evidence_constructor_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
            parsed_document=parsed_document,
            runtime_trace=runtime_trace,
            status_override=status_override,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_evidence_graph_chunk_layer_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
        parsed_document,
        runtime_trace: dict[str, Any] | None = None,
        status_override: RuntimeStatus | None = None,
    ) -> str:
        document = contribution["document"]
        snapshot = build_evidence_graph_chunk_layer_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
            parsed_document=parsed_document,
            runtime_trace=runtime_trace,
            status_override=status_override,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_quality_gate_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
        runtime_trace: dict[str, Any] | None = None,
        status_override: RuntimeStatus | None = None,
    ) -> str:
        document = contribution["document"]
        knowledge_items = self._load_runtime_knowledge_items(
            archive_id=archive_id,
            document=document,
            contribution=contribution,
        )

        current_version, document_published = self._build_publication_context(
            archive_id,
            document["id"],
        )
        snapshot = build_quality_gate_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            contribution=contribution,
            knowledge_items=knowledge_items,
            current_version=current_version,
            document_published=document_published,
            runtime_trace=runtime_trace,
            status_override=status_override,
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def persist_indexes_snapshots_apis_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict[str, Any],
    ) -> str:
        document = contribution["document"]
        current_version, document_published = self._build_publication_context(
            archive_id,
            document["id"],
        )
        knowledge_items = self._load_runtime_knowledge_items(
            archive_id=archive_id,
            document=document,
            contribution=contribution,
        )
        gate_snapshot = self.runtime_repository.load_stage_snapshot(
            archive_id,
            document["id"],
            "quality_policy_evaluation_governance_gate",
        ) or {}
        gate_fields = {
            field.get("key"): field.get("value")
            for section in (gate_snapshot.get("stage_observer") or {}).get("sections", [])
            for field in section.get("fields", [])
            if isinstance(field, dict)
        }
        snapshot = build_indexes_snapshots_apis_snapshot(
            archive_id=archive_id,
            document_id=document["id"],
            document_title=document["title"],
            current_version=current_version,
            document_published=document_published,
            contribution=contribution,
            knowledge_items=knowledge_items,
            gate_decision_status=gate_fields.get("decision"),
            gate_decision_reason=gate_fields.get("reason"),
        )
        self._save_stage_snapshot(archive_id, document["id"], snapshot)
        return snapshot.stage_id

    def _load_runtime_knowledge_items(
        self,
        *,
        archive_id: str,
        document: dict[str, Any],
        contribution: dict[str, Any],
    ) -> list[dict[str, Any]]:
        try:
            payload = self.knowledge_service._load_raw(archive_id)
            document_index = self.knowledge_service._build_document_index(payload)
            live_document = document_index.get(document["id"])
            if live_document is None:
                raise FileNotFoundError(document["id"])
            return ArchiveKnowledgeService._build_document_knowledge_items(
                payload,
                document["id"],
                live_document,
            )
        except FileNotFoundError:
            return ArchiveKnowledgeService._build_document_knowledge_items_from_contribution(
                contribution,
                document,
            )

    def _build_publication_context(
        self,
        archive_id: str,
        document_id: str,
    ) -> tuple[dict[str, Any] | None, bool]:
        try:
            publication = self.knowledge_service.get_publication_overview(archive_id)
        except FileNotFoundError:
            publication = {"archive_id": archive_id, "current_version": None, "history": [], "working_summary": {}}

        published_payload, current_version = self.knowledge_service.published_repository.load_latest(archive_id)
        document_published = False
        if published_payload:
            document_published = document_id in {row["id"] for row in published_payload.get("documents", [])}
            if not document_published:
                for collection_name in ("entities", "events", "processes"):
                    if any(
                        document_id in item.get("document_ids", [])
                        for item in published_payload.get(collection_name, [])
                    ):
                        document_published = True
                        break
        return current_version or publication.get("current_version"), document_published

    def _normalize_document_payload(
        self,
        document_source: dict[str, Any],
        contribution: dict[str, Any] | None,
    ) -> dict[str, Any]:
        contribution_document = (contribution or {}).get("document", {})
        return {
            "document_id": (
                document_source.get("document_id")
                or contribution_document.get("id")
                or document_source.get("id")
            ),
            "title": document_source.get("title") or contribution_document.get("title"),
            "path": document_source.get("path") or contribution_document.get("path"),
            "file_type": document_source.get("file_type") or contribution_document.get("file_type"),
            "source_archive": document_source.get("source_archive") or contribution_document.get("source_archive"),
            "source_file_path": document_source.get("source_file_path") or contribution_document.get("source_file_path"),
            "source_digest": document_source.get("source_digest") or contribution_document.get("source_digest"),
            "included_in_archive": document_source.get("included_in_archive", True),
            "parser_name": document_source.get("parser_name") or contribution_document.get("parser_name"),
            "segment_count": document_source.get("segment_count") or contribution_document.get("segment_count") or 0,
        }

    def _resolve_source_dir(self, document_source: dict[str, Any]) -> Path:
        source_file_path = document_source.get("source_file_path")
        if not source_file_path:
            return Path(".").resolve()

        file_path = Path(source_file_path).expanduser().resolve()
        document_path = document_source.get("path")
        relative_parts = Path(document_path).parts if document_path else ()
        if relative_parts:
            parent_index = min(len(relative_parts) - 1, len(file_path.parents) - 1)
            return file_path.parents[parent_index]
        return file_path.parent

    def _save_stage_snapshot(self, archive_id: str, document_id: str, snapshot) -> None:
        payload = snapshot.model_dump(mode="json")
        payload["snapshot_contract_version"] = RUNTIME_SNAPSHOT_CONTRACT_VERSION
        self.runtime_repository.save_stage_snapshot(
            archive_id,
            document_id,
            snapshot.stage_id,
            payload,
        )

    @staticmethod
    def _load_parsed_document_from_source_file(source_file_path: str | None):
        if not source_file_path:
            return None
        file_path = Path(source_file_path).expanduser().resolve()
        if not file_path.exists():
            return None
        try:
            return ParsingService(formal_extraction_mode=True).parse_file(file_path)
        except Exception:
            return None
