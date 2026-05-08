from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TemplateStatus = Literal["draft", "active", "disabled", "archived"]
DocumentStatus = Literal["draft", "checking", "ready_to_freeze", "frozen", "submitted_to_p3", "archived"]
LayoutRatio = Literal["2:3", "1:1"]


class RequirementAuthoringTemplateWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_code: str
    name: str
    description: str = ""
    status: TemplateStatus = "draft"
    sections: list[dict] | None = None
    form_groups: list[dict] | None = None
    field_mappings: list[dict] | None = None
    questionnaire_policy: dict | None = None
    gap_rules: dict | None = None
    knowledge_bindings: list[dict] | None = None


class RequirementAuthoringDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    template_id: str
    archive_ids: list[str] = Field(default_factory=list)
    layout_ratio: LayoutRatio = "2:3"


class RequirementAuthoringMessageWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str


class RequirementAuthoringFormPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: dict[str, str]


class RequirementAuthoringDocumentSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    template_id: str | None = None
    archive_ids: list[str] | None = None
    knowledge_binding: dict | None = None


class RequirementAuthoringClausePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str


class RequirementAuthoringKnowledgeBindingWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    domain_id: str


def default_template_payload(template_code: str = "81433") -> dict:
    name = "软件级需求规格说明模板" if template_code == "81433" else "平台级需求规格说明模板"
    return {
        "description": f"{template_code} 内置基线，仅作为首版默认模板，可被配置台替换。",
        "sections": [
            {
                "section_id": "1",
                "title": "1 总则",
                "clauses": [
                    {
                        "clause_id": "REQ-1.1",
                        "title": "编写目的",
                        "field_keys": ["application_name", "domain_scope"],
                    },
                    {
                        "clause_id": "REQ-1.2",
                        "title": "适用范围",
                        "field_keys": ["application_scope", "target_users"],
                    },
                    {
                        "clause_id": "REQ-1.3",
                        "title": "术语与缩略语",
                        "field_keys": ["terms_glossary"],
                    }
                ],
            },
            {
                "section_id": "2",
                "title": "2 项目概述",
                "clauses": [
                    {
                        "clause_id": "REQ-2.1",
                        "title": "软件定位",
                        "field_keys": ["application_name", "domain_scope", "target_users"],
                    },
                    {
                        "clause_id": "REQ-2.2",
                        "title": "建设目标",
                        "field_keys": ["business_goals", "expected_value"],
                    },
                    {
                        "clause_id": "REQ-2.3",
                        "title": "使用场景",
                        "field_keys": ["main_scenarios", "usage_modes"],
                    },
                    {
                        "clause_id": "REQ-2.4",
                        "title": "范围边界",
                        "field_keys": ["in_scope", "out_of_scope"],
                    }
                ],
            },
            {
                "section_id": "3",
                "title": "3 功能需求",
                "clauses": [
                    {
                        "clause_id": "REQ-3.1",
                        "title": "用户与角色",
                        "field_keys": ["target_users"],
                    },
                    {
                        "clause_id": "REQ-3.2",
                        "title": "核心业务流程",
                        "field_keys": ["main_process", "normal_flow"],
                    },
                    {
                        "clause_id": "REQ-3.3",
                        "title": "态势展示与浏览",
                        "field_keys": ["situational_display"],
                    },
                    {
                        "clause_id": "REQ-3.4",
                        "title": "空间分析工具",
                        "field_keys": ["gis_analysis_tools"],
                    },
                    {
                        "clause_id": "REQ-3.5",
                        "title": "部署分析能力",
                        "field_keys": ["deployment_analysis"],
                    },
                    {
                        "clause_id": "REQ-3.6",
                        "title": "结果输出与共享",
                        "field_keys": ["result_outputs", "collaboration_mode"],
                    },
                    {
                        "clause_id": "REQ-3.7",
                        "title": "异常与补偿",
                        "field_keys": ["exception_flow", "fallback_rules"],
                    },
                ],
            },
            {
                "section_id": "4",
                "title": "4 数据与接口需求",
                "clauses": [
                    {
                        "clause_id": "REQ-4.1",
                        "title": "输入数据",
                        "field_keys": ["input_data_sources", "input_data_mode"],
                    },
                    {
                        "clause_id": "REQ-4.2",
                        "title": "输出数据与报表",
                        "field_keys": ["output_data_products"],
                    },
                    {
                        "clause_id": "REQ-4.3",
                        "title": "外部接口",
                        "field_keys": ["external_interfaces"],
                    },
                ],
            },
            {
                "section_id": "5",
                "title": "5 非功能需求",
                "clauses": [
                    {
                        "clause_id": "REQ-5.1",
                        "title": "性能与可靠性",
                        "field_keys": ["performance_requirements", "reliability_requirements"],
                    },
                    {
                        "clause_id": "REQ-5.2",
                        "title": "安全与权限",
                        "field_keys": ["security_requirements", "permission_model"],
                    },
                    {
                        "clause_id": "REQ-5.3",
                        "title": "部署与运行环境",
                        "field_keys": ["deployment_environment"],
                    },
                    {
                        "clause_id": "REQ-5.4",
                        "title": "精度与质量约束",
                        "field_keys": ["accuracy_constraints", "quality_constraints"],
                    }
                ],
            },
            {
                "section_id": "6",
                "title": "6 验收准则",
                "clauses": [
                    {
                        "clause_id": "REQ-6.1",
                        "title": "验收场景",
                        "field_keys": ["acceptance_scenarios"],
                    },
                    {
                        "clause_id": "REQ-6.2",
                        "title": "验收准则",
                        "field_keys": ["acceptance_criteria"],
                    },
                    {
                        "clause_id": "REQ-6.3",
                        "title": "待确认事项",
                        "field_keys": ["open_decision_items"],
                    }
                ],
            },
        ],
        "form_groups": [
            {
                "group_id": "overview",
                "title": "项目概述",
                "fields": [
                    {
                        "field_key": "application_name",
                        "label": "软件名称",
                        "required": True,
                        "clause_id": "REQ-2.1",
                    },
                    {
                        "field_key": "domain_scope",
                        "label": "领域范围",
                        "required": True,
                        "clause_id": "REQ-2.1",
                    },
                    {
                        "field_key": "target_users",
                        "label": "目标用户",
                        "required": True,
                        "clause_id": "REQ-3.1",
                    },
                    {
                        "field_key": "application_scope",
                        "label": "适用范围",
                        "required": True,
                        "clause_id": "REQ-1.2",
                    },
                    {
                        "field_key": "business_goals",
                        "label": "建设目标",
                        "required": True,
                        "clause_id": "REQ-2.2",
                    },
                    {
                        "field_key": "expected_value",
                        "label": "预期价值",
                        "required": False,
                        "clause_id": "REQ-2.2",
                    },
                    {
                        "field_key": "main_scenarios",
                        "label": "主要使用场景",
                        "required": True,
                        "clause_id": "REQ-2.3",
                    },
                    {
                        "field_key": "usage_modes",
                        "label": "使用模式",
                        "required": True,
                        "clause_id": "REQ-2.3",
                    },
                    {
                        "field_key": "in_scope",
                        "label": "纳入范围",
                        "required": False,
                        "clause_id": "REQ-2.4",
                    },
                    {
                        "field_key": "out_of_scope",
                        "label": "排除范围",
                        "required": False,
                        "clause_id": "REQ-2.4",
                    },
                    {
                        "field_key": "terms_glossary",
                        "label": "术语与缩略语",
                        "required": False,
                        "clause_id": "REQ-1.3",
                    },
                ],
            },
            {
                "group_id": "function",
                "title": "功能需求",
                "fields": [
                    {
                        "field_key": "main_process",
                        "label": "核心流程名称",
                        "required": True,
                        "clause_id": "REQ-3.2",
                    },
                    {
                        "field_key": "normal_flow",
                        "label": "正常流程",
                        "required": True,
                        "clause_id": "REQ-3.2",
                    },
                    {
                        "field_key": "exception_flow",
                        "label": "异常流程",
                        "required": True,
                        "clause_id": "REQ-3.7",
                    },
                    {
                        "field_key": "situational_display",
                        "label": "态势展示能力",
                        "required": True,
                        "clause_id": "REQ-3.3",
                    },
                    {
                        "field_key": "gis_analysis_tools",
                        "label": "空间分析工具",
                        "required": True,
                        "clause_id": "REQ-3.4",
                    },
                    {
                        "field_key": "deployment_analysis",
                        "label": "部署分析能力",
                        "required": True,
                        "clause_id": "REQ-3.5",
                    },
                    {
                        "field_key": "result_outputs",
                        "label": "结果输出",
                        "required": True,
                        "clause_id": "REQ-3.6",
                    },
                    {
                        "field_key": "collaboration_mode",
                        "label": "协同方式",
                        "required": True,
                        "clause_id": "REQ-3.6",
                    },
                    {
                        "field_key": "acceptance_scenarios",
                        "label": "验收场景",
                        "required": True,
                        "clause_id": "REQ-6.1",
                    },
                    {
                        "field_key": "acceptance_criteria",
                        "label": "验收准则",
                        "required": True,
                        "clause_id": "REQ-6.2",
                    },
                ],
            },
            {
                "group_id": "data_interface",
                "title": "数据与接口需求",
                "fields": [
                    {
                        "field_key": "input_data_sources",
                        "label": "输入数据来源",
                        "required": True,
                        "clause_id": "REQ-4.1",
                    },
                    {
                        "field_key": "input_data_mode",
                        "label": "输入数据模式",
                        "required": True,
                        "clause_id": "REQ-4.1",
                    },
                    {
                        "field_key": "output_data_products",
                        "label": "输出数据与报表",
                        "required": True,
                        "clause_id": "REQ-4.2",
                    },
                    {
                        "field_key": "external_interfaces",
                        "label": "外部接口",
                        "required": False,
                        "clause_id": "REQ-4.3",
                    },
                ],
            },
            {
                "group_id": "quality",
                "title": "非功能与约束",
                "fields": [
                    {
                        "field_key": "performance_requirements",
                        "label": "性能要求",
                        "required": True,
                        "clause_id": "REQ-5.1",
                    },
                    {
                        "field_key": "reliability_requirements",
                        "label": "可靠性要求",
                        "required": True,
                        "clause_id": "REQ-5.1",
                    },
                    {
                        "field_key": "security_requirements",
                        "label": "安全要求",
                        "required": True,
                        "clause_id": "REQ-5.2",
                    },
                    {
                        "field_key": "permission_model",
                        "label": "权限模型",
                        "required": True,
                        "clause_id": "REQ-5.2",
                    },
                    {
                        "field_key": "deployment_environment",
                        "label": "部署环境",
                        "required": True,
                        "clause_id": "REQ-5.3",
                    },
                    {
                        "field_key": "accuracy_constraints",
                        "label": "精度约束",
                        "required": True,
                        "clause_id": "REQ-5.4",
                    },
                    {
                        "field_key": "quality_constraints",
                        "label": "质量约束",
                        "required": False,
                        "clause_id": "REQ-5.4",
                    },
                    {
                        "field_key": "open_decision_items",
                        "label": "待确认事项",
                        "required": False,
                        "clause_id": "REQ-6.3",
                    }
                ],
            },
        ],
        "field_mappings": [
            {"field_key": "application_name", "clause_id": "REQ-2.1", "structured_path": "application.name"},
            {"field_key": "domain_scope", "clause_id": "REQ-2.1", "structured_path": "application.domain"},
            {"field_key": "application_scope", "clause_id": "REQ-1.2", "structured_path": "application.scope"},
            {"field_key": "terms_glossary", "clause_id": "REQ-1.3", "structured_path": "document_terms"},
            {"field_key": "business_goals", "clause_id": "REQ-2.2", "structured_path": "application.goals"},
            {"field_key": "expected_value", "clause_id": "REQ-2.2", "structured_path": "application.expected_value"},
            {"field_key": "main_scenarios", "clause_id": "REQ-2.3", "structured_path": "application.main_scenarios"},
            {"field_key": "usage_modes", "clause_id": "REQ-2.3", "structured_path": "application.usage_modes"},
            {"field_key": "in_scope", "clause_id": "REQ-2.4", "structured_path": "application.scope_in"},
            {"field_key": "out_of_scope", "clause_id": "REQ-2.4", "structured_path": "application.scope_out"},
            {"field_key": "target_users", "clause_id": "REQ-3.1", "structured_path": "application.target_users"},
            {"field_key": "main_process", "clause_id": "REQ-3.2", "structured_path": "processes[0].name"},
            {"field_key": "normal_flow", "clause_id": "REQ-3.2", "structured_path": "processes[0].description"},
            {"field_key": "situational_display", "clause_id": "REQ-3.3", "structured_path": "capabilities.situational_display"},
            {"field_key": "gis_analysis_tools", "clause_id": "REQ-3.4", "structured_path": "capabilities.gis_analysis_tools"},
            {"field_key": "deployment_analysis", "clause_id": "REQ-3.5", "structured_path": "capabilities.deployment_analysis"},
            {"field_key": "result_outputs", "clause_id": "REQ-3.6", "structured_path": "outputs.result_outputs"},
            {"field_key": "collaboration_mode", "clause_id": "REQ-3.6", "structured_path": "outputs.collaboration_mode"},
            {"field_key": "exception_flow", "clause_id": "REQ-3.7", "structured_path": "rules.exception_flow"},
            {"field_key": "fallback_rules", "clause_id": "REQ-3.7", "structured_path": "rules.fallback_rules"},
            {"field_key": "input_data_sources", "clause_id": "REQ-4.1", "structured_path": "data.input_sources"},
            {"field_key": "input_data_mode", "clause_id": "REQ-4.1", "structured_path": "data.input_mode"},
            {"field_key": "output_data_products", "clause_id": "REQ-4.2", "structured_path": "data.output_products"},
            {"field_key": "external_interfaces", "clause_id": "REQ-4.3", "structured_path": "interfaces.external"},
            {
                "field_key": "performance_requirements",
                "clause_id": "REQ-5.1",
                "structured_path": "non_functional.performance",
            },
            {
                "field_key": "reliability_requirements",
                "clause_id": "REQ-5.1",
                "structured_path": "non_functional.reliability",
            },
            {"field_key": "security_requirements", "clause_id": "REQ-5.2", "structured_path": "security.requirements"},
            {"field_key": "permission_model", "clause_id": "REQ-5.2", "structured_path": "security.permission_model"},
            {
                "field_key": "deployment_environment",
                "clause_id": "REQ-5.3",
                "structured_path": "deployment.environment",
            },
            {"field_key": "accuracy_constraints", "clause_id": "REQ-5.4", "structured_path": "quality.accuracy"},
            {"field_key": "quality_constraints", "clause_id": "REQ-5.4", "structured_path": "quality.constraints"},
            {"field_key": "acceptance_scenarios", "clause_id": "REQ-6.1", "structured_path": "acceptance.scenarios"},
            {"field_key": "acceptance_criteria", "clause_id": "REQ-6.2", "structured_path": "acceptance.criteria"},
            {"field_key": "open_decision_items", "clause_id": "REQ-6.3", "structured_path": "acceptance.open_items"},
        ],
        "questionnaire_policy": {
            "mode": "cli_requirement_analysis",
            "system_role": "系统主动分析、起草和修补，专家主要判断、选择和短答。",
            "quick_inputs": ["可以", "更正式", "加超时", "重拟", "继续"],
        },
        "gap_rules": {
            "required_fields": [
                "application_name",
                "domain_scope",
                "target_users",
                "application_scope",
                "business_goals",
                "main_scenarios",
                "main_process",
                "normal_flow",
                "exception_flow",
                "situational_display",
                "gis_analysis_tools",
                "deployment_analysis",
                "result_outputs",
                "input_data_sources",
                "input_data_mode",
                "performance_requirements",
                "security_requirements",
                "deployment_environment",
                "accuracy_constraints",
                "acceptance_scenarios",
                "acceptance_criteria",
            ]
        },
        "knowledge_bindings": [
            {"archive_id": "20161116-nas", "label": "NAS 体系结构知识库", "enabled": True},
        ],
        "display_name": name,
    }
