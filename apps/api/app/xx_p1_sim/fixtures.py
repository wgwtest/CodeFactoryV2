from __future__ import annotations

ARCHIVE_VERSION = "v1.0"
FIXED_SEED = "xx-p1-sim-fixed-v1"
PUBLISHED_AT = "2026-04-30T00:00:00+00:00"

PROVIDER = {
    "provider_id": "xx-p1-sim",
    "provider_name": "XX-P1-Sim",
    "provider_kind": "p1_knowledge_provider",
    "status": "online",
    "capabilities": ["domain_catalog", "knowledge_archive"],
    "version": ARCHIVE_VERSION,
    "seed": FIXED_SEED,
}

DOMAINS = [
    {
        "domain_id": "airspace-planning",
        "domain_name": "空域规划领域知识",
        "domain_summary": "包含空域对象、冲突窗口、协同规划流程、会签约束和证据片段。",
        "archive_version": ARCHIVE_VERSION,
        "concept_count": 12,
        "rule_count": 8,
        "process_count": 3,
        "evidence_count": 18,
    },
    {
        "domain_id": "government-service",
        "domain_name": "政务服务领域知识",
        "domain_summary": "包含预约、窗口、排队、办理状态和服务评价知识。",
        "archive_version": ARCHIVE_VERSION,
        "concept_count": 9,
        "rule_count": 6,
        "process_count": 4,
        "evidence_count": 12,
    },
    {
        "domain_id": "supply-chain-collaboration",
        "domain_name": "供应链协同领域知识",
        "domain_summary": "包含订单、交付、异常协同和履约约束知识。",
        "archive_version": ARCHIVE_VERSION,
        "concept_count": 10,
        "rule_count": 7,
        "process_count": 4,
        "evidence_count": 14,
    },
]

ARCHIVES = {
    "airspace-planning": {
        "provider_id": "xx-p1-sim",
        "domain_id": "airspace-planning",
        "archive_id": "archive-airspace-planning-v1",
        "archive_version": ARCHIVE_VERSION,
        "published_at": PUBLISHED_AT,
        "concepts": [
            {
                "concept_id": "concept-airspace-cell",
                "name": "空域单元",
                "definition": "用于表达可规划、可协调和可约束的空域范围。",
            },
            {
                "concept_id": "concept-conflict-window",
                "name": "冲突窗口",
                "definition": "两个或多个规划对象在时间和空间上存在冲突风险的窗口。",
            },
            {
                "concept_id": "concept-coordination-task",
                "name": "协同任务",
                "definition": "围绕冲突识别、会签确认和结果发布形成的协同处理事项。",
            },
        ],
        "entities": [
            {
                "concept_id": "entity-duty-office",
                "name": "值班席位",
                "definition": "负责接收、研判和处置空域规划协同任务的业务席位。",
            }
        ],
        "rules": [
            {
                "rule_id": "rule-confirm-conflict-window",
                "name": "冲突窗口确认规则",
                "description": "冲突窗口未确认时，不得直接发布规划结果。",
            },
            {
                "rule_id": "rule-audit-key-state",
                "name": "关键状态留痕规则",
                "description": "会签、驳回、发布等关键状态必须保留审计证据。",
            },
        ],
        "processes": [
            {
                "process_id": "process-airspace-coordination",
                "name": "空域规划协同流程",
                "steps": ["任务创建", "冲突识别", "协同会签", "结果发布"],
            }
        ],
        "constraints": [
            {
                "constraint_id": "constraint-audit-trace",
                "category": "traceability",
                "description": "关键状态变化需要保留责任人、时间和依据。",
            }
        ],
        "evidence_refs": [
            {
                "evidence_id": "evidence-airspace-term",
                "source": "P1 发布态领域知识",
                "excerpt": "空域规划过程应围绕空域单元、冲突窗口和协同任务形成可追溯记录。",
            }
        ],
    },
    "government-service": {
        "provider_id": "xx-p1-sim",
        "domain_id": "government-service",
        "archive_id": "archive-government-service-v1",
        "archive_version": ARCHIVE_VERSION,
        "published_at": PUBLISHED_AT,
        "concepts": [
            {"concept_id": "concept-appointment", "name": "预约", "definition": "服务对象发起的办理时段申请。"},
            {"concept_id": "concept-service-window", "name": "窗口", "definition": "承接政务服务事项的办理单元。"},
        ],
        "entities": [],
        "rules": [
            {"rule_id": "rule-queue", "name": "排队规则", "description": "预约和现场排队需要形成统一叫号序列。"}
        ],
        "processes": [
            {"process_id": "process-service", "name": "政务服务办理流程", "steps": ["预约", "取号", "办理", "评价"]}
        ],
        "constraints": [
            {"constraint_id": "constraint-status", "category": "status", "description": "办理状态需要面向用户可查询。"}
        ],
        "evidence_refs": [
            {"evidence_id": "evidence-service", "source": "P1 发布态领域知识", "excerpt": "政务服务过程需要公开办理状态。"}
        ],
    },
    "supply-chain-collaboration": {
        "provider_id": "xx-p1-sim",
        "domain_id": "supply-chain-collaboration",
        "archive_id": "archive-supply-chain-v1",
        "archive_version": ARCHIVE_VERSION,
        "published_at": PUBLISHED_AT,
        "concepts": [
            {"concept_id": "concept-order", "name": "订单", "definition": "供应链协同中的需求和履约载体。"},
            {"concept_id": "concept-delivery", "name": "交付", "definition": "围绕订单形成的供给结果。"},
        ],
        "entities": [],
        "rules": [
            {"rule_id": "rule-exception", "name": "异常协同规则", "description": "交付异常需要通知责任方并保留处置记录。"}
        ],
        "processes": [
            {"process_id": "process-delivery", "name": "订单履约流程", "steps": ["下单", "确认", "交付", "验收"]}
        ],
        "constraints": [
            {"constraint_id": "constraint-delivery", "category": "fulfillment", "description": "履约节点需要可追踪。"}
        ],
        "evidence_refs": [
            {"evidence_id": "evidence-supply", "source": "P1 发布态领域知识", "excerpt": "供应链协同需要围绕订单和交付管理异常。"}
        ],
    },
}
