from app.extraction.schema import ExtractedCandidate, ExtractedRelation, ExtractionBatch
from app.knowledge_builder import SourceDocument, build_knowledge_index
from app.parsing.models import ParsedSegment


def test_build_knowledge_index_extracts_entities_events_and_processes() -> None:
    documents = [
        SourceDocument(
            path="source/[3]NAS体系结构产品/Far Term/OV-1.docx",
            title="远期顶层运行概念图（OV-1）",
            file_type="docx",
            source_archive="translated",
            text="""
联邦航空管理局（FAA）
国家空域系统（NAS）企业体系架构（NAS EA）
本文档描述了使命任务服务、支持服务、SOA核心服务、管理服务、企业治理、技术体系架构服务和交互服务。
图3.0-II NAS远期(NextGen)需求文档的服务互操作性过程流
""".strip(),
        ),
        SourceDocument(
            path="source/[3]NAS体系结构产品/As Is/10002025_NAS-EA-OV-5-As-Is-v1.0-012910.docx",
            title="当前运行活动模型（OV-5）",
            file_type="docx",
            source_archive="translated",
            text="该附录描述了管理和控制NAS架构与需求的方法。",
        ),
    ]

    knowledge = build_knowledge_index(documents)

    entity_names = {item["name"] for item in knowledge["entities"]}
    event_names = {item["name"] for item in knowledge["events"]}
    process_names = {item["name"] for item in knowledge["processes"]}
    relation_keys = {(item["type"], item["from"], item["to"]) for item in knowledge["relations"]}
    entity_index = {item["name"]: item for item in knowledge["entities"]}

    assert "联邦航空管理局" in entity_names
    assert "国家空域系统" in entity_names
    assert "OV-1" in entity_names
    assert "使命任务服务" in entity_names
    assert "当前状态（As Is）" in event_names
    assert "远期目标（Far Term）" in event_names
    assert "服务互操作流程" in process_names
    assert "架构与需求治理" in process_names
    assert ("describes", entity_index["OV-1"]["id"], entity_index["国家空域系统"]["id"]) in relation_keys
    assert knowledge["summary"]["relation_count"] >= 4


def test_build_knowledge_index_extracts_operational_nodes_and_exchanges_from_ov2_rows() -> None:
    documents = [
        SourceDocument(
            path="source/[3]NAS体系结构产品/As Is/10002024_NAS-EA-OV-2-As-Is-V1.0-091311.docx",
            title="运行节点关联关系图（OV-2）",
            file_type="docx",
            source_archive="translated",
            text="""
| ATCT | 机场塔台管制 |
| TRACON | 终端雷达进近管制 |
| Tower-Tracon I/O 1 Next Departure I/O 2 Aircraft Synchronization | 塔台——终端雷达进近管制 输入/输出 1：下一次离场 输入/输出 2：航空器信息同步 |
| IEX Name: Flow Coordination Message | IEX 名称：流量协调消息 |
""".strip(),
        )
    ]

    knowledge = build_knowledge_index(documents)

    entity_index = {item["name"]: item for item in knowledge["entities"]}

    assert entity_index["机场塔台管制"]["category"] == "operational_node"
    assert "ATCT" in entity_index["机场塔台管制"]["aliases"]
    assert entity_index["终端雷达进近管制"]["category"] == "operational_node"
    assert entity_index["流量协调消息"]["category"] == "information_exchange"
    assert entity_index["下一次离场"]["category"] == "information_exchange"
    assert "Next Departure" in entity_index["下一次离场"]["aliases"]

    relations = {
        (relation["type"], relation["from"], relation["to"])
        for relation in knowledge["relations"]
    }
    tower_id = entity_index["机场塔台管制"]["id"]
    tracon_id = entity_index["终端雷达进近管制"]["id"]
    departure_id = entity_index["下一次离场"]["id"]

    assert ("operational_exchange", tower_id, tracon_id) in relations
    assert ("participates_in_exchange", tower_id, departure_id) in relations
    assert ("participates_in_exchange", tracon_id, departure_id) in relations
    assert ("part_of", tower_id, entity_index["国家空域系统"]["id"]) in relations


def test_build_knowledge_index_extracts_activity_level_processes_from_ov5_rows() -> None:
    documents = [
        SourceDocument(
            path="source/[3]NAS体系结构产品/As Is/10002025_NAS-EA-OV-5-As-Is-v1.0-012910.docx",
            title="当前运行活动模型（OV-5）",
            file_type="docx",
            source_archive="translated",
            text="""
| TITLE:OPERATIONAL ACTIVITY MODEL (OV-5) — CONTROL AIR TRAFFIC | 题目：运行活动图(OV-5)-空中交通管制 |
| MANAGE FLIGHT INFORMATION | 航班信息管理 |
| SEPARATE AIRCRAFT | 航空器间隔 |
| TRANSFER CONTROL RESPONSIBILITY | 管制移交 |
""".strip(),
        )
    ]

    knowledge = build_knowledge_index(documents)
    process_names = {item["name"] for item in knowledge["processes"]}

    assert "航班信息管理" in process_names
    assert "航空器间隔" in process_names
    assert "管制移交" in process_names


def test_build_knowledge_index_uses_extraction_service_for_structured_segments(monkeypatch) -> None:
    documents = [
        SourceDocument(
            path="source/[3]NAS体系结构产品/As Is/coordination.docx",
            title="运行协调说明",
            file_type="docx",
            source_archive="translated",
            text="运行协调说明",
            segments=[
                ParsedSegment(
                    heading="运行协调",
                    content="运行协调说明",
                    anchor={"page": 1, "section": "运行协调", "line_start": 1, "line_end": 1},
                )
            ],
        )
    ]

    def fake_extract_document(self, *, document_id, title, file_path, segments):
        del self, document_id, title, file_path, segments
        return ExtractionBatch(
            document_id="doc-runtime",
            title="运行协调说明",
            candidates=[
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="国家空域系统",
                    payload={"category": "system_or_service", "aliases": ["NAS"], "evidence": "国家空域系统"},
                ),
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="全国流量管理",
                    payload={"category": "domain_concept", "aliases": ["流量管理"], "evidence": "全国流量管理"},
                ),
                ExtractedCandidate(
                    item_type="process",
                    canonical_name="流量调配",
                    payload={"category": "domain_process", "aliases": [], "evidence": "流量调配"},
                ),
            ],
            relations=[
                ExtractedRelation(relation_type="part_of", source_name="全国流量管理", target_name="国家空域系统"),
                ExtractedRelation(relation_type="part_of", source_name="流量调配", target_name="国家空域系统"),
            ],
        )

    monkeypatch.setattr("app.extraction.service.ExtractionService.extract_document", fake_extract_document)

    knowledge = build_knowledge_index(documents)

    entity_names = {item["name"] for item in knowledge["entities"]}
    process_names = {item["name"] for item in knowledge["processes"]}
    relations = {(item["type"], item["from"], item["to"]) for item in knowledge["relations"]}
    entity_index = {item["name"]: item for item in knowledge["entities"]}
    process_index = {item["name"]: item for item in knowledge["processes"]}

    assert "全国流量管理" in entity_names
    assert "流量调配" in process_names
    assert ("part_of", entity_index["全国流量管理"]["id"], entity_index["国家空域系统"]["id"]) in relations
    assert ("part_of", process_index["流量调配"]["id"], entity_index["国家空域系统"]["id"]) in relations
