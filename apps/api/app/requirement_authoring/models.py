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
                        "title": "异常与补偿",
                        "field_keys": ["exception_flow"],
                    },
                ],
            },
            {
                "section_id": "4",
                "title": "4 非功能需求",
                "clauses": [
                    {
                        "clause_id": "REQ-4.1",
                        "title": "性能与可靠性",
                        "field_keys": ["non_functional"],
                    }
                ],
            },
            {
                "section_id": "5",
                "title": "5 验收准则",
                "clauses": [
                    {
                        "clause_id": "REQ-5.1",
                        "title": "验收准则",
                        "field_keys": ["acceptance_criteria"],
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
                        "clause_id": "REQ-3.3",
                    },
                    {
                        "field_key": "acceptance_criteria",
                        "label": "验收准则",
                        "required": True,
                        "clause_id": "REQ-5.1",
                    },
                ],
            },
            {
                "group_id": "quality",
                "title": "非功能需求",
                "fields": [
                    {
                        "field_key": "non_functional",
                        "label": "性能与可靠性",
                        "required": True,
                        "clause_id": "REQ-4.1",
                    }
                ],
            },
        ],
        "field_mappings": [
            {"field_key": "application_name", "clause_id": "REQ-2.1", "structured_path": "application.name"},
            {"field_key": "domain_scope", "clause_id": "REQ-2.1", "structured_path": "application.domain"},
            {"field_key": "target_users", "clause_id": "REQ-3.1", "structured_path": "application.target_users"},
            {"field_key": "main_process", "clause_id": "REQ-3.2", "structured_path": "processes[0].name"},
            {"field_key": "normal_flow", "clause_id": "REQ-3.2", "structured_path": "processes[0].description"},
            {"field_key": "exception_flow", "clause_id": "REQ-3.3", "structured_path": "rules.exception_flow"},
            {"field_key": "non_functional", "clause_id": "REQ-4.1", "structured_path": "non_functional_constraints[0]"},
            {"field_key": "acceptance_criteria", "clause_id": "REQ-5.1", "structured_path": "metrics.acceptance"},
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
                "main_process",
                "normal_flow",
                "exception_flow",
                "acceptance_criteria",
                "non_functional",
            ]
        },
        "knowledge_bindings": [
            {"archive_id": "20161116-nas", "label": "NAS 体系结构知识库", "enabled": True},
        ],
        "display_name": name,
    }
