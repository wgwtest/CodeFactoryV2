import json
from pathlib import Path

import pytest

from app.archive_knowledge import builder as archive_builder
from app.extraction.service import ExtractionService
from app.knowledge_builder import SourceDocument
from app.parsing.models import ParsedDocument, ParsedSegment


def _segment(content: str) -> ParsedSegment:
    return ParsedSegment(
        heading=content[:32],
        content=content,
        anchor={"page": 1, "section": content[:32], "line_start": 1, "line_end": 1},
        block_type="paragraph",
    )


def test_collect_documents_rejects_non_docling_parser_for_formal_extraction(monkeypatch, tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    file_path = source_root / "sample.pdf"
    file_path.write_bytes(b"%PDF-1.4\n")

    class FakeParsingService:
        def parse_file(self, path: Path):
            del path
            return ParsedDocument(
                parser_name="pymupdf",
                parser_version="v3",
                segments=[_segment("fallback parser content")],
            )

    monkeypatch.setattr(archive_builder, "ParsingService", lambda *args, **kwargs: FakeParsingService())

    with pytest.raises(ValueError, match="Docling"):
        archive_builder.collect_documents([source_root], formal_extraction_mode=True)


def test_formal_extraction_requires_structured_llm(monkeypatch) -> None:
    segments = [_segment("国家空域系统运行协调说明")]

    def fake_build_structured_llm(*, output_schema):
        del output_schema
        raise ValueError("LLM api key is not configured")

    monkeypatch.setattr("app.extraction.service.build_structured_llm", fake_build_structured_llm)

    with pytest.raises(ValueError, match="结构化大模型"):
        ExtractionService(formal_extraction_mode=True).extract_document(
            document_id="doc-1",
            title="运行协调说明",
            file_path="source/runtime/coordination.docx",
            segments=segments,
        )


def test_build_archive_knowledge_writes_formal_extraction_report(monkeypatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    document = SourceDocument(
        path="doctrine/sample.pdf",
        title="Sample",
        file_type="pdf",
        source_archive="doctrine",
        text="国家空域系统",
        parser_name="docling_pdf",
        segment_count=1,
        segments=[_segment("国家空域系统")],
    )

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])
    monkeypatch.setattr(
        archive_builder,
        "collect_documents",
        lambda document_roots, formal_extraction_mode=False: [document],
    )

    def fake_build_knowledge_index(documents, extraction_service=None, diagnostics_collector=None):
        del extraction_service
        assert len(documents) == 1
        assert diagnostics_collector is not None
        diagnostics_collector.append(
            {
                "document_id": "doc-1",
                "title": "Sample",
                "file_path": "doctrine/sample.pdf",
                "parser_name": "docling_pdf",
                "llm_enrichment_used": True,
                "llm_provider": "openai_compatible",
                "llm_model": "gpt-4.1-mini",
                "strategy": "schema_rules+llm",
                "candidate_count": 1,
                "relation_count": 1,
            }
        )
        return {
            "summary": {
                "document_count": 1,
                "entity_count": 1,
                "event_count": 0,
                "process_count": 0,
                "relation_count": 1,
            },
            "documents": [
                {
                    "id": "doc-1",
                    "path": "doctrine/sample.pdf",
                    "title": "Sample",
                    "file_type": "pdf",
                    "source_archive": "doctrine",
                    "character_count": 6,
                }
            ],
            "entities": [
                {
                    "id": "entity-nas",
                    "name": "国家空域系统",
                    "category": "system_or_service",
                    "aliases": ["NAS"],
                    "document_ids": ["doc-1"],
                    "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
                }
            ],
            "events": [],
            "processes": [],
            "relations": [
                {
                    "type": "part_of",
                    "from": "entity-nas",
                    "to": "entity-nas-parent",
                }
            ],
        }

    monkeypatch.setattr(archive_builder, "build_knowledge_index", fake_build_knowledge_index)

    result = archive_builder.build_archive_knowledge(
        archive_id="strict-kb",
        archive_name="Strict KB",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    report = json.loads(result.extraction_report_path.read_text(encoding="utf-8"))

    assert report["archive_id"] == "strict-kb"
    assert report["strict_mode"] is True
    assert report["documents"][0]["parser_name"] == "docling_pdf"
    assert report["documents"][0]["llm_provider"] == "openai_compatible"
    assert report["documents"][0]["relation_count"] == 1
