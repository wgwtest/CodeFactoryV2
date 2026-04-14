from __future__ import annotations

import json
from pathlib import Path

from app.archive_knowledge.builder import render_summary
from app.archive_knowledge.rebuild import reconcile_curated_payload
from app.extraction.schema import ExtractionBatch
from app.knowledge_builder import SourceDocument, build_knowledge_index
from app.parsing.models import ParsedSegment


class _StaticExtractionService:
    def __init__(self, batch: ExtractionBatch) -> None:
        self.batch = batch

    def extract_document(self, *, document_id, title, file_path, segments):
        del segments
        return self.batch.model_copy(
            deep=True,
            update={
                "document_id": document_id,
                "title": title,
                "metadata": {
                    **self.batch.metadata,
                    "source_path": file_path,
                },
            },
        )


def build_preview_archive_payload(
    preview_payload: dict,
    *,
    document_path: str,
    source_archive: str,
    file_type: str,
    character_count: int,
) -> tuple[dict, dict]:
    preview_document = preview_payload.get("document", {})
    batch = ExtractionBatch.model_validate(preview_payload["final_batch"])
    document = SourceDocument(
        path=document_path,
        title=preview_document.get("title") or batch.title,
        file_type=file_type,
        source_archive=source_archive,
        text=" " * max(character_count, 0),
        segments=[
            ParsedSegment(
                heading=preview_document.get("title") or batch.title,
                content=preview_document.get("title") or batch.title,
                anchor={"page": 1, "section": preview_document.get("title") or batch.title, "line_start": 1, "line_end": 1},
                block_type="paragraph",
            )
        ],
    )

    base_payload = build_knowledge_index(
        [document],
        extraction_service=_StaticExtractionService(batch),
    )
    if base_payload.get("documents"):
        base_payload["documents"][0]["character_count"] = character_count

    curated_payload = reconcile_curated_payload(base_payload, None)
    return base_payload, curated_payload


def write_preview_archive_artifacts(
    *,
    output_root: str | Path,
    archive_id: str,
    archive_name: str,
    preview_payload: dict,
    document_path: str,
    source_archive: str,
    file_type: str,
    character_count: int,
) -> dict[str, Path]:
    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_payload, curated_payload = build_preview_archive_payload(
        preview_payload,
        document_path=document_path,
        source_archive=source_archive,
        file_type=file_type,
        character_count=character_count,
    )

    base_path = output_dir / f"{archive_id}-knowledge.json"
    curated_path = output_dir / f"{archive_id}-knowledge-curated.json"
    markdown_path = output_dir / f"{archive_id}-knowledge.md"
    parsed_documents_path = output_dir / f"{archive_id}-parsed-documents.json"
    extraction_report_path = output_dir / f"{archive_id}-extraction-report.json"

    base_path.write_text(json.dumps(base_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    curated_path.write_text(json.dumps(curated_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_summary(base_payload, archive_name=archive_name), encoding="utf-8")
    parsed_documents_path.write_text(
        json.dumps(
            [
                {
                    "path": document_path,
                    "title": preview_payload.get("document", {}).get("title"),
                    "file_type": file_type,
                    "source_archive": source_archive,
                    "parser_name": preview_payload.get("document", {}).get("parser"),
                    "segment_count": preview_payload.get("document", {}).get("segment_count"),
                    "character_count": character_count,
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    extraction_report_path.write_text(
        json.dumps(
            {
                "archive_id": archive_id,
                "archive_name": archive_name,
                "strict_mode": True,
                "summary": preview_payload.get("summary", {}),
                "document": preview_payload.get("document", {}),
                "chunk_stats": preview_payload.get("chunk_stats", []),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "base_path": base_path,
        "curated_path": curated_path,
        "markdown_path": markdown_path,
        "parsed_documents_path": parsed_documents_path,
        "extraction_report_path": extraction_report_path,
    }
