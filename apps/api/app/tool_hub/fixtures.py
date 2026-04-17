from __future__ import annotations

from app.tool_hub.models import CatalogItem, ToolDefinition, ToolVerification


DOMAIN_CATALOG = [
    CatalogItem(id="simulated_blue_force", label="模拟蓝军", description="围绕蓝军建模、对抗推演、行动控制和评估复盘的业务域"),
    CatalogItem(id="navigation_planning", label="导航规划", description="围绕航路设计、冲突校核和导航方案生成的业务域"),
    CatalogItem(id="data_governance", label="数据治理", description="围绕对象归并、质量核验、血缘审查和标准化治理的业务域"),
    CatalogItem(id="case_management", label="案件管理", description="围绕工单、案例、事项等业务对象的受理与流转"),
    CatalogItem(id="workflow_approval", label="审批流转", description="围绕审批路径、规则校验和节点解释的业务域"),
    CatalogItem(id="scheduling_dispatch", label="排班调度", description="围绕资源排班、冲突检测和调度建议的业务域"),
    CatalogItem(id="alert_response", label="告警处置", description="围绕告警接收、分派、升级和闭环处置的业务域"),
    CatalogItem(id="reporting_audit", label="报表审计", description="围绕统计报表、审计留痕和经营复盘的业务域"),
    CatalogItem(id="master_data", label="主数据维护", description="围绕主数据归并、标准化和一致性校验的业务域"),
    CatalogItem(id="cross_domain_shared", label="跨域通用", description="不绑定单一业务域、面向多域复用的通用工具"),
]

LIFECYCLE_STAGE_CATALOG = [
    CatalogItem(id="domain_discovery", label="业务梳理"),
    CatalogItem(id="solution_design", label="方案设计"),
    CatalogItem(id="build_integration", label="构建集成"),
    CatalogItem(id="verification_release", label="验证发布"),
    CatalogItem(id="operation_optimization", label="运行优化"),
]

TOOL_FORM_CATALOG = [
    CatalogItem(id="skill", label="Skill", description="可被 Agent 或编排节点直接调用的技能工具"),
    CatalogItem(id="template", label="模板", description="用于生成页面、配置、脚手架或工件骨架的模板资产"),
    CatalogItem(id="service_endpoint", label="服务接口", description="通过 HTTP/RPC 等方式提供能力的服务化工具"),
    CatalogItem(id="package_bundle", label="包组件", description="以包、插件或发行件形式交付的工具组件"),
    CatalogItem(id="static_library", label="静态库", description="需在构建期链接的库型工具"),
    CatalogItem(id="dynamic_library", label="动态库", description="需在运行期加载的库型工具"),
]

RUNTIME_PLATFORM_CATALOG = [
    CatalogItem(id="browser", label="浏览器/前端"),
    CatalogItem(id="backend_service", label="后端服务"),
    CatalogItem(id="agent_runtime", label="Agent 运行时"),
    CatalogItem(id="container", label="容器环境"),
    CatalogItem(id="local_cli", label="本地 CLI"),
    CatalogItem(id="embedded_sdk", label="嵌入 SDK"),
]

INPUT_TYPE_CATALOG = [
    CatalogItem(id="requirement_brief", label="需求简述"),
    CatalogItem(id="process_list", label="流程清单"),
    CatalogItem(id="entity_list", label="对象清单"),
    CatalogItem(id="form_schema", label="表单结构"),
    CatalogItem(id="rule_set", label="规则集"),
    CatalogItem(id="snapshot_json", label="冻结快照"),
    CatalogItem(id="manual_text", label="人工文本"),
    CatalogItem(id="map_asset", label="地图资产"),
    CatalogItem(id="terrain_layer", label="地形图层"),
    CatalogItem(id="force_definition", label="兵力定义"),
    CatalogItem(id="rule_definition", label="规则定义"),
    CatalogItem(id="mission_definition", label="任务定义"),
    CatalogItem(id="simulation_result", label="推演结果"),
]

OUTPUT_TYPE_CATALOG = [
    CatalogItem(id="validation_report", label="验证报告"),
    CatalogItem(id="review_suggestion", label="审阅建议"),
    CatalogItem(id="template_bundle", label="模板包"),
    CatalogItem(id="structured_json", label="结构化 JSON"),
    CatalogItem(id="integration_config", label="集成配置"),
    CatalogItem(id="battlefield_map", label="战场底图"),
    CatalogItem(id="visibility_report", label="通视报告"),
    CatalogItem(id="force_tree", label="兵力编组树"),
    CatalogItem(id="rule_bundle", label="规则包"),
    CatalogItem(id="action_plan", label="行动计划"),
    CatalogItem(id="metric_report", label="指标报告"),
]

SUPPORTED_SOURCE_CATALOG = [
    CatalogItem(id="p1_readonly_api", label="P1 只读 API"),
    CatalogItem(id="frozen_snapshot", label="冻结快照"),
    CatalogItem(id="manual_input", label="人工输入"),
    CatalogItem(id="tool_hub_snapshot", label="工具仓快照"),
]

VERIFICATION_STATUS_CATALOG = [
    CatalogItem(id="unverified", label="未验证"),
    CatalogItem(id="verified", label="已验证"),
    CatalogItem(id="warning", label="需复核"),
    CatalogItem(id="failed", label="失败"),
]

TAG_NAMESPACE_CATALOG = [
    CatalogItem(id="domain", label="业务域标签"),
    CatalogItem(id="lifecycle", label="生命周期标签"),
    CatalogItem(id="form", label="工具形态标签"),
    CatalogItem(id="runtime", label="运行平台标签"),
    CatalogItem(id="input", label="输入标签"),
    CatalogItem(id="output", label="输出标签"),
    CatalogItem(id="risk", label="风险标签"),
]


def demo_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            tool_id="tool-process-validator",
            name="审批规则校验器",
            slug="approval-rule-validator",
            status="active",
            summary="针对审批路径和规则集生成结构化校验结论",
            problem_statement="降低审批方案设计阶段的人工比对成本",
            primary_domain_id="workflow_approval",
            tool_form_id="skill",
            runtime_platform_ids=["agent_runtime", "backend_service"],
            lifecycle_stage_ids=["solution_design", "verification_release"],
            tags=[
                "domain:workflow_approval",
                "form:skill",
                "runtime:agent_runtime",
                "runtime:backend_service",
                "lifecycle:solution_design",
                "lifecycle:verification_release",
                "input:process_list",
                "input:rule_set",
                "output:validation_report",
            ],
            input_types=["process_list", "rule_set", "manual_text"],
            output_types=["validation_report", "structured_json"],
            supported_sources=["manual_input", "frozen_snapshot"],
            usage_notes="适用于审批链条设计前后的快速规则校验。",
            keywords=["审批", "规则", "流程"],
            verification=ToolVerification(
                status="verified",
                last_verified_result="审批基线样例通过",
                sample_case_ids=["sample-approval-validation"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-process-explainer",
            name="审批路径解释器",
            slug="approval-path-explainer",
            status="active",
            summary="为审批流程命中结果补充路径解释和人工复核提示",
            problem_statement="帮助评审人员理解规则命中依据和潜在缺口",
            primary_domain_id="workflow_approval",
            tool_form_id="skill",
            runtime_platform_ids=["agent_runtime"],
            lifecycle_stage_ids=["solution_design", "verification_release"],
            tags=[
                "domain:workflow_approval",
                "form:skill",
                "runtime:agent_runtime",
                "lifecycle:solution_design",
                "lifecycle:verification_release",
                "input:process_list",
                "output:review_suggestion",
                "risk:manual-review-required",
            ],
            input_types=["process_list", "manual_text"],
            output_types=["review_suggestion"],
            supported_sources=["manual_input"],
            usage_notes="更适合作为解释层，与校验器配合使用。",
            keywords=["审批", "解释", "路径"],
            verification=ToolVerification(
                status="warning",
                last_verified_result="解释结论可用，但仍需人工复核",
                sample_case_ids=["sample-approval-explainer"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-entity-normalization",
            name="主数据归一建议器",
            slug="master-data-normalization-advisor",
            status="active",
            summary="针对对象清单给出归一建议和冲突提示",
            problem_statement="减少主数据维护阶段的重复判断与漏判",
            primary_domain_id="master_data",
            tool_form_id="service_endpoint",
            runtime_platform_ids=["backend_service", "container"],
            lifecycle_stage_ids=["build_integration", "operation_optimization"],
            tags=[
                "domain:master_data",
                "form:service_endpoint",
                "runtime:backend_service",
                "runtime:container",
                "lifecycle:build_integration",
                "lifecycle:operation_optimization",
                "input:entity_list",
                "output:review_suggestion",
                "risk:manual-review-required",
            ],
            input_types=["entity_list", "snapshot_json"],
            output_types=["review_suggestion", "structured_json"],
            supported_sources=["p1_readonly_api", "frozen_snapshot", "tool_hub_snapshot"],
            usage_notes="优先用于对象量较大的主数据整理场景。",
            keywords=["主数据", "归一", "冲突"],
            verification=ToolVerification(
                status="verified",
                last_verified_result="主数据归一基线样例通过",
                sample_case_ids=["sample-master-data-review"],
            ),
        ),
        ToolDefinition(
            tool_id="tool-knowledge-coverage-mapper",
            name="案件表单模板包",
            slug="case-form-template-kit",
            status="draft",
            summary="根据业务表单结构生成案件录入模板与约束骨架",
            problem_statement="缩短案件管理页面和配置模板的初始搭建时间",
            primary_domain_id="case_management",
            tool_form_id="template",
            runtime_platform_ids=["browser", "embedded_sdk"],
            lifecycle_stage_ids=["solution_design", "build_integration"],
            tags=[
                "domain:case_management",
                "form:template",
                "runtime:browser",
                "runtime:embedded_sdk",
                "lifecycle:solution_design",
                "lifecycle:build_integration",
                "input:form_schema",
                "output:template_bundle",
            ],
            input_types=["form_schema", "manual_text"],
            output_types=["template_bundle", "integration_config"],
            supported_sources=["manual_input", "frozen_snapshot"],
            usage_notes="更适合作为案件管理模块的模板起点。",
            keywords=["案件", "表单", "模板"],
            verification=ToolVerification(
                status="unverified",
                last_verified_result="",
                sample_case_ids=[],
            ),
        ),
    ]
