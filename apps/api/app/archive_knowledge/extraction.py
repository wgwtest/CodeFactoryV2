from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import md5
from pathlib import Path

from app.archive_knowledge.builder import (
    SUPPORTED_SUFFIXES,
    DiscoveredDocument,
    build_archive_knowledge,
    parse_discovered_document,
    persist_archive_outputs,
)
from app.archive_knowledge.document_artifacts import (
    DocumentArtifactRepository,
    aggregate_document_contributions,
    build_document_contribution,
)
from app.archive_knowledge.runtime_parser_execution import parsed_document_from_source_document
from app.archive_knowledge.runtime_snapshot_service import (
    DocumentRuntimeSnapshotService,
)
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.knowledge_builder import SourceDocument, _document_id
from app.parsing.service import ParsingService


class ArchiveExtractionService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.runtime_snapshot_service = DocumentRuntimeSnapshotService(self.output_root)
        self.runtime_repository = self.runtime_snapshot_service.runtime_repository

    def build_archive(
        self,
        archive_id: str,
        *,
        source_dir: Path,
        extract_root: Path,
        archive_name: str,
        policy_snapshot: dict | None = None,
    ) -> dict:
        result = build_archive_knowledge(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            extract_root=extract_root,
            output_root=self.output_root,
            formal_extraction_mode=True,
            policy_snapshot=policy_snapshot,
        )

        return {
            "archive_id": result.archive_id,
            "source_dir": str(result.source_dir),
            "extract_root": str(result.extract_root),
            "json_path": str(result.json_path),
            "curated_path": str(result.curated_path),
            "markdown_path": str(result.markdown_path),
            "parsed_documents_path": str(result.parsed_documents_path),
            "extraction_report_path": str(result.extraction_report_path),
            "summary": result.summary,
        }

    def formalize_document(
        self,
        archive_id: str,
        *,
        document_id: str,
        source_dir: Path,
        extract_root: Path,
        archive_name: str | None = None,
    ) -> dict:
        archive_name = archive_name or archive_id
        artifact_repository = DocumentArtifactRepository(self.output_root)

        if not artifact_repository.has_manifest(archive_id):
            build_result = self.build_archive(
                archive_id,
                source_dir=source_dir,
                extract_root=extract_root,
                archive_name=archive_name,
            )
            document_detail = ArchiveKnowledgeService(self.output_root).get_document_detail(archive_id, document_id)
            return {
                "archive_id": archive_id,
                "document_id": document_id,
                "action": "include",
                "mode": "full_rebuild_bootstrap",
                "document_included": True,
                "summary": build_result["summary"],
                "document": document_detail["document"] if document_detail is not None else None,
            }

        document_source = artifact_repository.get_document_source_info(archive_id, document_id)
        if document_source is None:
            raise ValueError(f"Document not found in archive manifest: {document_id}")

        document = self._build_formal_source_document(document_source)
        contribution = build_document_contribution(
            document,
            extraction_service=self._formal_extraction_service(),
            document_id=document_id,
        )
        artifact_repository.upsert(archive_id, contribution, included_in_archive=True)
        self._persist_asset_intake_snapshot(
            archive_id,
            archive_name=archive_name,
            document_id=document_id,
            document_title=document.title,
            document_path=document.path,
            source_dir=source_dir,
            source_file_path=document.source_file_path,
            file_type=document.file_type,
            source_archive=document.source_archive,
            source_digest=document.source_digest,
            included_in_archive=True,
            mode="formalize_document",
            intake_timestamp=datetime.now(UTC).isoformat(),
        )
        parsed_document = parsed_document_from_source_document(
            parser_name=document.parser_name,
            segment_count=document.segment_count,
            segments=document.segments,
            source_file_path=document.source_file_path,
            source_digest=document.source_digest,
        )
        self._persist_parser_router_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document.title,
            file_type=document.file_type,
            source_file_path=document.source_file_path,
            parser_name=parsed_document.parser_name,
            parser_version=parsed_document.parser_version,
        )
        self._persist_parser_execution_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document.title,
            file_type=document.file_type,
            parsed_document=parsed_document,
        )
        self._persist_unified_document_object_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document.title,
            file_type=document.file_type,
            parsed_document=parsed_document,
        )
        self._persist_evidence_constructor_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
        )
        self._persist_evidence_graph_chunk_layer_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
        )
        self._persist_evidence_pack_snapshot(archive_id, contribution=contribution)
        self._persist_concept_candidate_review_snapshot(
            archive_id,
            contribution=contribution,
        )
        self._persist_relation_review_family_normalization_snapshot(
            archive_id,
            contribution=contribution,
        )
        self._persist_definition_summary_conflict_consolidation_snapshot(
            archive_id,
            contribution=contribution,
        )
        self._persist_canonical_knowledge_snapshot(archive_id, contribution=contribution)
        result = self._rebuild_archive_from_artifacts(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            extract_root=extract_root,
            artifact_repository=artifact_repository,
        )
        self._persist_quality_gate_snapshot(archive_id, contribution=contribution)
        self._persist_indexes_snapshots_apis_snapshot(archive_id, contribution=contribution)
        document_detail = ArchiveKnowledgeService(self.output_root).get_document_detail(archive_id, document_id)
        return {
            "archive_id": archive_id,
            "document_id": document_id,
            "action": "include",
            "mode": "incremental_merge",
            "document_included": True,
            "summary": result.summary,
            "document": document_detail["document"] if document_detail is not None else None,
        }

    def import_document(
        self,
        archive_id: str,
        *,
        file_name: str,
        file_bytes: bytes,
        source_dir: Path,
        extract_root: Path,
        archive_name: str | None = None,
    ) -> dict:
        archive_name = archive_name or archive_id
        source_dir = source_dir.expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(f"Archive source directory does not exist or is not readable: {source_dir}")

        stored_file_path, staged_new_file = self._stage_uploaded_document(
            source_dir,
            file_name=file_name,
            file_bytes=file_bytes,
        )
        document_path = stored_file_path.relative_to(source_dir).as_posix()
        document_id = _document_id(document_path)
        artifact_repository = DocumentArtifactRepository(self.output_root)

        try:
            if not artifact_repository.has_manifest(archive_id):
                build_result = self.build_archive(
                    archive_id,
                    source_dir=source_dir,
                    extract_root=extract_root,
                    archive_name=archive_name,
                )
                document_detail = ArchiveKnowledgeService(self.output_root).get_document_detail(archive_id, document_id)
                return {
                    "archive_id": archive_id,
                    "document_id": document_id,
                    "action": "include",
                    "mode": "full_rebuild_bootstrap_import",
                    "document_included": True,
                    "stored_path": document_path,
                    "summary": build_result["summary"],
                    "document": document_detail["document"] if document_detail is not None else None,
                }

            source_digest = _file_digest(stored_file_path)
            parsed_document_for_runtime = None
            if artifact_repository.has_reusable_artifact(
                archive_id,
                document_id,
                source_digest=source_digest,
            ):
                contribution = artifact_repository.load_document_contribution(archive_id, document_id)
                if contribution is None:
                    raise FileNotFoundError(f"Document artifact missing after upload: {document_id}")
            else:
                document = self._build_uploaded_source_document(
                    source_dir=source_dir,
                    stored_file_path=stored_file_path,
                    source_digest=source_digest,
                )
                contribution = build_document_contribution(
                    document,
                    extraction_service=self._formal_extraction_service(),
                    document_id=document_id,
                )
                parsed_document_for_runtime = parsed_document_from_source_document(
                    parser_name=document.parser_name,
                    segment_count=document.segment_count,
                    segments=document.segments,
                    source_file_path=document.source_file_path,
                    source_digest=document.source_digest,
                )

            artifact_repository.upsert(archive_id, contribution, included_in_archive=True)
            contribution_document = contribution["document"]
            self._persist_asset_intake_snapshot(
                archive_id,
                archive_name=archive_name,
                document_id=document_id,
                document_title=contribution_document["title"],
                document_path=document_path,
                source_dir=source_dir,
                source_file_path=str(stored_file_path),
                file_type=contribution_document["file_type"],
                source_archive=contribution_document["source_archive"],
                source_digest=source_digest,
                included_in_archive=True,
                mode="import_document",
                intake_timestamp=datetime.now(UTC).isoformat(),
            )
            if parsed_document_for_runtime is None:
                existing_parser_snapshot = self.runtime_repository.load_stage_snapshot(
                    archive_id,
                    document_id,
                    "parser_execution",
                )
                existing_router_snapshot = self.runtime_repository.load_stage_snapshot(
                    archive_id,
                    document_id,
                    "parser_router",
                )
                if existing_parser_snapshot is None or existing_router_snapshot is None:
                    parsed_document_for_runtime = parsed_document_from_source_document(
                        parser_name=contribution_document.get("parser_name"),
                        segment_count=int(contribution_document.get("segment_count") or 0),
                        segments=[],
                        source_file_path=contribution_document.get("source_file_path"),
                        source_digest=contribution_document.get("source_digest"),
                    )
            if parsed_document_for_runtime is not None:
                self._persist_parser_router_snapshot(
                    archive_id,
                    document_id=document_id,
                    document_title=contribution_document["title"],
                    file_type=contribution_document["file_type"],
                    source_file_path=contribution_document.get("source_file_path"),
                    parser_name=parsed_document_for_runtime.parser_name,
                    parser_version=parsed_document_for_runtime.parser_version,
                )
                self._persist_parser_execution_snapshot(
                    archive_id,
                    document_id=document_id,
                    document_title=contribution_document["title"],
                    file_type=contribution_document["file_type"],
                    parsed_document=parsed_document_for_runtime,
                )
                self._persist_unified_document_object_snapshot(
                    archive_id,
                    document_id=document_id,
                    document_title=contribution_document["title"],
                    file_type=contribution_document["file_type"],
                    parsed_document=parsed_document_for_runtime,
                )
                self._persist_evidence_constructor_snapshot(
                    archive_id,
                    contribution=contribution,
                    parsed_document=parsed_document_for_runtime,
                )
                self._persist_evidence_graph_chunk_layer_snapshot(
                    archive_id,
                    contribution=contribution,
                    parsed_document=parsed_document_for_runtime,
                )
            self._persist_evidence_pack_snapshot(archive_id, contribution=contribution)
            self._persist_concept_candidate_review_snapshot(
                archive_id,
                contribution=contribution,
            )
            self._persist_relation_review_family_normalization_snapshot(
                archive_id,
                contribution=contribution,
            )
            self._persist_definition_summary_conflict_consolidation_snapshot(
                archive_id,
                contribution=contribution,
            )
            self._persist_canonical_knowledge_snapshot(archive_id, contribution=contribution)
            result = self._rebuild_archive_from_artifacts(
                archive_id=archive_id,
                archive_name=archive_name,
                source_dir=source_dir,
                extract_root=extract_root,
                artifact_repository=artifact_repository,
            )
            self._persist_quality_gate_snapshot(archive_id, contribution=contribution)
            self._persist_indexes_snapshots_apis_snapshot(archive_id, contribution=contribution)
            document_detail = ArchiveKnowledgeService(self.output_root).get_document_detail(archive_id, document_id)
            return {
                "archive_id": archive_id,
                "document_id": document_id,
                "action": "include",
                "mode": "single_document_import",
                "document_included": True,
                "stored_path": document_path,
                "summary": result.summary,
                "document": document_detail["document"] if document_detail is not None else None,
            }
        except Exception:
            if staged_new_file:
                stored_file_path.unlink(missing_ok=True)
            raise

    def remove_document(
        self,
        archive_id: str,
        *,
        document_id: str,
        source_dir: Path,
        extract_root: Path,
        archive_name: str | None = None,
    ) -> dict:
        archive_name = archive_name or archive_id
        artifact_repository = DocumentArtifactRepository(self.output_root)
        mode = "incremental_remove"

        if not artifact_repository.has_manifest(archive_id):
            self.build_archive(
                archive_id,
                source_dir=source_dir,
                extract_root=extract_root,
                archive_name=archive_name,
            )
            mode = "full_rebuild_bootstrap_remove"

        document_source = artifact_repository.set_included_in_archive(
            archive_id,
            document_id,
            included_in_archive=False,
        )
        if document_source is None:
            raise ValueError(f"Document not found in archive manifest: {document_id}")

        result = self._rebuild_archive_from_artifacts(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            extract_root=extract_root,
            artifact_repository=artifact_repository,
        )
        document_detail = ArchiveKnowledgeService(self.output_root).get_document_detail(archive_id, document_id)
        return {
            "archive_id": archive_id,
            "document_id": document_id,
            "action": "remove",
            "mode": mode,
            "document_included": False,
            "summary": result.summary,
            "document": document_detail["document"] if document_detail is not None else None,
        }

    @staticmethod
    def _formal_extraction_service():
        from app.extraction.service import ExtractionService

        return ExtractionService(formal_extraction_mode=True)

    @staticmethod
    def _build_formal_source_document(document_source: dict) -> SourceDocument:
        source_file_path = document_source.get("source_file_path")
        if not source_file_path:
            raise ValueError("Document artifact is missing the source file path for rebuild")

        file_path = Path(source_file_path).expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Document source file does not exist: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            raise ValueError(f"Formal extraction does not permit spreadsheet fallback parsing: {file_path}")

        parsed = ParsingService(formal_extraction_mode=True).parse_file(file_path)
        if suffix in {".pdf", ".doc", ".docx"} and parsed.parser_name not in {"docling_pdf", "docling_docx"}:
            raise ValueError(
                f"Formal extraction requires Docling for this file but parser {parsed.parser_name} was used: {file_path}"
            )

        text = "\n".join(segment.content for segment in parsed.segments)
        if not text.strip():
            raise ValueError(f"Formal extraction failed to produce text from document: {file_path}")

        return SourceDocument(
            path=document_source["path"],
            title=document_source["title"],
            file_type=document_source["file_type"],
            source_archive=document_source["source_archive"],
            text=text,
            parser_name=parsed.parser_name,
            segment_count=len(parsed.segments),
            segments=parsed.segments,
            source_file_path=str(file_path),
            source_digest=_file_digest(file_path),
        )

    @staticmethod
    def _build_uploaded_source_document(
        *,
        source_dir: Path,
        stored_file_path: Path,
        source_digest: str,
    ) -> SourceDocument:
        relative_path = stored_file_path.relative_to(source_dir).as_posix()
        relative_parts = Path(relative_path).parts
        source_archive = relative_parts[0] if len(relative_parts) > 1 else source_dir.name
        discovered_document = DiscoveredDocument(
            path=relative_path,
            title=stored_file_path.stem,
            file_type=stored_file_path.suffix.lower().lstrip("."),
            source_archive=source_archive,
            source_file_path=str(stored_file_path),
            source_digest=source_digest,
        )
        return parse_discovered_document(discovered_document, formal_extraction_mode=True)

    @staticmethod
    def _stage_uploaded_document(source_dir: Path, *, file_name: str, file_bytes: bytes) -> tuple[Path, bool]:
        sanitized_name = Path(file_name).name.strip()
        if not sanitized_name:
            raise ValueError("Uploaded file is missing a valid file name")
        if Path(sanitized_name).suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported archive source document type: {sanitized_name}")
        if not file_bytes:
            raise ValueError("Uploaded file is empty")

        target_dir = source_dir / "manual_uploads" / date.today().isoformat()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = (target_dir / sanitized_name).resolve()
        if not target_path.is_relative_to(source_dir):
            raise ValueError("Uploaded file path escapes the archive source directory")
        if target_path.exists():
            if target_path.read_bytes() == file_bytes:
                return target_path, False
            raise ValueError(f"Target file already exists in archive source directory: {target_path}")

        target_path.write_bytes(file_bytes)
        return target_path, True

    def _rebuild_archive_from_artifacts(
        self,
        *,
        archive_id: str,
        archive_name: str,
        source_dir: Path,
        extract_root: Path,
        artifact_repository: DocumentArtifactRepository,
    ):
        all_contributions = artifact_repository.load_contributions(archive_id)
        included_contributions = artifact_repository.load_contributions(archive_id, included_only=True)
        knowledge = aggregate_document_contributions(included_contributions)
        return persist_archive_outputs(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir.expanduser().resolve(),
            extract_root=extract_root.expanduser().resolve(),
            output_root=self.output_root.expanduser().resolve(),
            knowledge=knowledge,
            contributions=all_contributions,
            formal_extraction_mode=True,
        )

    def _persist_asset_intake_snapshot(
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
    ) -> None:
        self.runtime_snapshot_service.persist_asset_intake_snapshot(
            archive_id,
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

    def _persist_evidence_pack_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_evidence_pack_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_concept_candidate_review_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_concept_candidate_review_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_relation_review_family_normalization_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_relation_review_family_normalization_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_definition_summary_conflict_consolidation_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_definition_summary_conflict_consolidation_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_canonical_knowledge_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_canonical_knowledge_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_parser_router_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        source_file_path: str | None,
        parser_name: str | None,
        parser_version: str | None,
    ) -> None:
        self.runtime_snapshot_service.persist_parser_router_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            source_file_path=source_file_path,
            parser_name=parser_name,
            parser_version=parser_version,
        )

    def _persist_parser_execution_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        parsed_document,
    ) -> None:
        self.runtime_snapshot_service.persist_parser_execution_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            parsed_document=parsed_document,
        )

    def _persist_unified_document_object_snapshot(
        self,
        archive_id: str,
        *,
        document_id: str,
        document_title: str,
        file_type: str | None,
        parsed_document,
    ) -> None:
        self.runtime_snapshot_service.persist_unified_document_object_snapshot(
            archive_id,
            document_id=document_id,
            document_title=document_title,
            file_type=file_type,
            parsed_document=parsed_document,
        )

    def _persist_evidence_constructor_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
        parsed_document,
    ) -> None:
        self.runtime_snapshot_service.persist_evidence_constructor_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
        )

    def _persist_evidence_graph_chunk_layer_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
        parsed_document,
    ) -> None:
        self.runtime_snapshot_service.persist_evidence_graph_chunk_layer_snapshot(
            archive_id,
            contribution=contribution,
            parsed_document=parsed_document,
        )

    @staticmethod
    def _load_parsed_document_from_source_file(source_file_path: str | None):
        return DocumentRuntimeSnapshotService._load_parsed_document_from_source_file(source_file_path)

    def _persist_quality_gate_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_quality_gate_snapshot(
            archive_id,
            contribution=contribution,
        )

    def _persist_indexes_snapshots_apis_snapshot(
        self,
        archive_id: str,
        *,
        contribution: dict,
    ) -> None:
        self.runtime_snapshot_service.persist_indexes_snapshots_apis_snapshot(
            archive_id,
            contribution=contribution,
        )


def _file_digest(path: Path) -> str:
    hasher = md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
