from __future__ import annotations

from pathlib import Path

import fitz

from app.software_design.models import (
    ReferenceCenter,
    ReferenceSection,
    ReferenceTemplate,
    StandardReference,
    StandardSearchResult,
    TemplateStandardMapping,
)


def _reference_templates() -> list[ReferenceTemplate]:
    return [
        ReferenceTemplate(
            template_id="template-sdd-82284",
            title="DI-IPSC-82284A Software/Hardware Design Description",
            source_doc_id="DI-IPSC-82284",
            document_type="software_design_description",
            version="A",
            format="pdf",
            summary="更适合作为平台级软件工厂软设骨架，覆盖总体架构、分解、接口、部署约束与设计追溯。",
            recommendation="当目标产物不是单一小软件，而是平台级软件或带明显系统边界的产品时，优先采用该模板。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
            pdf_asset_name="template-sdd-82284.pdf",
            sections=[
                ReferenceSection(section_id="scope", title="1. Scope", summary="定义软件设计对象、边界与适用环境。"),
                ReferenceSection(section_id="overview", title="2. System Overview", summary="交代平台级背景、设计上下文与关键约束。"),
                ReferenceSection(section_id="architecture", title="3. Architecture", summary="描述总体架构、分层、部署形态与关键设计决策。"),
                ReferenceSection(section_id="interfaces", title="4. Interfaces", summary="说明内部模块、外部系统与数据交换接口。"),
                ReferenceSection(section_id="detail", title="5. Detailed Design", summary="下钻到模块职责、状态、数据与异常处理。"),
                ReferenceSection(section_id="traceability", title="6. Traceability", summary="建立需求、设计、模块工单之间的追溯链。"),
            ],
        ),
        ReferenceTemplate(
            template_id="template-sdd-81435",
            title="DI-IPSC-81435A Software Design Description",
            source_doc_id="DI-IPSC-81435",
            document_type="software_design_description",
            version="A",
            format="pdf",
            summary="适合纯软件级项目的经典软设模板，结构更轻、对象更聚焦。",
            recommendation="当目标是边界清晰的软件产品或单体应用时，可采用该模板作为更轻量的软设骨架。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=205915",
            pdf_asset_name="template-sdd-81435.pdf",
            sections=[
                ReferenceSection(section_id="scope", title="1. Scope", summary="说明软件设计目标、范围和引用基线。"),
                ReferenceSection(section_id="design-decisions", title="2. Design Decisions", summary="记录架构、技术栈和关键折中。"),
                ReferenceSection(section_id="architecture", title="3. Architectural Design", summary="定义模块分解、控制流与数据流。"),
                ReferenceSection(section_id="detailed-design", title="4. Detailed Design", summary="细化模块职责、接口、算法和数据结构。"),
                ReferenceSection(section_id="traceability", title="5. Requirements Traceability", summary="保持需求到设计元素的映射。"),
            ],
        ),
    ]


def _standard_references() -> list[StandardReference]:
    return [
        StandardReference(
            doc_id="DI-IPSC-82259",
            title="System/Subsystem Specification",
            category="dod-did",
            scope="platform_or_system",
            summary="定义系统/子系统规格说明的内容骨架，适合承接平台级或系统边界明确的需求规格说明。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283189",
            recommended_use="当软件工厂输出对象已接近平台级系统能力包时，用它约束上游需求规格说明更稳妥。",
            tags=["platform", "specification", "requirement", "82259"],
            sections=[
                ReferenceSection(section_id="scope", title="Scope", summary="说明系统/子系统边界、用途和运行环境。"),
                ReferenceSection(section_id="requirements", title="Requirements", summary="组织功能、接口、性能和约束要求。"),
                ReferenceSection(section_id="verification", title="Verification", summary="为后续设计和验收提供验证基线。"),
            ],
        ),
        StandardReference(
            doc_id="DI-IPSC-82284",
            title="Software/Hardware Design Description",
            category="dod-did",
            scope="platform_or_system",
            summary="规定软件/硬件设计说明内容，适合作为平台级软件工厂软设骨架。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
            recommended_use="与 DI-IPSC-82259 配对时，可以把平台级规格说明平滑展开为架构与模块设计说明。",
            tags=["platform", "design", "description", "82284", "software", "hardware"],
            sections=[
                ReferenceSection(section_id="scope", title="Scope", summary="规定设计说明对象、层级和适用范围。"),
                ReferenceSection(section_id="architecture", title="Architecture", summary="描述系统分解、组件边界和总体设计决策。"),
                ReferenceSection(section_id="interfaces", title="Interfaces", summary="列明内部与外部接口以及约束。"),
                ReferenceSection(section_id="detail", title="Detailed Design", summary="细化到可实施的模块与数据结构层。"),
            ],
        ),
        StandardReference(
            doc_id="DI-IPSC-81433",
            title="Software Requirements Specification",
            category="dod-did",
            scope="software_only",
            summary="经典软件需求规格说明模板，适合纯软件级需求输入。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=205913",
            recommended_use="当产物边界明确且不需要系统级框架时，它比 82259 更轻、更纯软件化。",
            tags=["software", "requirement", "specification", "81433"],
            sections=[
                ReferenceSection(section_id="scope", title="Scope", summary="界定软件目标、用户、背景和运行环境。"),
                ReferenceSection(section_id="requirements", title="Requirements", summary="组织功能、接口、性能与非功能要求。"),
                ReferenceSection(section_id="qualification", title="Qualification", summary="为设计与验证提供软件级验收依据。"),
            ],
        ),
        StandardReference(
            doc_id="DI-IPSC-81435",
            title="Software Design Description",
            category="dod-did",
            scope="software_only",
            summary="经典软件设计说明模板，适合软件级项目的详细设计编制。",
            official_detail_url="https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=205915",
            recommended_use="当设计对象是纯软件应用或服务时，可用它形成更直接的软件设计文档。",
            tags=["software", "design", "description", "81435"],
            sections=[
                ReferenceSection(section_id="design-decisions", title="Design Decisions", summary="记录设计原则、约束和折中。"),
                ReferenceSection(section_id="architecture", title="Architectural Design", summary="描述软件分层、模块划分和交互。"),
                ReferenceSection(section_id="detail", title="Detailed Design", summary="细化模块职责、接口和数据结构。"),
            ],
        ),
    ]


def _template_mappings() -> list[TemplateStandardMapping]:
    return [
        TemplateStandardMapping(
            template_id="template-sdd-82284",
            doc_id="DI-IPSC-82259",
            rationale="平台级软设模板需要由更高一层的系统/子系统规格说明提供边界、接口和约束基线。",
            section_pairs=[
                {"template_section": "1. Scope", "standard_section": "Scope"},
                {"template_section": "3. Architecture", "standard_section": "Requirements"},
                {"template_section": "6. Traceability", "standard_section": "Verification"},
            ],
        ),
        TemplateStandardMapping(
            template_id="template-sdd-82284",
            doc_id="DI-IPSC-82284",
            rationale="这是平台级软件工厂当前最推荐的软件设计说明主模板来源。",
            section_pairs=[
                {"template_section": "2. System Overview", "standard_section": "Scope"},
                {"template_section": "3. Architecture", "standard_section": "Architecture"},
                {"template_section": "4. Interfaces", "standard_section": "Interfaces"},
                {"template_section": "5. Detailed Design", "standard_section": "Detailed Design"},
            ],
        ),
        TemplateStandardMapping(
            template_id="template-sdd-81435",
            doc_id="DI-IPSC-81435",
            rationale="当对象收敛到纯软件产品时，81435 的章节骨架更轻更直接。",
            section_pairs=[
                {"template_section": "2. Design Decisions", "standard_section": "Design Decisions"},
                {"template_section": "3. Architectural Design", "standard_section": "Architectural Design"},
                {"template_section": "4. Detailed Design", "standard_section": "Detailed Design"},
            ],
        ),
    ]


def build_reference_center(asset_base_url: str) -> ReferenceCenter:
    templates = [template.model_copy(update={"pdf_url": None}) for template in _reference_templates()]
    return ReferenceCenter(
        templates=templates,
        standards=_standard_references(),
        mappings=_template_mappings(),
    )


def search_standards(query: str) -> list[StandardSearchResult]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return []

    results: list[StandardSearchResult] = []
    for standard in _standard_references():
        if normalized_query in standard.title.lower() or normalized_query in standard.summary.lower():
            results.append(
                StandardSearchResult(
                    doc_id=standard.doc_id,
                    title=standard.title,
                    matched_section="Overview",
                    excerpt=standard.summary,
                    official_detail_url=standard.official_detail_url,
                )
            )
            continue
        for section in standard.sections:
            haystack = " ".join([section.title, section.summary, *standard.tags]).lower()
            if normalized_query in haystack:
                results.append(
                    StandardSearchResult(
                        doc_id=standard.doc_id,
                        title=standard.title,
                        matched_section=section.title,
                        excerpt=section.summary,
                        official_detail_url=standard.official_detail_url,
                    )
                )
                break
    return results


def ensure_reference_assets(asset_dir: Path) -> None:
    asset_dir.mkdir(parents=True, exist_ok=True)
    for template in _reference_templates():
        asset_path = asset_dir / template.pdf_asset_name
        if asset_path.exists():
            continue
        _write_template_pdf(asset_path, template)


def _write_template_pdf(asset_path: Path, template: ReferenceTemplate) -> None:
    document = fitz.open()
    page = document.new_page()
    content_lines = [
        template.title,
        "",
        f"Source DID: {template.source_doc_id}",
        f"Official detail: {template.official_detail_url}",
        "",
        "Why this template:",
        template.recommendation,
        "",
        "Template skeleton:",
        *[f"- {section.title}: {section.summary}" for section in template.sections],
        "",
        "Generated for the local XX-P3 reference center.",
    ]
    page.insert_textbox(
        fitz.Rect(48, 48, 545, 780),
        "\n".join(content_lines),
        fontsize=12,
        fontname="helv",
        align=0,
    )
    document.save(asset_path)
    document.close()
