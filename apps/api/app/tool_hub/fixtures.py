from __future__ import annotations

from app.tool_hub.models import CatalogItem, ToolDefinition, ToolVerification


CATEGORY_CATALOG = [
    CatalogItem(id="knowledge_ingestion", label="资料接入", description="面向知识资料接入与预处理"),
    CatalogItem(id="knowledge_processing", label="知识处理", description="面向解析、抽取与结构化处理"),
    CatalogItem(id="knowledge_governance", label="知识治理", description="面向候选治理与发布修订"),
    CatalogItem(id="knowledge_query", label="知识查询", description="面向检索、查询和解释"),
    CatalogItem(id="application_modeling", label="应用建模", description="面向建模与构建描述"),
    CatalogItem(id="validation_support", label="验证支撑", description="面向验证、解释和风险提示"),
]

STAGE_CATALOG = [
    CatalogItem(id="archive_intake", label="资料接入"),
    CatalogItem(id="parsing", label="结构化解析"),
    CatalogItem(id="extraction", label="候选抽取"),
    CatalogItem(id="governance", label="知识治理"),
    CatalogItem(id="query", label="知识查询"),
    CatalogItem(id="modeling", label="应用建模"),
    CatalogItem(id="validation", label="验证工作台"),
]

INPUT_TYPE_CATALOG = [
    CatalogItem(id="archive_summary", label="知识库摘要"),
    CatalogItem(id="entity_list", label="实体列表"),
    CatalogItem(id="process_list", label="流程列表"),
    CatalogItem(id="item_detail", label="知识详情"),
    CatalogItem(id="search_results", label="搜索结果"),
    CatalogItem(id="snapshot_json", label="冻结快照"),
    CatalogItem(id="manual_text", label="人工文本"),
]

OUTPUT_TYPE_CATALOG = [
    CatalogItem(id="candidate_set", label="候选集合"),
    CatalogItem(id="review_suggestion", label="审核建议"),
    CatalogItem(id="validation_report", label="验证报告"),
    CatalogItem(id="requirement_draft", label="需求草案"),
    CatalogItem(id="structured_json", label="结构化 JSON"),
]

SUPPORTED_SOURCE_CATALOG = [
    CatalogItem(id="p1_readonly_api", label="P1 只读 API"),
    CatalogItem(id="frozen_snapshot", label="冻结快照"),
    CatalogItem(id="manual_input", label="人工输入"),
]

VERIFICATION_STATUS_CATALOG = [
    CatalogItem(id="unverified", label="未验证"),
    CatalogItem(id="verified", label="已验证"),
    CatalogItem(id="warning", label="需复核"),
    CatalogItem(id="failed", label="失败"),
]

TAG_NAMESPACE_CATALOG = [
    CatalogItem(id="stage", label="阶段标签"),
    CatalogItem(id="capability", label="能力标签"),
    CatalogItem(id="input", label="输入标签"),
    CatalogItem(id="output", label="输出标签"),
    CatalogItem(id="risk", label="风险标签"),
]


def demo_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="tool-process-validator",
            name="流程验证器",
            slug="process-validator",
            status="active",
            summary="针对流程清单生成结构化验证建议",
            problem_statement="降低流程建模前期人工比对成本",
            primary_category_id="application_modeling",
            tags=[
                "stage:modeling",
                "capability:process-analysis",
                "input:process-list",
                "output:validation-report",
            ],
            applicable_stages=["modeling", "validation"],
            input_types=["process_list", "manual_text"],
            output_types=["validation_report", "structured_json"],
            supported_sources=["manual_input", "frozen_snapshot"],
            usage_notes="适用于流程梳理和建模前的快速分析。",
            keywords=["流程", "验证", "建模"],
            verification=ToolVerification(
                status="verified",
                last_verified_result="基线流程样例通过",
                sample_case_ids=["sample-process-validation"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-entity-normalization",
            name="实体归一建议器",
            slug="entity-normalization-advisor",
            status="active",
            summary="针对实体候选提供归一建议和风险提示",
            problem_statement="减少候选实体治理时的重复判断与漏判",
            primary_category_id="knowledge_governance",
            tags=[
                "stage:governance",
                "capability:entity-normalization",
                "input:entity-list",
                "output:review-suggestion",
                "risk:manual-review-required",
            ],
            applicable_stages=["governance"],
            input_types=["entity_list"],
            output_types=["review_suggestion"],
            supported_sources=["p1_readonly_api", "frozen_snapshot"],
            usage_notes="优先用于候选实体规模较大的治理场景。",
            keywords=["实体", "归一", "治理"],
            verification=ToolVerification(
                status="warning",
                last_verified_result="样例可用，但需要人工复核",
                sample_case_ids=["sample-entity-review"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-knowledge-coverage-mapper",
            name="知识覆盖映射器",
            slug="knowledge-coverage-mapper",
            status="active",
            summary="将工具能力映射到阶段和能力域，输出覆盖矩阵",
            problem_statement="帮助识别工具池空白区与过密区",
            primary_category_id="validation_support",
            tags=[
                "stage:validation",
                "capability:coverage-analysis",
                "input:snapshot-json",
                "output:validation-report",
            ],
            applicable_stages=["validation", "query"],
            input_types=["snapshot_json", "manual_text"],
            output_types=["validation_report"],
            supported_sources=["frozen_snapshot", "manual_input"],
            usage_notes="适合做工具池覆盖可视化。",
            keywords=["覆盖", "矩阵", "分析"],
            verification=ToolVerification(
                status="verified",
                last_verified_result="矩阵基线样例通过",
                sample_case_ids=["sample-coverage-matrix"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-process-explainer",
            name="流程候选解释器",
            slug="process-explainer",
            status="draft",
            summary="给出流程候选命中的解释理由",
            problem_statement="帮助用户理解匹配链路与结果依据",
            primary_category_id="validation_support",
            tags=[
                "stage:modeling",
                "capability:process-analysis",
                "input:process-list",
                "output:review-suggestion",
            ],
            applicable_stages=["modeling"],
            input_types=["process_list"],
            output_types=["review_suggestion"],
            supported_sources=["manual_input"],
            usage_notes="更适合作为解释层，不直接替代主分析工具。",
            keywords=["流程", "解释"],
            verification=ToolVerification(
                status="unverified",
                last_verified_result="",
                sample_case_ids=[],
            ),
        ),
    ]
