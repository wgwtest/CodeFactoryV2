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


def _simple_contribution(document: SourceDocument, *, document_id: str) -> dict:
    return {
        "document": {
            "id": document_id,
            "path": document.path,
            "title": document.title,
            "file_type": document.file_type,
            "source_archive": document.source_archive,
            "character_count": len(document.text),
            "parser_name": document.parser_name,
            "segment_count": document.segment_count,
            "source_file_path": document.source_file_path,
            "source_digest": document.source_digest,
        },
        "entities": [
            {
                "id": "entity-nas",
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": "国家空域系统"}],
            }
        ],
        "events": [],
        "processes": [],
        "relations": [],
        "extraction": {
            "strategy": "schema_rules+llm",
            "candidate_count": 1,
            "relation_count": 0,
            "llm_enrichment_used": True,
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
        },
    }


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


def test_discover_documents_skips_spreadsheets_for_formal_extraction_and_records_warning(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    pdf_path = source_root / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    spreadsheet_path = source_root / "sample.xls"
    spreadsheet_path.write_bytes(b"spreadsheet")

    warnings: list[dict] = []
    documents = archive_builder.discover_documents(
        [source_root],
        formal_extraction_mode=True,
        warnings_collector=warnings,
    )

    assert [document.path for document in documents] == ["sample.pdf"]
    assert warnings == [
        {
            "code": "unsupported_spreadsheet_skipped",
            "severity": "warning",
            "file_path": str(spreadsheet_path),
            "file_type": "xls",
            "message": f"正式知识库抽取已跳过表格文件（当前未接入 Docling 表格链路）：{spreadsheet_path}",
        }
    ]


def test_load_runtime_acceptance_slow_profile_reads_source_config(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / archive_builder.RUNTIME_SLOW_PROFILE_FILENAME).write_text(
        json.dumps(
            {
                "enabled": True,
                "stage_delay_ms": 900,
                "chunk_delay_ms": 180,
                "document_delay_ms": 600,
            }
        ),
        encoding="utf-8",
    )

    profile = archive_builder.load_runtime_acceptance_slow_profile(source_root)

    assert profile.enabled is True
    assert profile.stage_delay_seconds == 0.9
    assert profile.chunk_delay_seconds == 0.18
    assert profile.document_delay_seconds == 0.6


def test_load_runtime_acceptance_slow_profile_defaults_to_disabled(tmp_path: Path) -> None:
    profile = archive_builder.load_runtime_acceptance_slow_profile(tmp_path)

    assert profile.enabled is False
    assert profile.stage_delay_seconds == 0
    assert profile.chunk_delay_seconds == 0
    assert profile.document_delay_seconds == 0


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
        lambda document_roots, formal_extraction_mode=False, warnings_collector=None: [document],
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
    assert report["warning_count"] == 0
    assert report["warnings"] == []
    assert report["documents"][0]["parser_name"] == "docling_pdf"
    assert report["documents"][0]["llm_provider"] == "openai_compatible"
    assert report["documents"][0]["relation_count"] == 1


def test_build_archive_knowledge_records_skipped_spreadsheet_warnings(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    pdf_path = source_dir / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    spreadsheet_path = source_dir / "sample.xls"
    spreadsheet_path.write_bytes(b"spreadsheet")

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        return SourceDocument(
            path=document.path,
            title=document.title,
            file_type=document.file_type,
            source_archive=document.source_archive,
            text="国家空域系统",
            parser_name="docling_pdf",
            segment_count=1,
            segments=[_segment("国家空域系统")],
            source_file_path=document.source_file_path,
            source_digest=document.source_digest,
        )

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)
    monkeypatch.setattr(
        archive_builder,
        "build_document_contribution",
        lambda document, extraction_service=None, *, document_id=None, policy_snapshot=None: _simple_contribution(
            document, document_id="doc-1"
        ),
    )

    result = archive_builder.build_archive_knowledge(
        archive_id="strict-kb",
        archive_name="Strict KB",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    report = json.loads(result.extraction_report_path.read_text(encoding="utf-8"))
    build_state = json.loads((output_root / "strict-kb-document-build-state.json").read_text(encoding="utf-8"))

    assert result.summary["document_count"] == 1
    assert report["warning_count"] == 1
    assert report["warnings"][0]["file_path"] == str(spreadsheet_path)
    assert report["warnings"][0]["file_type"] == "xls"
    assert build_state["warning_count"] == 1
    assert build_state["warnings"][0]["message"].endswith(str(spreadsheet_path))


def test_build_archive_knowledge_skips_docling_failed_pdf_and_continues(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    broken_pdf_path = source_dir / "broken.pdf"
    broken_pdf_path.write_bytes(b"%PDF-1.4\nbroken")
    good_pdf_path = source_dir / "good.pdf"
    good_pdf_path.write_bytes(b"%PDF-1.4\ngood")

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        if document.title == "broken":
            raise ValueError(
                f"正式知识库抽取要求 PDF 使用 Docling 解析，但当前文件未能通过 Docling 成功解析：{document.source_file_path}"
            )
        return SourceDocument(
            path=document.path,
            title=document.title,
            file_type=document.file_type,
            source_archive=document.source_archive,
            text="国家空域系统",
            parser_name="docling_pdf",
            segment_count=1,
            segments=[_segment("国家空域系统")],
            source_file_path=document.source_file_path,
            source_digest=document.source_digest,
        )

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)
    monkeypatch.setattr(
        archive_builder,
        "build_document_contribution",
        lambda document, extraction_service=None, *, document_id=None, policy_snapshot=None: _simple_contribution(
            document, document_id="doc-good"
        ),
    )

    result = archive_builder.build_archive_knowledge(
        archive_id="strict-kb",
        archive_name="Strict KB",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    report = json.loads(result.extraction_report_path.read_text(encoding="utf-8"))
    build_state = json.loads((output_root / "strict-kb-document-build-state.json").read_text(encoding="utf-8"))

    assert result.summary["document_count"] == 1
    assert report["warning_count"] == 1
    assert report["warnings"][0]["code"] == "docling_pdf_skipped"
    assert report["warnings"][0]["file_path"] == str(broken_pdf_path)
    assert "Docling" in report["warnings"][0]["message"]
    assert build_state["status"] == "completed"
    assert len(build_state["skipped_document_ids"]) == 1
    assert build_state["warning_count"] == 1
    skipped_row = next(item for item in build_state["documents"] if item["title"] == "broken")
    assert skipped_row["state"] == "skipped"


def test_build_archive_knowledge_skips_docling_failed_docx_and_continues(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    broken_docx_path = source_dir / "broken.docx"
    broken_docx_path.write_bytes(b"broken")
    good_docx_path = source_dir / "good.docx"
    good_docx_path.write_bytes(b"good")

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        if document.title == "broken":
            raise ValueError(
                f"正式知识库抽取要求 DOC/DOCX 使用 Docling 解析，但当前文件未能通过 Docling 成功解析：{document.source_file_path}"
            )
        return SourceDocument(
            path=document.path,
            title=document.title,
            file_type=document.file_type,
            source_archive=document.source_archive,
            text="国家空域系统",
            parser_name="docling_docx",
            segment_count=1,
            segments=[_segment("国家空域系统")],
            source_file_path=document.source_file_path,
            source_digest=document.source_digest,
        )

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)
    monkeypatch.setattr(
        archive_builder,
        "build_document_contribution",
        lambda document, extraction_service=None, *, document_id=None, policy_snapshot=None: _simple_contribution(
            document, document_id="doc-good"
        ),
    )

    result = archive_builder.build_archive_knowledge(
        archive_id="strict-kb",
        archive_name="Strict KB",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    report = json.loads(result.extraction_report_path.read_text(encoding="utf-8"))
    build_state = json.loads((output_root / "strict-kb-document-build-state.json").read_text(encoding="utf-8"))

    assert result.summary["document_count"] == 1
    assert report["warning_count"] == 1
    assert report["warnings"][0]["code"] == "docling_docx_skipped"
    assert report["warnings"][0]["file_path"] == str(broken_docx_path)
    assert "DOCX" in report["warnings"][0]["message"]
    assert build_state["status"] == "completed"
    assert len(build_state["skipped_document_ids"]) == 1
    assert build_state["warning_count"] == 1
    skipped_row = next(item for item in build_state["documents"] if item["title"] == "broken")
    assert skipped_row["state"] == "skipped"


def test_build_archive_knowledge_skips_doc_conversion_failure_and_continues(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    broken_doc_path = source_dir / "broken.doc"
    broken_doc_path.write_bytes(b"broken")
    good_docx_path = source_dir / "good.docx"
    good_docx_path.write_bytes(b"good")

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        if document.title == "broken":
            cause = FileNotFoundError("[WinError 2] 系统找不到指定的文件。")
            raise ValueError(
                f"正式知识库抽取失败：{document.source_file_path} ([WinError 2] 系统找不到指定的文件。)"
            ) from cause
        return SourceDocument(
            path=document.path,
            title=document.title,
            file_type=document.file_type,
            source_archive=document.source_archive,
            text="国家空域系统",
            parser_name="docling_docx",
            segment_count=1,
            segments=[_segment("国家空域系统")],
            source_file_path=document.source_file_path,
            source_digest=document.source_digest,
        )

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)
    monkeypatch.setattr(
        archive_builder,
        "build_document_contribution",
        lambda document, extraction_service=None, *, document_id=None, policy_snapshot=None: _simple_contribution(
            document, document_id="doc-good"
        ),
    )

    result = archive_builder.build_archive_knowledge(
        archive_id="strict-kb",
        archive_name="Strict KB",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    report = json.loads(result.extraction_report_path.read_text(encoding="utf-8"))
    build_state = json.loads((output_root / "strict-kb-document-build-state.json").read_text(encoding="utf-8"))

    assert result.summary["document_count"] == 1
    assert report["warning_count"] == 1
    assert report["warnings"][0]["code"] == "doc_conversion_skipped"
    assert report["warnings"][0]["file_path"] == str(broken_doc_path)
    assert "DOC 转 DOCX 失败" in report["warnings"][0]["message"]
    assert build_state["status"] == "completed"
    assert len(build_state["skipped_document_ids"]) == 1
    assert build_state["warning_count"] == 1
    skipped_row = next(item for item in build_state["documents"] if item["title"] == "broken")
    assert skipped_row["state"] == "skipped"
