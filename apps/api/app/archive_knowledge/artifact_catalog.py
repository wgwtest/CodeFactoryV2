from __future__ import annotations

from typing import TypedDict


class ArtifactInterpretation(TypedDict):
    kind_label: str
    family_code: str | None
    family_label: str | None
    display_name: str | None
    standard_name: str | None
    summary: str
    producer_hint: str | None


ARTIFACT_FAMILIES: dict[str, dict[str, str]] = {
    "AV": {
        "family_label": "架构总览",
        "generic_summary": "用于说明架构范围、背景、术语和总体说明。",
    },
    "OV": {
        "family_label": "运行视图",
        "generic_summary": "用于描述业务运行概念、活动和信息交换需求。",
    },
    "SV": {
        "family_label": "系统视图",
        "generic_summary": "用于描述系统、接口、功能以及系统随时间的实现演进。",
    },
    "TV": {
        "family_label": "技术视图",
        "generic_summary": "用于描述适用标准、技术约束和技术演进方向。",
    },
}

ARTIFACT_DETAILS: dict[str, dict[str, str]] = {
    "AV-1": {
        "display_name": "概述与摘要信息",
        "standard_name": "Overview and Summary Information",
        "summary": "AV-1 是架构总览中的架构工件，用于说明架构范围、背景、目标和使用边界。",
    },
    "AV-2": {
        "display_name": "集成词典",
        "standard_name": "Integrated Dictionary",
        "summary": "AV-2 是架构总览中的架构工件，用于统一定义架构中的术语、数据元素和缩写。",
    },
    "OV-1": {
        "display_name": "高层运行概念图",
        "standard_name": "High-Level Operational Concept Graphic",
        "summary": "OV-1 是运行视图中的架构工件，用于展示高层运行概念和业务场景。",
    },
    "OV-2": {
        "display_name": "运行节点连接描述",
        "standard_name": "Operational Node Connectivity Description",
        "summary": "OV-2 是运行视图中的架构工件，用于描述运行节点之间的连接关系和协作边界。",
    },
    "OV-3": {
        "display_name": "运行信息交换矩阵",
        "standard_name": "Operational Information Exchange Matrix",
        "summary": "OV-3 是运行视图中的架构工件，用于说明运行节点之间交换了什么信息以及交换条件。",
    },
    "OV-5": {
        "display_name": "运行活动模型",
        "standard_name": "Operational Activity Model",
        "summary": "OV-5 是运行视图中的架构工件，用于描述业务活动、活动分解及其输入输出关系。",
    },
    "OV-7": {
        "display_name": "逻辑数据模型",
        "standard_name": "Logical Data Model",
        "summary": "OV-7 是运行视图中的架构工件，用于定义业务语义上的数据对象及其关系。",
    },
    "SV-1": {
        "display_name": "系统接口描述",
        "standard_name": "Systems Interface Description",
        "summary": "SV-1 是系统视图中的架构工件，用于描述系统之间的接口和连接关系。",
    },
    "SV-2": {
        "display_name": "系统通信描述",
        "standard_name": "Systems Communications Description",
        "summary": "SV-2 是系统视图中的架构工件，用于描述系统通信路径和通信约束。",
    },
    "SV-4": {
        "display_name": "系统功能描述",
        "standard_name": "Systems Functionality Description",
        "summary": "SV-4 是系统视图中的架构工件，用于描述系统提供的功能以及功能间关系。",
    },
    "SV-5": {
        "display_name": "运行活动到系统功能追踪矩阵",
        "standard_name": "Operational Activity to Systems Function Traceability Matrix",
        "summary": "SV-5 是系统视图中的架构工件，用于把业务活动与系统功能建立追踪关系。",
    },
    "SV-6": {
        "display_name": "系统数据交换矩阵",
        "standard_name": "Systems Data Exchange Matrix",
        "summary": "SV-6 是系统视图中的架构工件，用于描述系统之间交换的数据及其约束。",
    },
    "SV-7": {
        "display_name": "系统性能参数矩阵",
        "standard_name": "Systems Performance Parameters Matrix",
        "summary": "SV-7 是系统视图中的架构工件，用于描述系统性能指标和约束参数。",
    },
    "SV-8": {
        "display_name": "系统演进描述",
        "standard_name": "Systems Evolution Description",
        "summary": "SV-8 是系统视图中的架构工件，用于描述系统或服务随时间的演进计划。",
    },
    "SV-9": {
        "display_name": "系统技术预测",
        "standard_name": "Systems Technology Forecast",
        "summary": "SV-9 是系统视图中的架构工件，用于描述支撑系统演进的技术趋势和技术路线。",
    },
    "TV-1": {
        "display_name": "技术标准概况",
        "standard_name": "Technical Standards Profile",
        "summary": "TV-1 是技术视图中的架构工件，用于说明当前适用的标准和技术规范。",
    },
    "TV-2": {
        "display_name": "技术标准预测",
        "standard_name": "Technical Standards Forecast",
        "summary": "TV-2 是技术视图中的架构工件，用于描述未来拟采用的标准和技术演进方向。",
    },
}

CATEGORY_LABELS: dict[str, str] = {
    "organization": "组织",
    "system_or_service": "系统/服务",
    "architecture_concept": "架构概念",
    "architecture_artifact": "架构工件",
    "domain_concept": "领域概念",
    "service_category": "服务分类",
    "service_taxonomy": "服务分类",
    "operational_node": "运行节点",
    "information_exchange": "信息交换",
    "timeline_event": "时间事件",
    "domain_process": "领域流程",
}


def build_interpretation(name: str, category: str) -> ArtifactInterpretation:
    normalized_name = name.upper()
    if category == "architecture_artifact":
        family_code = normalized_name.split("-", 1)[0] if "-" in normalized_name else None
        family = ARTIFACT_FAMILIES.get(family_code or "")
        detail = ARTIFACT_DETAILS.get(normalized_name, {})
        family_label = family["family_label"] if family else None
        generic_summary = family["generic_summary"] if family else "用于表达特定架构视角下的结构化说明。"
        return {
            "kind_label": "架构工件",
            "family_code": family_code,
            "family_label": family_label,
            "display_name": detail.get("display_name"),
            "standard_name": detail.get("standard_name"),
            "summary": detail.get("summary", f"{normalized_name} 是架构工件，{generic_summary}"),
            "producer_hint": "当前档案未识别明确责任方；按工件类型推断，通常由体系架构或运行活动分析产出。",
        }

    if category == "operational_node":
        return {
            "kind_label": "运行节点",
            "family_code": None,
            "family_label": None,
            "display_name": None,
            "standard_name": None,
            "summary": f"{name} 是运行节点，表示在业务运行体系中承担职责、交换信息的参与方或岗位。",
            "producer_hint": "通常在 OV-2 / OV-3 等运行架构分析中识别。",
        }

    if category == "information_exchange":
        return {
            "kind_label": "信息交换",
            "family_code": None,
            "family_label": None,
            "display_name": None,
            "standard_name": None,
            "summary": f"{name} 是运行节点之间传递的信息交换项，用于表达交互内容或消息主题。",
            "producer_hint": "通常与运行节点连接关系一起在 OV-2 / OV-3 中识别。",
        }

    kind_label = CATEGORY_LABELS.get(category, category)
    return {
        "kind_label": kind_label,
        "family_code": None,
        "family_label": None,
        "display_name": None,
        "standard_name": None,
        "summary": f"{name} 是{kind_label}类实体。",
        "producer_hint": None,
    }
