from __future__ import annotations

from pathlib import Path

from app.archive_knowledge.builder import build_archive_knowledge, persist_archive_outputs
from app.archive_knowledge.document_artifacts import (
    DocumentArtifactRepository,
    aggregate_document_contributions,
    build_document_contribution,
)
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.knowledge_builder import SourceDocument
from app.parsing.service import ParsingService


class ArchiveExtractionService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def build_archive(
        self,
        archive_id: str,
        *,
        source_dir: Path,
        extract_root: Path,
        archive_name: str,
    ) -> dict:
        result = build_archive_knowledge(
            archive_id=archive_id,
            archive_name=archive_name,
            source_dir=source_dir,
            extract_root=extract_root,
            output_root=self.output_root,
            formal_extraction_mode=True,
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
            raise ValueError(f"知识库中未找到目标文档: {document_id}")

        document = self._build_formal_source_document(document_source)
        contribution = build_document_contribution(
            document,
            extraction_service=self._formal_extraction_service(),
            document_id=document_id,
        )
        artifact_repository.upsert(archive_id, contribution, included_in_archive=True)
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
            "action": "include",
            "mode": "incremental_merge",
            "document_included": True,
            "summary": result.summary,
            "document": document_detail["document"] if document_detail is not None else None,
        }

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
            raise ValueError(f"知识库中未找到目标文档: {document_id}")

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
            raise ValueError("文档级正式产物缺少源文件路径，无法执行增量重建")

        file_path = Path(source_file_path).expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"文档源文件不存在: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            raise ValueError(f"正式知识库抽取当前不允许使用非 Docling 的表格解析链路：{file_path}")

        parsed = ParsingService(formal_extraction_mode=True).parse_file(file_path)
        if suffix in {".pdf", ".doc", ".docx"} and parsed.parser_name not in {"docling_pdf", "docling_docx"}:
            raise ValueError(f"正式知识库抽取要求使用 Docling 解析，但文件实际使用了解析器 {parsed.parser_name}：{file_path}")

        text = "\n".join(segment.content for segment in parsed.segments)
        if not text.strip():
            raise ValueError(f"正式知识库抽取失败：Docling 未能从文件中解析出有效文本：{file_path}")

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
        )

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
