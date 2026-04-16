import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.archive_knowledge.builder import persist_archive_outputs
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.extraction import ArchiveExtractionService
from app.extraction.schema import ExtractedCandidate, ExtractionBatch
from app.knowledge_builder import SourceDocument, _document_id
from app.parsing.models import ParsedDocument, ParsedSegment
from app.archive_knowledge.rebuild import reconcile_curated_payload


def test_aggregate_document_contributions_merges_items_and_relations():
    from app.archive_knowledge.document_artifacts import aggregate_document_contributions

    contributions = [
        {
            "document": {
                "id": "doc-1",
                "path": "docs/doc-1.docx",
                "title": "Document One",
                "file_type": "docx",
                "source_archive": "kb",
                "character_count": 1000,
                "parser_name": "docling_docx",
                "segment_count": 12,
            },
            "entities": [
                {
                    "id": "entity-国家空域系统",
                    "name": "国家空域系统",
                    "category": "system_or_service",
                    "aliases": ["NAS"],
                    "document_ids": ["doc-1"],
                    "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
                },
                {
                    "id": "entity-机场塔台管制",
                    "name": "机场塔台管制",
                    "category": "operational_node",
                    "aliases": ["ATCT"],
                    "document_ids": ["doc-1"],
                    "evidence": [{"document_id": "doc-1", "excerpt": "机场塔台管制"}],
                },
            ],
            "events": [],
            "processes": [],
            "relations": [
                {
                    "type": "part_of",
                    "source_name": "机场塔台管制",
                    "target_name": "国家空域系统",
                    "confidence": 0.9,
                    "evidence": "机场塔台管制属于国家空域系统",
                }
            ],
            "extraction": {
                "strategy": "schema_rules+llm",
                "candidate_count": 2,
                "relation_count": 1,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
            },
        },
        {
            "document": {
                "id": "doc-2",
                "path": "docs/doc-2.pdf",
                "title": "Document Two",
                "file_type": "pdf",
                "source_archive": "kb",
                "character_count": 1200,
                "parser_name": "docling_pdf",
                "segment_count": 20,
            },
            "entities": [
                {
                    "id": "entity-国家空域系统",
                    "name": "国家空域系统",
                    "category": "system_or_service",
                    "aliases": ["国家空域体系"],
                    "document_ids": ["doc-2"],
                    "evidence": [{"document_id": "doc-2", "excerpt": "国家空域体系"}],
                }
            ],
            "events": [],
            "processes": [
                {
                    "id": "process-管制移交",
                    "name": "管制移交",
                    "category": "domain_process",
                    "aliases": [],
                    "document_ids": ["doc-2"],
                    "evidence": [{"document_id": "doc-2", "excerpt": "管制移交"}],
                }
            ],
            "relations": [
                {
                    "type": "part_of",
                    "source_name": "管制移交",
                    "target_name": "国家空域系统",
                    "confidence": 0.8,
                    "evidence": "管制移交属于国家空域系统",
                }
            ],
            "extraction": {
                "strategy": "schema_rules+llm",
                "candidate_count": 2,
                "relation_count": 1,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
            },
        },
    ]

    payload = aggregate_document_contributions(contributions)

    assert payload["summary"] == {
        "document_count": 2,
        "entity_count": 2,
        "event_count": 0,
        "process_count": 1,
        "relation_count": 6,
    }
    nas = next(item for item in payload["entities"] if item["name"] == "国家空域系统")
    assert nas["document_ids"] == ["doc-1", "doc-2"]
    assert nas["aliases"] == ["NAS", "国家空域体系"]
    assert {"type": "part_of", "from": "entity-机场塔台管制", "to": "entity-国家空域系统", "confidence": 0.9, "evidence": "机场塔台管制属于国家空域系统"} in payload["relations"]
    assert {"type": "part_of", "from": "process-管制移交", "to": "entity-国家空域系统", "confidence": 0.8, "evidence": "管制移交属于国家空域系统"} in payload["relations"]


def test_reconcile_curated_payload_inherits_review_state_by_alias_overlap():
    base_payload = {
        "summary": {
            "document_count": 1,
            "entity_count": 1,
            "event_count": 0,
            "process_count": 0,
        },
        "documents": [
            {
                "id": "doc-1",
                "title": "Document One",
                "path": "docs/doc-1.docx",
                "file_type": "docx",
                "source_archive": "kb",
                "character_count": 1000,
            }
        ],
        "entities": [
            {
                "id": "entity-国家空域体系",
                "name": "国家空域体系",
                "category": "domain_concept",
                "aliases": ["NAS"],
                "document_ids": ["doc-1"],
                "evidence": [{"document_id": "doc-1", "excerpt": "国家空域体系"}],
            }
        ],
        "events": [],
        "processes": [],
        "relations": [],
    }
    previous_curated_payload = {
        "summary": base_payload["summary"],
        "documents": base_payload["documents"],
        "entities": [
            {
                "id": "entity-国家空域系统",
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "review_status": "approved",
                "document_ids": ["doc-1"],
                "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
            }
        ],
        "events": [],
        "processes": [],
        "relations": [],
    }

    reconciled = reconcile_curated_payload(base_payload, previous_curated_payload)

    assert reconciled["entities"][0]["name"] == "国家空域系统"
    assert reconciled["entities"][0]["category"] == "system_or_service"
    assert reconciled["entities"][0]["aliases"] == ["NAS"]
    assert reconciled["entities"][0]["review_status"] == "approved"


def test_formalize_document_rebuilds_archive_from_document_artifacts(tmp_path, monkeypatch):
    from app.archive_knowledge.document_artifacts import aggregate_document_contributions

    source_file = tmp_path / "doc-1.docx"
    source_file.write_text("stub", encoding="utf-8")

    contributions = [
        {
            "document": {
                "id": "doc-1",
                "path": "docs/doc-1.docx",
                "title": "Document One",
                "file_type": "docx",
                "source_archive": "kb",
                "character_count": 1000,
                "parser_name": "docling_docx",
                "segment_count": 10,
                "source_file_path": str(source_file),
            },
            "entities": [
                {
                    "id": "entity-国家空域系统",
                    "name": "国家空域系统",
                    "category": "system_or_service",
                    "aliases": ["NAS"],
                    "document_ids": ["doc-1"],
                    "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
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
        },
        {
            "document": {
                "id": "doc-2",
                "path": "docs/doc-2.pdf",
                "title": "Document Two",
                "file_type": "pdf",
                "source_archive": "kb",
                "character_count": 1200,
                "parser_name": "docling_pdf",
                "segment_count": 12,
                "source_file_path": str(tmp_path / "doc-2.pdf"),
            },
            "entities": [],
            "events": [],
            "processes": [
                {
                    "id": "process-管制移交",
                    "name": "管制移交",
                    "category": "domain_process",
                    "aliases": [],
                    "document_ids": ["doc-2"],
                    "evidence": [{"document_id": "doc-2", "excerpt": "管制移交"}],
                }
            ],
            "relations": [],
            "extraction": {
                "strategy": "schema_rules+llm",
                "candidate_count": 1,
                "relation_count": 0,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
            },
        },
    ]

    repository = DocumentArtifactRepository(tmp_path)
    repository.replace_all("kb", contributions)
    persist_archive_outputs(
        archive_id="kb",
        archive_name="测试知识库",
        source_dir=tmp_path,
        extract_root=tmp_path,
        output_root=tmp_path,
        knowledge=aggregate_document_contributions(contributions),
        contributions=contributions,
        formal_extraction_mode=True,
    )

    def fake_parse_file(self, file_path: Path, file_name: str | None = None):
        del self, file_name
        assert file_path == source_file
        return ParsedDocument(
            parser_name="docling_docx",
            parser_version="v1",
            segments=[
                ParsedSegment(
                    heading="Section 1",
                    content="更新后的国家空域系统与空域协同平台",
                    anchor={"page": 1, "section": "Section 1", "line_start": 1, "line_end": 1},
                )
            ],
        )

    def fake_extract_document(self, *, document_id, title, file_path, segments):
        del self, title, file_path, segments
        return ExtractionBatch(
            document_id=document_id,
            title="Document One",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="国家空域系统",
                    payload={"category": "system_or_service", "aliases": ["NAS"], "evidence": "国家空域系统"},
                ),
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="空域协同平台",
                    payload={"category": "system_or_service", "aliases": [], "evidence": "空域协同平台"},
                ),
            ],
            relations=[],
            metadata={"llm_enrichment_used": True, "llm_provider": "deepseek", "llm_model": "deepseek-chat"},
        )

    monkeypatch.setattr("app.parsing.service.ParsingService.parse_file", fake_parse_file)
    monkeypatch.setattr("app.extraction.service.ExtractionService.extract_document", fake_extract_document)

    result = ArchiveExtractionService(tmp_path).formalize_document(
        "kb",
        document_id="doc-1",
        source_dir=tmp_path,
        extract_root=tmp_path,
        archive_name="测试知识库",
    )

    assert result["mode"] == "incremental_merge"
    assert result["summary"] == {
        "document_count": 2,
        "entity_count": 2,
        "event_count": 0,
        "process_count": 1,
        "relation_count": 3,
    }

    payload = json.loads((tmp_path / "kb-knowledge.json").read_text(encoding="utf-8"))
    entity_names = {item["name"] for item in payload["entities"]}
    assert entity_names == {"国家空域系统", "空域协同平台"}
    assert any(item["name"] == "管制移交" for item in payload["processes"])


def test_document_artifact_repository_excludes_document_without_deleting_artifact(tmp_path):
    contribution_doc_1 = {
        "document": {
            "id": "doc-1",
            "path": "docs/doc-1.docx",
            "title": "Document One",
            "file_type": "docx",
            "source_archive": "kb",
            "character_count": 1000,
            "parser_name": "docling_docx",
            "segment_count": 10,
            "source_file_path": str(tmp_path / "doc-1.docx"),
        },
        "entities": [
            {
                "id": "entity-国家空域系统",
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "document_ids": ["doc-1"],
                "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
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
    contribution_doc_2 = {
        "document": {
            "id": "doc-2",
            "path": "docs/doc-2.docx",
            "title": "Document Two",
            "file_type": "docx",
            "source_archive": "kb",
            "character_count": 800,
            "parser_name": "docling_docx",
            "segment_count": 8,
            "source_file_path": str(tmp_path / "doc-2.docx"),
        },
        "entities": [],
        "events": [],
        "processes": [
            {
                "id": "process-管制移交",
                "name": "管制移交",
                "category": "domain_process",
                "aliases": [],
                "document_ids": ["doc-2"],
                "evidence": [{"document_id": "doc-2", "excerpt": "管制移交"}],
            }
        ],
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

    repository = DocumentArtifactRepository(tmp_path)
    repository.replace_all("kb", [contribution_doc_1, contribution_doc_2])

    repository.set_included_in_archive("kb", "doc-1", included_in_archive=False)

    remaining = repository.load_contributions("kb", included_only=True)
    removed = repository.load_document_contribution("kb", "doc-1")
    manifest_row = repository.get_document_source_info("kb", "doc-1")

    assert [item["document"]["id"] for item in remaining] == ["doc-2"]
    assert removed is not None
    assert removed["document"]["id"] == "doc-1"
    assert manifest_row is not None
    assert manifest_row["included_in_archive"] is False


def test_remove_document_rebuilds_archive_without_deleting_document_artifact(tmp_path):
    from app.archive_knowledge.document_artifacts import aggregate_document_contributions

    contribution_doc_1 = {
        "document": {
            "id": "doc-1",
            "path": "docs/doc-1.docx",
            "title": "Document One",
            "file_type": "docx",
            "source_archive": "kb",
            "character_count": 1000,
            "parser_name": "docling_docx",
            "segment_count": 10,
            "source_file_path": str(tmp_path / "doc-1.docx"),
        },
        "entities": [
            {
                "id": "entity-国家空域系统",
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "document_ids": ["doc-1"],
                "evidence": [{"document_id": "doc-1", "excerpt": "国家空域系统"}],
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
    contribution_doc_2 = {
        "document": {
            "id": "doc-2",
            "path": "docs/doc-2.docx",
            "title": "Document Two",
            "file_type": "docx",
            "source_archive": "kb",
            "character_count": 800,
            "parser_name": "docling_docx",
            "segment_count": 8,
            "source_file_path": str(tmp_path / "doc-2.docx"),
        },
        "entities": [],
        "events": [],
        "processes": [
            {
                "id": "process-管制移交",
                "name": "管制移交",
                "category": "domain_process",
                "aliases": [],
                "document_ids": ["doc-2"],
                "evidence": [{"document_id": "doc-2", "excerpt": "管制移交"}],
            }
        ],
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

    repository = DocumentArtifactRepository(tmp_path)
    repository.replace_all("kb", [contribution_doc_1, contribution_doc_2])
    persist_archive_outputs(
        archive_id="kb",
        archive_name="测试知识库",
        source_dir=tmp_path,
        extract_root=tmp_path,
        output_root=tmp_path,
        knowledge=aggregate_document_contributions([contribution_doc_1, contribution_doc_2]),
        contributions=[contribution_doc_1, contribution_doc_2],
        formal_extraction_mode=True,
    )

    result = ArchiveExtractionService(tmp_path).remove_document(
        "kb",
        document_id="doc-1",
        source_dir=tmp_path,
        extract_root=tmp_path,
        archive_name="测试知识库",
    )

    assert result["action"] == "remove"
    assert result["document_id"] == "doc-1"
    assert result["document_included"] is False
    assert result["summary"] == {
        "document_count": 1,
        "entity_count": 0,
        "event_count": 0,
        "process_count": 1,
        "relation_count": 1,
    }

    payload = json.loads((tmp_path / "kb-knowledge.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in payload["documents"]] == ["doc-2"]
    assert payload["processes"][0]["name"] == "管制移交"
    assert DocumentArtifactRepository(tmp_path).load_document_contribution("kb", "doc-1") is not None


def test_build_archive_knowledge_persists_completed_formal_documents_before_later_failure(tmp_path, monkeypatch):
    from app.archive_knowledge import builder as archive_builder

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    documents = [
        _build_discovered_document(source_dir, "alpha.docx", "Alpha", "alpha digest"),
        _build_discovered_document(source_dir, "bravo.docx", "Bravo", "bravo digest"),
        _build_discovered_document(source_dir, "charlie.docx", "Charlie", "charlie digest"),
    ]
    contributions = {
        document.path: _build_document_contribution_payload(
            _build_source_document(document),
            entity_name=f"{document.title}实体",
        )
        for document in documents[:2]
    }

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])
    monkeypatch.setattr(archive_builder, "discover_documents", lambda *args, **kwargs: documents)

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        state = DocumentArtifactRepository(output_root).load_build_state("kb")
        assert state is not None
        assert state["status"] == "running"
        return _build_source_document(document)

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)

    def fake_build_document_contribution(document, extraction_service=None, *, document_id=None):
        del extraction_service, document_id
        if document.path == documents[2].path:
            raise ValueError("正式知识库抽取要求使用结构化大模型抽取，但当前调用失败：Request timed out.")
        return contributions[document.path]

    monkeypatch.setattr(archive_builder, "build_document_contribution", fake_build_document_contribution)

    with pytest.raises(ValueError, match="Request timed out"):
        archive_builder.build_archive_knowledge(
            archive_id="kb",
            archive_name="测试知识库",
            source_dir=source_dir,
            extract_root=extract_root,
            output_root=output_root,
            formal_extraction_mode=True,
        )

    repository = DocumentArtifactRepository(output_root)
    stored_document_ids = [item["document_id"] for item in repository.list_documents("kb")]
    assert stored_document_ids == [_document_id(documents[0].path), _document_id(documents[1].path)]

    build_state = repository.load_build_state("kb")
    assert build_state is not None
    assert build_state["status"] == "failed"
    assert build_state["completed_document_ids"] == stored_document_ids
    assert build_state["failed_document_id"] == _document_id(documents[2].path)
    assert build_state["pending_document_ids"] == [_document_id(documents[2].path)]
    assert (output_root / "kb-knowledge.json").exists() is False


def test_build_archive_knowledge_resumes_from_checkpoint_without_reextracting_completed_documents(tmp_path, monkeypatch):
    from app.archive_knowledge import builder as archive_builder

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    extract_root = tmp_path / "extract"
    output_root = tmp_path / "output"

    documents = [
        _build_discovered_document(source_dir, "alpha.docx", "Alpha", "alpha digest"),
        _build_discovered_document(source_dir, "bravo.docx", "Bravo", "bravo digest"),
        _build_discovered_document(source_dir, "charlie.docx", "Charlie", "charlie digest"),
    ]
    repository = DocumentArtifactRepository(output_root)
    repository.upsert("kb", _build_document_contribution_payload(_build_source_document(documents[0]), entity_name="Alpha实体"))
    repository.upsert("kb", _build_document_contribution_payload(_build_source_document(documents[1]), entity_name="Bravo实体"))
    repository.save_build_state(
        "kb",
        {
            "archive_id": "kb",
            "status": "failed",
            "mode": "formal",
            "expected_document_count": 3,
            "completed_document_ids": [_document_id(documents[0].path), _document_id(documents[1].path)],
            "pending_document_ids": [_document_id(documents[2].path)],
            "failed_document_id": _document_id(documents[2].path),
            "documents": [
                {
                    "document_id": _document_id(document.path),
                    "path": document.path,
                    "title": document.title,
                    "state": "completed" if index < 2 else "pending",
                    "source_digest": document.source_digest,
                }
                for index, document in enumerate(documents)
            ],
        },
    )

    monkeypatch.setattr(archive_builder, "extract_archives", lambda *args, **kwargs: None)
    monkeypatch.setattr(archive_builder, "resolve_document_roots", lambda source, extract: [source])
    monkeypatch.setattr(archive_builder, "discover_documents", lambda *args, **kwargs: documents)

    parsed_document_paths: list[str] = []
    called_document_paths: list[str] = []

    def fake_parse_discovered_document(document, *, formal_extraction_mode):
        assert formal_extraction_mode is True
        parsed_document_paths.append(document.path)
        return _build_source_document(document)

    monkeypatch.setattr(archive_builder, "parse_discovered_document", fake_parse_discovered_document)

    def fake_build_document_contribution(document, extraction_service=None, *, document_id=None):
        del extraction_service, document_id
        called_document_paths.append(document.path)
        return _build_document_contribution_payload(document, entity_name=f"{document.title}实体")

    monkeypatch.setattr(archive_builder, "build_document_contribution", fake_build_document_contribution)

    result = archive_builder.build_archive_knowledge(
        archive_id="kb",
        archive_name="测试知识库",
        source_dir=source_dir,
        extract_root=extract_root,
        output_root=output_root,
        formal_extraction_mode=True,
    )

    assert parsed_document_paths == [documents[2].path]
    assert called_document_paths == [documents[2].path]
    assert result.summary == {
        "document_count": 3,
        "entity_count": 3,
        "event_count": 0,
        "process_count": 0,
        "relation_count": 3,
    }

    build_state = repository.load_build_state("kb")
    assert build_state is not None
    assert build_state["status"] == "completed"
    assert build_state["failed_document_id"] is None
    assert build_state["pending_document_ids"] == []
    assert build_state["completed_document_ids"] == [_document_id(document.path) for document in documents]


def _build_discovered_document(source_dir: Path, relative_name: str, title: str, source_digest: str):
    file_path = source_dir / relative_name
    file_path.write_text(title, encoding="utf-8")
    return SimpleNamespace(
        path=f"docs/{relative_name}",
        title=title,
        file_type="docx",
        source_archive="kb",
        source_file_path=str(file_path),
        source_digest=source_digest,
    )


def _build_source_document(document) -> SourceDocument:
    return SourceDocument(
        path=document.path,
        title=document.title,
        file_type="docx",
        source_archive="kb",
        text=f"{document.title} 内容",
        parser_name="docling_docx",
        segment_count=1,
        segments=[
            ParsedSegment(
                heading=document.title,
                content=f"{document.title} 内容",
                anchor={"page": 1, "section": document.title, "line_start": 1, "line_end": 1},
            )
        ],
        source_file_path=document.source_file_path,
        source_digest=document.source_digest,
    )


def _build_document_contribution_payload(document: SourceDocument, *, entity_name: str) -> dict:
    document_id = _document_id(document.path)
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
                "id": f"entity-{entity_name}",
                "name": entity_name,
                "category": "system_or_service",
                "aliases": [],
                "document_ids": [document_id],
                "evidence": [{"document_id": document_id, "excerpt": entity_name}],
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
