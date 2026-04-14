from app.config import settings
from app.extraction.service import ExtractionService
from app.extraction.schema import ExtractedCandidate, ExtractedRelation, ExtractionBatch
from app.parsing.models import ParsedSegment


def _set_setting(name: str, value) -> None:
    object.__setattr__(settings, name, value)


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

    def fake_llm_enrichment(self, *, document_id, title, file_path, segments, base_batch):
        del self, document_id, title, file_path, segments, base_batch
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
