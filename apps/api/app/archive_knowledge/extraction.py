from __future__ import annotations

from pathlib import Path

from app.archive_knowledge.builder import build_archive_knowledge


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
