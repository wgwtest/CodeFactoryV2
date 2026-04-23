from __future__ import annotations

from copy import deepcopy
from hashlib import md5
import json
from typing import Any

POLICY_ACTIONS = [
    "auto_pass",
    "warn_continue",
    "manual_review",
    "block_return",
    "defer_publish",
]

DEFAULT_STAGE_ORDER = [
    "asset_intake",
    "parser_router",
    "parser_execution",
    "unified_document_object",
    "evidence_constructor",
    "evidence_graph_chunk_layer",
    "evidence_pack",
    "concept_candidate_review",
    "relation_review_family_normalization",
    "definition_summary_conflict_consolidation",
    "canonical_knowledge",
    "quality_policy_evaluation_governance_gate",
    "indexes_snapshots_apis",
]


def _rule(key: str, name: str, meaning: str, threshold: str, action: str) -> dict[str, str]:
    return {
        "key": key,
        "name": name,
        "meaning": meaning,
        "threshold": threshold,
        "action": action,
    }


def _stage(
    *,
    stage_id: str,
    label: str,
    group: str,
    objective: str,
    ai_mode: str,
    default_action: str,
    inputs: list[str],
    ai_adaptation: str,
    rules: list[dict[str, str]],
    branches: list[str],
    outputs: list[str],
    observability: list[str],
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "label": label,
        "group": group,
        "enabled": True,
        "ai_mode": ai_mode,
        "default_action": default_action,
        "objective": objective,
        "inputs": inputs,
        "ai_adaptation": ai_adaptation,
        "rules": rules,
        "branches": branches,
        "outputs": outputs,
        "observability": observability,
    }


STAGE_POLICY_DEFAULTS: dict[str, dict[str, Any]] = {
    "asset_intake": _stage(
        stage_id="asset_intake",
        label="素材接入",
        group="摄取与统一",
        objective="判断当前文档能否进入正式抽取链路，并补齐基础来源标记、语种提示和扫描风险。",
        ai_mode="轻量识别 + 规则兜底",
        default_action="block_return",
        inputs=["原始文件流", "来源标记", "接入白名单"],
        ai_adaptation="AI 自动识别语种、版式和扫描特征，决定是否需要 OCR 预处理。",
        rules=[
            _rule("asset-1", "接入格式完整性", "文件必须可读取并命中允许的类型", "mime_type in allowlist && size > 0", "block_return"),
            _rule("asset-2", "来源标签补齐", "来源标签缺失时保留告警并继续", "source_label missing", "warn_continue"),
            _rule("asset-3", "扫描件分流", "扫描评分较高时自动切到 OCR 预处理", "scan_score >= 0.6", "auto_pass"),
        ],
        branches=["扫描件 -> OCR 预处理", "结构完整 -> 进入解析路由", "格式损坏 -> 阻断并退回素材池"],
        outputs=["接入质量标签", "文档类型初判", "语种提示", "预处理决策"],
        observability=["mime_type", "language_hint", "scan_score", "source_label", "intake_risk"],
    ),
    "parser_router": _stage(
        stage_id="parser_router",
        label="解析路由",
        group="摄取与统一",
        objective="为当前文档选择最合适的解析器组合和增强链路。",
        ai_mode="解析器路由建议",
        default_action="auto_pass",
        inputs=["接入质量标签", "文档类型初判", "解析器能力矩阵"],
        ai_adaptation="AI 根据版式、语言和图文比例给多条解析链路排序。",
        rules=[
            _rule("router-1", "主解析器命中率", "优先采用历史稳定性最高的解析器", "top_parser_confidence >= 0.75", "auto_pass"),
            _rule("router-2", "多语种切换", "检测到双语内容时挂载多语解析模型", "language_mix >= 2", "warn_continue"),
            _rule("router-3", "未知版式", "模板匹配过低时转人工复核候选池", "template_match < 0.45", "manual_review"),
        ],
        branches=["已知模板 -> 高速解析链", "多语文档 -> 多语解析链", "未知模板 -> 保守解析链 + 人工复核"],
        outputs=["解析器选择结果", "模板匹配结果", "增强能力挂载列表"],
        observability=["parser_choice", "template_match", "language_mix", "router_confidence"],
    ),
    "parser_execution": _stage(
        stage_id="parser_execution",
        label="解析执行",
        group="摄取与统一",
        objective="稳定产出结构化解析结果，并对缺页、乱码和表格裂解做自动补偿。",
        ai_mode="结构修复辅助",
        default_action="warn_continue",
        inputs=["解析器选择结果", "原始文件流", "预处理配置"],
        ai_adaptation="AI 对段落续接、表格裂解和标题层级混乱进行修复。",
        rules=[
            _rule("exec-1", "正文覆盖率", "正文覆盖率过低时直接阻断", "body_coverage >= 0.7", "block_return"),
            _rule("exec-2", "表格裂解修复", "表格裂解时尝试结构修复再继续", "table_split_score >= 0.5", "auto_pass"),
            _rule("exec-3", "乱码恢复", "乱码比例偏高时保留告警并继续", "garbled_ratio <= 0.08", "warn_continue"),
        ],
        branches=["解析稳定 -> 统一文档对象", "结构异常 -> 自动修复后继续", "正文缺失 -> 阻断回退"],
        outputs=["结构化正文", "表格与附件提取物", "修复日志", "段落层级结果"],
        observability=["body_coverage", "table_split_score", "garbled_ratio", "repair_count"],
    ),
    "unified_document_object": _stage(
        stage_id="unified_document_object",
        label="统一文档",
        group="摄取与统一",
        objective="把多来源解析结果压成统一文档对象，供后续证据层稳定消费。",
        ai_mode="对象整编与字段对齐",
        default_action="auto_pass",
        inputs=["结构化正文", "表格与附件提取物", "统一对象 schema"],
        ai_adaptation="AI 将标题、段落、表格、注释和附件引用统一到标准字段。",
        rules=[
            _rule("udo-1", "统一对象完整度", "缺少核心字段时不进入证据层", "required_fields >= 0.95", "block_return"),
            _rule("udo-2", "层级冲突修正", "层级冲突时按标准目录结构重排", "heading_conflict > 0", "auto_pass"),
            _rule("udo-3", "附件引用绑定", "附件无法绑定正文时发出告警", "attachment_bind_rate >= 0.85", "warn_continue"),
        ],
        branches=["对象完整 -> 证据构造", "字段缺失 -> 回退解析执行", "附件弱绑定 -> 告警继续"],
        outputs=["统一文档对象", "结构完整度评分", "字段缺失清单"],
        observability=["schema_score", "heading_conflict", "attachment_bind_rate", "missing_fields"],
    ),
    "evidence_constructor": _stage(
        stage_id="evidence_constructor",
        label="证据构造",
        group="证据与知识生成",
        objective="从统一文档对象中切出可回溯的证据片段、证据块和原文锚点。",
        ai_mode="证据片段定位",
        default_action="auto_pass",
        inputs=["统一文档对象", "证据抽取模板", "锚点定位策略"],
        ai_adaptation="AI 按语义边界和章节结构切出证据片段，并补齐原文坐标与上下文摘要。",
        rules=[
            _rule("evi-1", "最小上下文窗口", "证据必须保留前后文窗口", "context_window >= 2", "auto_pass"),
            _rule("evi-2", "锚点可回溯性", "没有原文锚点的证据不能进入图谱", "anchor_present = true", "block_return"),
            _rule("evi-3", "重复证据折叠", "重复率偏高时先做折叠再继续", "duplicate_ratio <= 0.2", "warn_continue"),
        ],
        branches=["证据稳定 -> 图谱/切块层", "锚点缺失 -> 回退统一文档", "重复过高 -> 折叠后继续"],
        outputs=["证据片段集", "原文锚点", "证据上下文摘要"],
        observability=["evidence_count", "anchor_present_rate", "duplicate_ratio", "context_window"],
    ),
    "evidence_graph_chunk_layer": _stage(
        stage_id="evidence_graph_chunk_layer",
        label="证据图谱/切块",
        group="证据与知识生成",
        objective="将证据片段组织成图谱节点和 chunk 分层，为候选知识生成准备结构化上下文。",
        ai_mode="图谱切块编排",
        default_action="auto_pass",
        inputs=["证据片段集", "图谱建模模板", "切块窗口策略"],
        ai_adaptation="AI 根据实体密度、关系密度和章节边界自动生成图谱节点与 chunk 布局。",
        rules=[
            _rule("graph-1", "切块密度控制", "单块证据过密时自动拆块", "chunk_token <= 1200", "auto_pass"),
            _rule("graph-2", "跨章混块保护", "跨章证据默认不直接混块", "cross_section_ratio <= 0.25", "warn_continue"),
            _rule("graph-3", "孤立节点率", "孤立节点过高时转人工复核", "orphan_node_ratio <= 0.18", "manual_review"),
        ],
        branches=["切块稳定 -> 证据包", "跨章混块 -> 保守拆分后继续", "孤立率过高 -> 人工复核"],
        outputs=["证据图谱节点", "chunk 分层结果", "关系候选边"],
        observability=["chunk_token", "cross_section_ratio", "orphan_node_ratio", "relation_density"],
    ),
    "evidence_pack": _stage(
        stage_id="evidence_pack",
        label="证据包",
        group="证据与知识生成",
        objective="将图谱节点、chunk 和原文证据打包成标准证据包，供后续三条 AI 审查支路消费。",
        ai_mode="证据包编排与压缩",
        default_action="auto_pass",
        inputs=["证据图谱节点", "chunk 分层结果", "关系候选边"],
        ai_adaptation="AI 自动裁剪主证据、补证据和风险摘要，保持包体紧凑且可追踪。",
        rules=[
            _rule("pack-1", "支撑文档下限", "每个候选对象至少附带主证据和补证据", "support_doc_count >= 2", "warn_continue"),
            _rule("pack-2", "证据包长度", "包体过长时自动摘要压缩", "pack_token <= 1800", "auto_pass"),
            _rule("pack-3", "引用闭环", "引用链必须能回到原文锚点", "citation_closed = true", "block_return"),
        ],
        branches=["证据包稳定 -> 三条审查支路", "包体过长 -> 摘要压缩后继续", "引用断裂 -> 回退图谱层"],
        outputs=["标准证据包", "主证据/补证据集合", "风险摘要"],
        observability=["support_doc_count", "pack_token", "citation_closed", "pack_risk_score"],
    ),
    "concept_candidate_review": _stage(
        stage_id="concept_candidate_review",
        label="概念审查",
        group="证据与知识生成",
        objective="筛出值得进入规范知识层的概念候选、术语候选和对象候选。",
        ai_mode="概念候选判断",
        default_action="manual_review",
        inputs=["标准证据包", "概念抽取提示词", "术语白名单/黑名单"],
        ai_adaptation="AI 结合证据包和术语策略生成概念候选，并判断可信门槛。",
        rules=[
            _rule("concept-1", "候选可信度", "可信度不足时转人工复核", "confidence >= 0.78", "manual_review"),
            _rule("concept-2", "术语黑名单", "黑名单术语直接剔除", "term not in blacklist", "block_return"),
            _rule("concept-3", "别名折叠", "别名重合较高时折叠到主概念", "alias_overlap >= 0.65", "auto_pass"),
        ],
        branches=["可信度高 -> 规范知识汇流", "别名重合 -> 折叠后继续", "可信度低 -> 人工复核池"],
        outputs=["概念候选集", "别名映射", "可信度评分"],
        observability=["confidence", "alias_overlap", "blacklist_hit", "candidate_count"],
    ),
    "relation_review_family_normalization": _stage(
        stage_id="relation_review_family_normalization",
        label="关系/家族",
        group="证据与知识生成",
        objective="识别关系、家族归属和继承路径，将关系表达归一到统一 schema。",
        ai_mode="关系归一与家族推断",
        default_action="warn_continue",
        inputs=["标准证据包", "关系 schema", "关系家族词表"],
        ai_adaptation="AI 自动判断关系方向、关系家族和归一化名称，避免同义关系重复入图。",
        rules=[
            _rule("relation-1", "关系方向一致性", "方向不一致时先按 schema 重写", "direction_match = true", "auto_pass"),
            _rule("relation-2", "关系证据充分性", "缺少支撑证据的关系不进入发布链", "evidence_span >= 2", "block_return"),
            _rule("relation-3", "家族归一置信度", "置信度不足时保留告警", "family_confidence >= 0.7", "warn_continue"),
        ],
        branches=["关系稳定 -> 规范知识汇流", "方向冲突 -> schema 重写继续", "证据不足 -> 阻断回退"],
        outputs=["归一关系候选", "关系家族标签", "方向修正日志"],
        observability=["direction_match", "evidence_span", "family_confidence", "relation_count"],
    ),
    "definition_summary_conflict_consolidation": _stage(
        stage_id="definition_summary_conflict_consolidation",
        label="定义/冲突",
        group="证据与知识生成",
        objective="生成定义、摘要和冲突结论，并提前清理可见冲突。",
        ai_mode="定义整合与冲突诊断",
        default_action="manual_review",
        inputs=["标准证据包", "定义模板", "冲突检测策略"],
        ai_adaptation="AI 自动汇总定义候选、摘要和冲突说明，并给出合并或阻断建议。",
        rules=[
            _rule("definition-1", "定义字段完整性", "缺少核心定义字段时不进入规范知识", "definition_core_present = true", "block_return"),
            _rule("definition-2", "冲突密度控制", "冲突密度过高时转人工复核", "conflict_density <= 0.25", "manual_review"),
            _rule("definition-3", "摘要可追溯性", "摘要至少要能回查到一个主证据", "summary_traceable = true", "warn_continue"),
        ],
        branches=["冲突可收敛 -> 规范知识汇流", "冲突过高 -> 人工复核", "定义缺失 -> 回退证据包"],
        outputs=["定义候选", "摘要候选", "冲突说明与合并建议"],
        observability=["definition_core_present", "conflict_density", "summary_traceable", "conflict_count"],
    ),
    "canonical_knowledge": _stage(
        stage_id="canonical_knowledge",
        label="规范知识",
        group="规范化与发布",
        objective="汇总三条审查支路，形成可治理、可发布、可追溯的规范知识对象。",
        ai_mode="规范对象整编",
        default_action="auto_pass",
        inputs=["概念候选集", "归一关系候选", "定义/摘要/冲突结论"],
        ai_adaptation="AI 自动拼装规范知识对象，补齐标准字段、引用索引和版本差异摘要。",
        rules=[
            _rule("canonical-1", "规范名称存在", "没有规范名称时不允许进入质量门禁", "canonical_name present", "block_return"),
            _rule("canonical-2", "引用索引完整", "引用索引缺失时保留告警继续", "citation_index >= 0.9", "warn_continue"),
            _rule("canonical-3", "对象合并阈值", "高重合对象优先合并而非重复入库", "merge_similarity >= 0.82", "auto_pass"),
        ],
        branches=["对象稳定 -> 质量门禁", "索引缺失 -> 告警继续", "名称缺失 -> 回退审查支路"],
        outputs=["规范知识对象", "引用索引", "版本差异摘要"],
        observability=["canonical_name", "citation_index", "merge_similarity", "canonical_object_score"],
    ),
    "quality_policy_evaluation_governance_gate": _stage(
        stage_id="quality_policy_evaluation_governance_gate",
        label="质量门禁",
        group="规范化与发布",
        objective="集中执行质量门禁，决定当前对象是进入发布、告警继续还是阻断。",
        ai_mode="质量门禁决策辅助",
        default_action="block_return",
        inputs=["规范知识对象", "质量策略集", "阶段级风险信号"],
        ai_adaptation="AI 根据前序阶段风险信号给出门禁建议，但最终由策略阈值决定通过、告警或阻断。",
        rules=[
            _rule("gate-1", "支撑文档下限", "支撑证据不足时直接阻断", "supporting_documents >= 2", "block_return"),
            _rule("gate-2", "风险信号汇总", "风险过高时转人工复核", "risk_score < 0.65", "manual_review"),
            _rule("gate-3", "发布前冲突清零", "存在硬冲突时禁止进入发布链", "hard_conflict = 0", "block_return"),
        ],
        branches=["门禁通过 -> 发布/API", "风险中等 -> 人工复核", "硬冲突或支撑不足 -> 阻断回退规范知识"],
        outputs=["Gate 决策", "阻断/告警原因", "人工复核转交建议"],
        observability=["supporting_documents", "risk_score", "hard_conflict", "gate_decision"],
    ),
    "indexes_snapshots_apis": _stage(
        stage_id="indexes_snapshots_apis",
        label="发布/API",
        group="规范化与发布",
        objective="控制索引、快照和 API 发布的时机、范围与降级策略。",
        ai_mode="发布策略建议",
        default_action="defer_publish",
        inputs=["Gate 决策", "发布通道配置", "索引/快照策略"],
        ai_adaptation="AI 根据对象类型、变更幅度和风险等级建议发布到哪些索引、快照和 API 通道。",
        rules=[
            _rule("publish-1", "仅门禁通过对象可发布", "未通过门禁的对象不能进入发布通道", "gate_decision = pass", "block_return"),
            _rule("publish-2", "高风险对象延迟发布", "高风险对象先保留快照，不直接开放 API", "risk_score < 0.45", "defer_publish"),
            _rule("publish-3", "索引一致性检查", "索引版本不一致时只保存快照", "index_schema_match = true", "warn_continue"),
        ],
        branches=["门禁通过 -> 正式发布", "风险偏高 -> 延迟发布并保留快照", "索引不一致 -> 仅保留快照"],
        outputs=["索引发布决策", "快照策略", "API 暴露范围"],
        observability=["gate_decision", "risk_score", "index_schema_match", "publish_scope"],
    ),
}


def build_default_archive_policy_config(archive_id: str) -> dict[str, Any]:
    return {
        "archive_id": archive_id,
        "version_label": "13 阶段抽取蓝图 v1",
        "scope_label": "单文档抽取过程",
        "ai_autoadapt_enabled": True,
        "updated_at": None,
        "stage_order": DEFAULT_STAGE_ORDER[:],
        "stages": deepcopy(STAGE_POLICY_DEFAULTS),
    }


def _normalize_action(value: Any, *, fallback: str) -> str:
    if isinstance(value, str) and value in POLICY_ACTIONS:
        return value
    return fallback


def _normalize_text_list(values: Any, fallback: list[str]) -> list[str]:
    if not isinstance(values, list):
        return fallback
    normalized = [str(item).strip() for item in values if str(item).strip()]
    return normalized or fallback


def _normalize_rules(raw_rules: Any, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(raw_rules, list):
        return fallback

    normalized: list[dict[str, str]] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            continue

        normalized.append(
            {
                "key": str(raw_rule.get("key") or f"rule-{index + 1}"),
                "name": str(raw_rule.get("name") or "未命名规则"),
                "meaning": str(raw_rule.get("meaning") or ""),
                "threshold": str(raw_rule.get("threshold") or ""),
                "action": _normalize_action(raw_rule.get("action"), fallback=fallback[min(index, len(fallback) - 1)]["action"]),
            }
        )

    return normalized or fallback


def normalize_archive_policy_config(archive_id: str, raw_config: dict[str, Any] | None) -> dict[str, Any]:
    config = build_default_archive_policy_config(archive_id)
    if not raw_config:
        return config

    config["version_label"] = str(raw_config.get("version_label") or config["version_label"])
    config["scope_label"] = str(raw_config.get("scope_label") or config["scope_label"])
    config["ai_autoadapt_enabled"] = bool(raw_config.get("ai_autoadapt_enabled", config["ai_autoadapt_enabled"]))
    config["updated_at"] = raw_config.get("updated_at")

    candidate_stage_order = [stage_id for stage_id in raw_config.get("stage_order", []) if stage_id in STAGE_POLICY_DEFAULTS]
    if candidate_stage_order:
        remaining_stage_ids = [stage_id for stage_id in DEFAULT_STAGE_ORDER if stage_id not in candidate_stage_order]
        config["stage_order"] = candidate_stage_order + remaining_stage_ids

    raw_stages = raw_config.get("stages", {})
    if not isinstance(raw_stages, dict):
        return config

    for stage_id in DEFAULT_STAGE_ORDER:
        stage_default = deepcopy(STAGE_POLICY_DEFAULTS[stage_id])
        raw_stage = raw_stages.get(stage_id, {})
        if not isinstance(raw_stage, dict):
            config["stages"][stage_id] = stage_default
            continue

        stage_default["enabled"] = bool(raw_stage.get("enabled", stage_default["enabled"]))
        stage_default["label"] = str(raw_stage.get("label") or stage_default["label"])
        stage_default["group"] = str(raw_stage.get("group") or stage_default["group"])
        stage_default["ai_mode"] = str(raw_stage.get("ai_mode") or stage_default["ai_mode"])
        stage_default["default_action"] = _normalize_action(raw_stage.get("default_action"), fallback=stage_default["default_action"])
        stage_default["objective"] = str(raw_stage.get("objective") or stage_default["objective"])
        stage_default["inputs"] = _normalize_text_list(raw_stage.get("inputs"), stage_default["inputs"])
        stage_default["ai_adaptation"] = str(raw_stage.get("ai_adaptation") or stage_default["ai_adaptation"])
        stage_default["rules"] = _normalize_rules(raw_stage.get("rules"), stage_default["rules"])
        stage_default["branches"] = _normalize_text_list(raw_stage.get("branches"), stage_default["branches"])
        stage_default["outputs"] = _normalize_text_list(raw_stage.get("outputs"), stage_default["outputs"])
        stage_default["observability"] = _normalize_text_list(raw_stage.get("observability"), stage_default["observability"])
        config["stages"][stage_id] = stage_default

    return config


def build_policy_run_snapshot(
    archive_id: str,
    policy_config: dict[str, Any] | None,
    *,
    captured_at: str | None,
) -> dict[str, Any]:
    normalized = normalize_archive_policy_config(archive_id, policy_config)
    snapshot_payload = {
        "archive_id": archive_id,
        "version_label": normalized["version_label"],
        "scope_label": normalized["scope_label"],
        "ai_autoadapt_enabled": normalized["ai_autoadapt_enabled"],
        "config_updated_at": normalized.get("updated_at"),
        "stage_order": normalized["stage_order"],
        "stages": [
            {
                "stage_id": stage_id,
                "label": normalized["stages"][stage_id]["label"],
                "enabled": normalized["stages"][stage_id]["enabled"],
                "ai_mode": normalized["stages"][stage_id]["ai_mode"],
                "default_action": normalized["stages"][stage_id]["default_action"],
                "rule_count": len(normalized["stages"][stage_id]["rules"]),
                "rules": deepcopy(normalized["stages"][stage_id]["rules"]),
            }
            for stage_id in normalized["stage_order"]
            if stage_id in normalized["stages"]
        ],
    }
    snapshot_json = json.dumps(snapshot_payload, ensure_ascii=False, sort_keys=True)
    snapshot_id = md5(snapshot_json.encode("utf-8")).hexdigest()[:12]
    return {
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        **snapshot_payload,
    }
