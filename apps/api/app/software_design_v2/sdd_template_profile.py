from __future__ import annotations

from copy import deepcopy

from app.config import REPO_ROOT


SDD_81435_TEMPLATE_PATH = (
    REPO_ROOT
    / "DOC"
    / "JB_DOC"
    / "02-软件工厂产物模板中心"
    / "01-需求与设计主链模板"
    / "02-软件设计说明模板"
    / "基础模板"
    / "01-81435-软件设计说明准模板-v1.md"
)


_REQUIRED_SECTIONS = [
    {"section_id": "sdd-01", "number": "1", "title": "文档目的与设计口径", "minimum_chars": 250},
    {"section_id": "sdd-02", "number": "2", "title": "系统定位", "minimum_chars": 400},
    {"section_id": "sdd-03", "number": "3", "title": "业务目标与边界", "minimum_chars": 400},
    {"section_id": "sdd-04", "number": "4", "title": "总体架构", "minimum_chars": 1200},
    {"section_id": "sdd-05", "number": "5", "title": "前端软件设计", "minimum_chars": 1200},
    {"section_id": "sdd-06", "number": "6", "title": "后端软件设计", "minimum_chars": 1500},
    {"section_id": "sdd-07", "number": "7", "title": "核心对象模型", "minimum_chars": 1200},
    {"section_id": "sdd-08", "number": "8", "title": "API 设计", "minimum_chars": 1500},
    {"section_id": "sdd-09", "number": "9", "title": "关键运行流程", "minimum_chars": 1200},
    {"section_id": "sdd-10", "number": "10", "title": "智能能力、模型调用与插件设计", "minimum_chars": 400},
    {"section_id": "sdd-11", "number": "11", "title": "设计约束与质量门", "minimum_chars": 1000},
    {"section_id": "sdd-12", "number": "12", "title": "目标目录结构", "minimum_chars": 400},
    {"section_id": "sdd-13", "number": "13", "title": "验收口径", "minimum_chars": 400},
    {"section_id": "sdd-14", "number": "14", "title": "面向平台展示与验证输出接口", "minimum_chars": 400},
    {"section_id": "sdd-15", "number": "15", "title": "设计结论", "minimum_chars": 250},
]


_REQUIRED_TABLES = [
    {"table_id": "T1", "name": "术语与缩略语表", "section_id": "sdd-01"},
    {"table_id": "T2", "name": "用户角色与使用上下文表", "section_id": "sdd-02"},
    {"table_id": "T3", "name": "上下游边界表", "section_id": "sdd-03"},
    {"table_id": "T4", "name": "总体分层表", "section_id": "sdd-04"},
    {"table_id": "T5", "name": "能力模块映射表", "section_id": "sdd-04"},
    {"table_id": "T6", "name": "部署与运行单元表", "section_id": "sdd-04"},
    {"table_id": "T7", "name": "前端路由/页面/状态/命令表", "section_id": "sdd-05"},
    {"table_id": "T8", "name": "后端模块权威矩阵", "section_id": "sdd-06"},
    {"table_id": "T9", "name": "核心对象模型表", "section_id": "sdd-07"},
    {"table_id": "T10", "name": "API 分组表", "section_id": "sdd-08"},
    {"table_id": "T11", "name": "关键 API 表", "section_id": "sdd-08"},
    {"table_id": "T12", "name": "关键流程表或时序说明", "section_id": "sdd-09"},
    {"table_id": "T13", "name": "质量门表", "section_id": "sdd-11"},
    {"table_id": "T14", "name": "验收口径表", "section_id": "sdd-13"},
    {"table_id": "T15", "name": "需求追溯表", "section_id": "sdd-14"},
]


_REQUIRED_DIAGRAMS = [
    {
        "diagram_id": "D1",
        "name": "总体架构图",
        "section_id": "sdd-04",
        "allowed_types": ["mermaid", "plantuml", "graph_json"],
    },
    {
        "diagram_id": "D2",
        "name": "后端模块/服务关系图",
        "section_id": "sdd-06",
        "allowed_types": ["mermaid", "plantuml", "graph_json"],
    },
    {
        "diagram_id": "D3",
        "name": "核心对象关系图",
        "section_id": "sdd-07",
        "allowed_types": ["mermaid", "plantuml", "graph_json"],
    },
    {
        "diagram_id": "D4",
        "name": "关键运行流程图",
        "section_id": "sdd-09",
        "allowed_types": ["mermaid", "plantuml", "graph_json"],
    },
]


_DOCUMENT_STRUCTURE = {
    "section_children_field": "children",
    "block_field": "blocks",
    "minimum_heading_depth": 2,
    "required_block_kinds": ["paragraph", "table", "diagram"],
    "allowed_block_kinds": ["paragraph", "clause", "table", "list", "code", "diagram", "diagram_placeholder"],
    "table_shape": {"columns": "string[]", "rows": "string[][]"},
    "diagram_shape": {
        "kind": "diagram",
        "diagram_type": "mermaid | plantuml | graph_json",
        "content": "diagram source text or graph JSON string",
    },
}


def build_sdd_81435_template_profile(*, design_title: str, version_label: str) -> dict:
    return {
        "template_id": "81435-sdd-quasi-template-v1",
        "template_name": "81435-软件设计说明准模板-v1",
        "template_status": "quasi_template_v1_pending_review",
        "template_path": str(SDD_81435_TEMPLATE_PATH.relative_to(REPO_ROOT)),
        "standard_reference": "DI-IPSC-81435 Software Design Description",
        "design_title": design_title,
        "version_label": version_label,
        "document_type": "software_design_description",
        "applicability": {
            "applies_to": ["软件级应用", "软件级服务", "软件级工具", "软件配置项"],
            "does_not_apply_to": ["平台级对象", "系统级对象", "软硬件一体化对象"],
            "related_templates": {
                "platform_or_system_design": "82284",
                "interface_design": "81436",
                "database_design": "81437",
            },
        },
        "minimum_total_chars": 12000,
        "section_coverage": {"level_1_required": 1.0, "level_2_required": 0.9},
        "document_structure": deepcopy(_DOCUMENT_STRUCTURE),
        "required_sections": deepcopy(_REQUIRED_SECTIONS),
        "required_tables": deepcopy(_REQUIRED_TABLES),
        "diagram_requirements": {
            "minimum_diagram_count": len(_REQUIRED_DIAGRAMS),
            "required_diagrams": deepcopy(_REQUIRED_DIAGRAMS),
        },
        "generation_rules": [
            "生成正式软设草稿，不生成短摘要。",
            "必须承接 P2 冻结需求中的角色、功能、数据、接口、非功能和验收项。",
            "设计说明解释如何实现需求，不重新发明需求。",
            "每个一级章节应使用 children 输出二级小节；核心章节不得只把二级标题写进 content。",
            "正文应使用 blocks 输出段落、表格和图块；表格不得只作为普通段落。",
            "图优先使用 Mermaid、PlantUML 或 graph_json 结构化表达，不要求生成图片文件。",
            "每个核心章节必须展开模块、对象、接口、流程、约束或追溯，不得只给概括性短句。",
            "Dify、模型服务和插件能力必须写清输入、输出、超时、失败处理和人工复核边界。",
            "信息不足时保留完整结构，写明缺口、暂定假设、待确认问题和实现影响。",
        ],
    }


def build_sdd_81435_quality_rules() -> dict:
    return {
        "result_status": "draft_only",
        "must_not_freeze": True,
        "require_traceability": True,
        "require_gap_list": True,
        "require_review_findings": True,
        "minimum_total_chars": 12000,
        "section_coverage": {"level_1_required": 1.0, "level_2_required": 0.9},
        "document_structure": {
            **deepcopy(_DOCUMENT_STRUCTURE),
            "require_structured_blocks": True,
            "require_section_children": True,
        },
        "required_sections": deepcopy(_REQUIRED_SECTIONS),
        "required_tables": deepcopy(_REQUIRED_TABLES),
        "diagram_requirements": {
            "minimum_diagram_count": len(_REQUIRED_DIAGRAMS),
            "required_diagrams": deepcopy(_REQUIRED_DIAGRAMS),
        },
        "core_section_minimum_chars": {
            section["section_id"]: section["minimum_chars"]
            for section in _REQUIRED_SECTIONS
            if section["section_id"] in {"sdd-04", "sdd-05", "sdd-06", "sdd-07", "sdd-08", "sdd-09", "sdd-11"}
        },
        "validation_rules": [
            "15 个一级章节必须全部存在。",
            "至少 90% 一级章节必须包含 children 二级小节。",
            "核心章节必须使用 blocks 输出段落、表格和图块。",
            "必须至少生成 D1-D4 四类结构化图块；图块可为 Mermaid、PlantUML 或 graph_json。",
            "核心章节必须达到最低中文字符数。",
            "必备表格 T1-T15 必须存在或给出等价结构。",
            "高优先级 P2 需求必须映射到 P3 章节、模块、API 或质量门。",
            "外部能力边界必须包含输入、输出、失败处理和复核约定。",
        ],
    }
