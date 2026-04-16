import pytest

from app.config import settings
from app.extraction.service import ExtractionService
from app.extraction.schema import ExtractedCandidate, ExtractedRelation, ExtractionBatch
from app.knowledge_builder import SourceDocument, build_knowledge_index
from app.parsing.models import ParsedSegment


def _set_setting(name: str, value) -> None:
    object.__setattr__(settings, name, value)


@pytest.fixture(autouse=True)
def _reset_extraction_settings():
    snapshot = {
        "llm_enrichment_enabled": settings.llm_enrichment_enabled,
        "formal_chunk_segment_threshold": settings.formal_chunk_segment_threshold,
        "formal_chunk_char_threshold": settings.formal_chunk_char_threshold,
        "formal_chunk_char_limit": settings.formal_chunk_char_limit,
        "llm_provider": settings.llm_provider,
        "llm_api_key": settings.llm_api_key,
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "openai_api_key": settings.openai_api_key,
    }
    _set_setting("llm_enrichment_enabled", False)
    _set_setting("formal_chunk_segment_threshold", 120)
    _set_setting("formal_chunk_char_threshold", 50000)
    _set_setting("formal_chunk_char_limit", 12000)
    yield
    for name, value in snapshot.items():
        _set_setting(name, value)


def test_extractor_builds_nas_artifact_operational_relationships() -> None:
    segments = [
        ParsedSegment(
            heading="标题",
            content="联邦航空管理局 国家空域系统企业级体系架构(NAS EA) 空中交通组织 国家空域系统(NAS) 运行节点关联关系图（OV-2） 当前情况",
            anchor={"page": 1, "section": "标题", "line_start": 1, "line_end": 1},
        ),
        ParsedSegment(
            heading="元数据",
            content="| 批准机构 | 联邦航空管理局（FAA） |",
            anchor={"page": 1, "section": "元数据", "line_start": 2, "line_end": 2},
            block_type="table_row",
        ),
        ParsedSegment(
            heading="节点图例",
            content="| ATCT | 机场塔台管制 |",
            anchor={"page": 1, "section": "节点图例", "line_start": 3, "line_end": 3},
            block_type="table_row",
        ),
        ParsedSegment(
            heading="节点图例",
            content="| AIRCRAFT | 航空器 |",
            anchor={"page": 1, "section": "节点图例", "line_start": 4, "line_end": 4},
            block_type="table_row",
        ),
        ParsedSegment(
            heading="交换关系",
            content="| Tower-Aircraft I/O 1 Pre-Departure Clearance I/O 2 Taxi Instructions | 塔台——航空器 输入/输出 1：预离场许可 输入/输出 2：滑行指令 |",
            anchor={"page": 1, "section": "交换关系", "line_start": 5, "line_end": 5},
            block_type="table_row",
        ),
        ParsedSegment(
            heading="交换关系",
            content="| IEX Name: ATC Message | IEX 名称：空中交通管制消息 |",
            anchor={"page": 1, "section": "交换关系", "line_start": 6, "line_end": 6},
            block_type="table_row",
        ),
    ]

    batch = ExtractionService().extract_document(
        document_id="doc-ov2",
        title="10002024_NAS-EA-OV-2-As-Is-V1.0-091311",
        file_path="source/[3]NAS体系结构产品/As Is/10002024_NAS-EA-OV-2-As-Is-V1.0-091311.docx",
        segments=segments,
    )

    candidate_index = {(item.item_type, item.canonical_name): item for item in batch.candidates}
    relation_index = {
        (relation.relation_type, relation.source_name, relation.target_name)
        for relation in batch.relations
    }

    assert ("entity", "OV-2") in candidate_index
    assert candidate_index[("entity", "OV-2")].payload["category"] == "architecture_artifact"
    assert ("entity", "国家空域系统") in candidate_index
    assert ("entity", "联邦航空管理局") in candidate_index
    assert ("entity", "机场塔台管制") in candidate_index
    assert ("entity", "航空器") in candidate_index
    assert ("entity", "预离场许可") in candidate_index
    assert ("event", "当前状态（As Is）") in candidate_index

    assert ("describes", "OV-2", "国家空域系统") in relation_index
    assert ("owned_by", "OV-2", "联邦航空管理局") in relation_index
    assert ("part_of", "机场塔台管制", "国家空域系统") in relation_index
    assert ("operational_exchange", "机场塔台管制", "航空器") in relation_index
    assert ("participates_in_exchange", "机场塔台管制", "预离场许可") in relation_index
    assert ("participates_in_exchange", "航空器", "预离场许可") in relation_index


def test_extractor_merges_llm_enrichment_when_enabled(monkeypatch) -> None:
    segments = [
        ParsedSegment(
            heading="标题",
            content="国家空域系统运行协调说明",
            anchor={"page": 1, "section": "标题", "line_start": 1, "line_end": 1},
        )
    ]

    def fake_llm_enrichment(self, *, document_id, title, file_path, segments, base_batch, structured_llm_bundle):
        del self, document_id, title, file_path, segments, base_batch, structured_llm_bundle
        return ExtractionBatch(
            document_id="doc-1",
            title="运行协调说明",
            strategy="llamaindex_openai",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="塔台放行协调",
                    confidence=0.96,
                    payload={
                        "category": "domain_concept",
                        "aliases": ["放行协调"],
                        "evidence": "塔台放行协调用于统一起飞许可分发。",
                    },
                )
            ],
            relations=[
                ExtractedRelation(
                    relation_type="part_of",
                    source_name="塔台放行协调",
                    target_name="国家空域系统",
                    confidence=0.91,
                    payload={"evidence": "塔台放行协调属于国家空域系统运行能力。"},
                )
            ],
            metadata={"provider": "fake-llm"},
        )

    monkeypatch.setattr(ExtractionService, "_try_llm_enrichment", fake_llm_enrichment, raising=False)

    batch = ExtractionService().extract_document(
        document_id="doc-1",
        title="运行协调说明",
        file_path="source/runtime/coordination.docx",
        segments=segments,
    )

    candidate_index = {(item.item_type, item.canonical_name): item for item in batch.candidates}
    relation_index = {
        (relation.relation_type, relation.source_name, relation.target_name)
        for relation in batch.relations
    }

    assert ("entity", "塔台放行协调") in candidate_index
    assert ("part_of", "塔台放行协调", "国家空域系统") in relation_index
    assert batch.metadata["llm_enrichment_used"] is True
    assert batch.strategy == "schema_rules+llm"


def test_extractor_uses_provider_adapter_without_legacy_openai_key(monkeypatch) -> None:
    segments = [
        ParsedSegment(
            heading="标题",
            content="国家空域系统运行协调说明",
            anchor={"page": 1, "section": "标题", "line_start": 1, "line_end": 1},
        )
    ]

    _set_setting("llm_enrichment_enabled", True)
    _set_setting("llm_provider", "deepseek")
    _set_setting("llm_api_key", "deepseek-test-key")
    _set_setting("llm_base_url", "https://api.deepseek.com/v1")
    _set_setting("llm_model", "deepseek-chat")
    _set_setting("openai_api_key", None)

    class FakeStructuredLLM:
        def complete(self, prompt: str):
            del prompt
            return type(
                "FakeResponse",
                (),
                {
                    "raw": {
                        "candidates": [
                            {
                                "item_type": "entity",
                                "canonical_name": "塔台放行协调",
                                "category": "domain_concept",
                                "aliases": ["放行协调"],
                                "evidence": "塔台放行协调属于国家空域系统运行协调能力。",
                                "confidence": 0.96,
                            }
                        ],
                        "relations": [
                            {
                                "relation_type": "part_of",
                                "source_name": "塔台放行协调",
                                "target_name": "国家空域系统",
                                "evidence": "塔台放行协调属于国家空域系统运行能力。",
                                "confidence": 0.9,
                            }
                        ],
                        "notes": "provider=deepseek",
                    }
                },
            )()

    captured: dict[str, str] = {}

    def fake_build_structured_llm(*, output_schema):
        captured["schema"] = output_schema.__name__
        return FakeStructuredLLM(), {"provider": "deepseek", "model": "deepseek-chat"}

    monkeypatch.setattr(
        "app.extraction.service.build_structured_llm",
        fake_build_structured_llm,
    )

    batch = ExtractionService().extract_document(
        document_id="doc-1",
        title="运行协调说明",
        file_path="source/runtime/coordination.docx",
        segments=segments,
    )

    candidate_index = {(item.item_type, item.canonical_name): item for item in batch.candidates}
    assert captured["schema"] == "StructuredExtractionResponse"
    assert ("entity", "塔台放行协调") in candidate_index
    assert batch.metadata["llm_enrichment_used"] is True
    assert batch.metadata["llm_provider"] == "deepseek"


def test_build_llm_supports_deepseek_metadata() -> None:
    from app.integrations.llm import build_llm
    from llama_index.core.types import PydanticProgramMode

    llm, metadata = build_llm(
        provider="deepseek",
        api_key="deepseek-test-key",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        context_window=64000,
        supports_function_calling=True,
        supports_chat=True,
        temperature=0,
    )

    assert metadata["provider"] == "deepseek"
    assert metadata["model"] == "deepseek-chat"
    assert llm.metadata.model_name == "deepseek-chat"
    assert llm.metadata.context_window == 64000
    assert llm.metadata.is_chat_model is True
    assert llm.metadata.is_function_calling_model is True
    assert llm.pydantic_program_mode == PydanticProgramMode.LLM


def test_select_llm_segments_spreads_across_long_document() -> None:
    segments = [
        ParsedSegment(
            heading=f"第{i}页标题",
            content=f"第{i}页领域知识说明，包含实体、事件、流程与关系。",
            anchor={"page": i, "section": f"第{i}页标题", "line_start": 1, "line_end": 1},
        )
        for i in range(1, 61)
    ]

    selected = ExtractionService._select_llm_segments(segments)
    selected_pages = [int(segment.anchor["page"]) for segment in selected]

    assert len(selected) <= settings.llm_enrichment_segment_limit
    assert 1 in selected_pages
    assert 60 in selected_pages


def test_formal_extraction_uses_chunked_path_for_long_document(monkeypatch) -> None:
    _set_setting("formal_chunk_segment_threshold", 3)
    _set_setting("formal_chunk_char_threshold", 100000)

    segments = [
        ParsedSegment(
            heading=f"第{i}章",
            content="领域内容 " * 40,
            anchor={"page": i, "section": f"第{i}章", "line_start": 1, "line_end": 6},
            block_type="paragraph",
        )
        for i in range(1, 5)
    ]

    calls = {"chunked": 0, "standard": 0}

    def fake_chunked(self, **kwargs):
        del self, kwargs
        calls["chunked"] += 1
        return ExtractionBatch(
            document_id="doc-1",
            title="长文档",
            candidates=[],
            relations=[],
            metadata={"chunking_used": True, "chunk_count": 2},
        )

    def fake_standard(self, **kwargs):
        del self, kwargs
        calls["standard"] += 1
        return ExtractionBatch(document_id="doc-1", title="长文档", candidates=[], relations=[], metadata={})

    monkeypatch.setattr(ExtractionService, "_extract_with_chunks", fake_chunked)
    monkeypatch.setattr(ExtractionService, "_extract_standard_document", fake_standard)

    batch = ExtractionService(formal_extraction_mode=True).extract_document(
        document_id="doc-1",
        title="长文档",
        file_path="runtime/long.pdf",
        segments=segments,
    )

    assert calls == {"chunked": 1, "standard": 0}
    assert batch.metadata["chunking_used"] is True


def test_chunked_formal_extraction_records_source_refs(monkeypatch) -> None:
    _set_setting("formal_chunk_segment_threshold", 2)
    _set_setting("formal_chunk_char_threshold", 10)
    _set_setting("formal_chunk_char_limit", 200)

    segments = [
        ParsedSegment(
            heading="第一章",
            content="信号支援体系说明 " * 20,
            anchor={"page": 1, "section": "第一章", "line_start": 1, "line_end": 8},
            block_type="paragraph",
        ),
        ParsedSegment(
            heading="第二章",
            content="信号支援体系补充 " * 20,
            anchor={"page": 2, "section": "第二章", "line_start": 1, "line_end": 8},
            block_type="paragraph",
        ),
    ]

    def fake_extract_chunk_batch(self, *, document_id, title, file_path, source_document, chunk, structured_llm_bundle):
        del self, document_id, title, file_path, source_document, structured_llm_bundle
        source_ref = {
            "chunk_id": chunk.chunk_id,
            "chunk_heading": chunk.heading,
            "segment_ids": chunk.segment_ids,
            "anchors": chunk.anchors,
        }
        return ExtractionBatch(
            document_id="doc-1",
            title="信号支援",
            strategy="schema_rules+llm",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="信号支援",
                    confidence=0.9,
                    payload={
                        "category": "domain_concept",
                        "aliases": [chunk.heading],
                        "evidence": f"{chunk.heading} 证据",
                        "source_refs": [source_ref],
                    },
                )
            ],
            relations=[
                ExtractedRelation(
                    relation_type="part_of",
                    source_name="信号支援",
                    target_name="通信体系",
                    confidence=0.88,
                    payload={"evidence": f"{chunk.heading} 关系证据", "source_refs": [source_ref]},
                )
            ],
            metadata={
                "chunk_id": chunk.chunk_id,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
                "llm_base_url": "https://api.deepseek.com/v1",
            },
        )

    monkeypatch.setattr(ExtractionService, "_build_structured_llm_bundle", lambda self: ("fake-llm", {}))
    monkeypatch.setattr(ExtractionService, "_extract_chunk_batch", fake_extract_chunk_batch)

    batch = ExtractionService(formal_extraction_mode=True).extract_document(
        document_id="doc-1",
        title="信号支援",
        file_path="runtime/fm.pdf",
        segments=segments,
    )

    candidate = next(item for item in batch.candidates if item.canonical_name == "信号支援")
    relation = next(item for item in batch.relations if item.source_name == "信号支援")

    assert len(candidate.payload["source_refs"]) == 2
    assert candidate.payload["source_refs"][0]["chunk_id"] == "chunk-001"
    assert candidate.payload["evidence_list"] == ["第一章 证据", "第二章 证据"]
    assert relation.payload["evidence_list"] == ["第一章 关系证据", "第二章 关系证据"]
    assert batch.metadata["chunking_used"] is True
    assert batch.metadata["chunk_count"] == 2
    assert batch.metadata["chunk_candidate_count_total"] == 2
    assert batch.metadata["merged_candidate_count"] == 1
    assert batch.metadata["llm_provider"] == "deepseek"


def test_chunked_formal_extraction_retries_with_smaller_subchunks_on_truncated_llm_json(monkeypatch) -> None:
    _set_setting("formal_chunk_segment_threshold", 1)
    _set_setting("formal_chunk_char_threshold", 10)
    _set_setting("formal_chunk_char_limit", 200)

    segments = [
        ParsedSegment(
            heading="第一章",
            content="联合作战符号规则 " * 40,
            anchor={"page": 1, "section": "第一章", "line_start": 1, "line_end": 20},
            block_type="paragraph",
        )
    ]

    seen_chunk_sizes: list[int] = []

    def fake_extract_chunk_batch(self, *, document_id, title, file_path, source_document, chunk, structured_llm_bundle):
        del self, document_id, title, file_path, source_document, structured_llm_bundle
        seen_chunk_sizes.append(chunk.char_count)
        if chunk.char_count > 100:
            raise ValueError(
                "正式知识库抽取要求使用结构化大模型抽取，但当前调用失败："
                "1 validation error for StructuredExtractionResponse Invalid JSON: EOF while parsing a list"
            )

        return ExtractionBatch(
            document_id="doc-1",
            title="长文档",
            strategy="schema_rules+llm",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name=f"子块-{chunk.chunk_id}",
                    confidence=0.9,
                    payload={"category": "domain_concept", "evidence": f"{chunk.chunk_id} 证据"},
                )
            ],
            relations=[],
            metadata={
                "chunk_id": chunk.chunk_id,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
                "llm_base_url": "https://api.deepseek.com/v1",
            },
        )

    monkeypatch.setattr(ExtractionService, "_build_structured_llm_bundle", lambda self: ("fake-llm", {}))
    monkeypatch.setattr(ExtractionService, "_extract_chunk_batch", fake_extract_chunk_batch)

    batch = ExtractionService(formal_extraction_mode=True).extract_document(
        document_id="doc-1",
        title="长文档",
        file_path="runtime/long.pdf",
        segments=segments,
    )

    assert any(size > 100 for size in seen_chunk_sizes)
    assert any(size <= 100 for size in seen_chunk_sizes)
    assert batch.metadata["chunking_used"] is True
    assert batch.metadata["llm_enrichment_used"] is True
    assert batch.metadata["chunk_count"] >= 2
    assert len(batch.candidates) >= 2


def test_llm_prompt_limits_dense_chunk_output_to_high_value_supplements() -> None:
    prompt = ExtractionService(formal_extraction_mode=True)._build_llm_prompt(
        title="MIL-STD-2525D",
        file_path="runtime/mil-std.pdf",
        segments=[
            ParsedSegment(
                heading="Symbol Set",
                content="符号定义与分类条目 " * 20,
                anchor={"page": 1, "section": "Symbol Set", "line_start": 1, "line_end": 10},
                block_type="paragraph",
            )
        ],
        base_batch=ExtractionBatch(document_id="doc-1", title="MIL-STD-2525D"),
        scope_label="Symbol Set",
        sample_segments=False,
    )

    assert "LLM 只负责对规则抽取结果做校正、高价值补充和去重" in prompt
    assert "如果当前片段是术语表、符号表、条目清单或大表格，不要逐项穷举整个表" in prompt
    assert "candidates 最多返回 24 条，relations 最多返回 16 条" in prompt


def test_chunked_formal_extraction_retries_with_smaller_subchunks_on_llm_timeout(monkeypatch) -> None:
    _set_setting("formal_chunk_segment_threshold", 1)
    _set_setting("formal_chunk_char_threshold", 10)
    _set_setting("formal_chunk_char_limit", 200)

    segments = [
        ParsedSegment(
            heading="第一章",
            content="超时重试块 " * 40,
            anchor={"page": 1, "section": "第一章", "line_start": 1, "line_end": 20},
            block_type="paragraph",
        )
    ]

    seen_chunk_sizes: list[int] = []

    def fake_extract_chunk_batch(self, *, document_id, title, file_path, source_document, chunk, structured_llm_bundle):
        del self, document_id, title, file_path, source_document, structured_llm_bundle
        seen_chunk_sizes.append(chunk.char_count)
        if chunk.char_count > 100:
            raise ValueError("正式知识库抽取要求使用结构化大模型抽取，但当前调用失败：Request timed out.")

        return ExtractionBatch(
            document_id="doc-1",
            title="长文档",
            strategy="schema_rules+llm",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name=f"超时子块-{chunk.chunk_id}",
                    confidence=0.9,
                    payload={"category": "domain_concept", "evidence": f"{chunk.chunk_id} 证据"},
                )
            ],
            relations=[],
            metadata={
                "chunk_id": chunk.chunk_id,
                "llm_enrichment_used": True,
                "llm_provider": "deepseek",
                "llm_model": "deepseek-chat",
                "llm_base_url": "https://api.deepseek.com/v1",
            },
        )

    monkeypatch.setattr(ExtractionService, "_build_structured_llm_bundle", lambda self: ("fake-llm", {}))
    monkeypatch.setattr(ExtractionService, "_extract_chunk_batch", fake_extract_chunk_batch)

    batch = ExtractionService(formal_extraction_mode=True).extract_document(
        document_id="doc-1",
        title="长文档",
        file_path="runtime/long.pdf",
        segments=segments,
    )

    assert any(size > 100 for size in seen_chunk_sizes)
    assert any(size <= 100 for size in seen_chunk_sizes)
    assert batch.metadata["chunking_used"] is True
    assert len(batch.candidates) >= 2


def test_build_knowledge_index_collects_chunking_diagnostics() -> None:
    diagnostics: list[dict] = []

    class FakeExtractionService:
        def extract_document(self, *, document_id, title, file_path, segments):
            del document_id, title, file_path, segments
            return ExtractionBatch(
                document_id="doc-1",
                title="长文档",
                candidates=[
                    ExtractedCandidate(
                        item_type="entity",
                        canonical_name="信号支援",
                        payload={"category": "domain_concept", "evidence": "章节证据"},
                    )
                ],
                relations=[],
                metadata={
                    "llm_enrichment_used": True,
                    "llm_provider": "deepseek",
                    "llm_model": "deepseek-chat",
                    "chunking_used": True,
                    "chunk_count": 3,
                    "chunk_char_limit": 12000,
                    "chunk_candidate_count_total": 9,
                    "chunk_relation_count_total": 4,
                    "merged_candidate_count": 5,
                    "merged_relation_count": 2,
                },
            )

    build_knowledge_index(
        [
            SourceDocument(
                path="docs/fm-6-02.pdf",
                title="FM 6-02",
                file_type="pdf",
                source_archive="doctrine",
                text="信号支援",
                parser_name="docling_pdf",
                segment_count=1,
                segments=[
                    ParsedSegment(
                        heading="第一章",
                        content="信号支援",
                        anchor={"page": 1, "section": "第一章", "line_start": 1, "line_end": 1},
                        block_type="paragraph",
                    )
                ],
            )
        ],
        extraction_service=FakeExtractionService(),
        diagnostics_collector=diagnostics,
    )

    assert diagnostics[0]["chunking_used"] is True
    assert diagnostics[0]["chunk_count"] == 3
    assert diagnostics[0]["chunk_candidate_count_total"] == 9
    assert diagnostics[0]["merged_relation_count"] == 2
