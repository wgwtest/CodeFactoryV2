from app.knowledge_builder import SourceDocument, build_knowledge_index


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

    assert "联邦航空管理局" in entity_names
    assert "国家空域系统" in entity_names
    assert "OV-1" in entity_names
    assert "使命任务服务" in entity_names
    assert "当前状态（As Is）" in event_names
    assert "远期目标（Far Term）" in event_names
    assert "服务互操作流程" in process_names
    assert "架构与需求治理" in process_names


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
