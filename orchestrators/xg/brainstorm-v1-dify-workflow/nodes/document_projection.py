
import json
import re

SECTION_ANCHORS = {
    "1 总则 / 编写目的": "REQ-1.1",
    "2 项目概述 / 软件定位": "REQ-2.1",
    "3 功能需求 / 用户与角色": "REQ-3.1",
    "3 功能需求 / 核心业务流程": "REQ-3.2",
    "3 功能需求 / 功能分解总览": "REQ-3.3",
    "3 功能需求 / 核心功能项说明": "REQ-3.4",
    "3 功能需求 / 结果输出与共享": "REQ-3.6",
    "3 功能需求 / 异常与补偿": "REQ-3.7",
    "4 数据需求 / 输入数据": "REQ-4.1",
    "4 数据需求 / 输出数据与报表": "REQ-4.2",
    "5 非功能需求 / 性能与可靠性": "REQ-5.1",
    "5 非功能需求 / 安全与权限": "REQ-5.2",
    "5 非功能需求 / 部署与运行环境": "REQ-5.3",
    "5 非功能需求 / 精度与质量约束": "REQ-5.4",
    "6 验收准则 / 验收准则": "REQ-6.2",
}
DRAFT_TRIGGERS = ["停止追问", "输出草案", "先成稿", "不要继续问", "先停止追问", "生成草案"]
REVIEW_TRIGGERS = ["回看", "总结", "已闭合", "未闭合", "哪些关键决策", "不要急着写全文", "先检查"]
CORRECTION_TRIGGERS = ["不是", "不对", "修正", "更正", "撤回", "替换", "改成"]
STALE_FALLBACK_QUESTION = "请继续补充一个可以写入需求规格说明的事实，例如用户、场景、流程、边界或验收口径。"
STALE_GAP_MARKERS = [
    "组织器策略问题",
    "请先确认软件名称、背景领域和编写目的",
    "可以补齐：组织器策略问题",
]

def _loads(value, fallback):
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass
        return fallback

def _item_text(item):
    if isinstance(item, dict):
        for key in ["content", "label", "question", "text", "title"]:
            value = str(item.get(key) or "").strip()
            if value:
                return value
        return json.dumps(item, ensure_ascii=False)
    return str(item or "").strip()

def _content_text(item):
    if isinstance(item, dict):
        for key in ["content", "label", "question", "text", "title"]:
            value = str(item.get(key) or "").strip()
            if value:
                return value
        return ""
    return str(item or "").strip()

def _contains(text, words):
    return any(word in text for word in words)

def _draft_requested(text, context):
    normalized = context.get("normalized_context") or {}
    if normalized.get("draft_requested") is True:
        return True
    compact = re.sub(r"\s+", "", str(text or ""))
    return any(trigger in compact for trigger in DRAFT_TRIGGERS)

def _review_requested(text):
    compact = re.sub(r"\s+", "", str(text or ""))
    if any(trigger in compact for trigger in DRAFT_TRIGGERS):
        return False
    supplement_markers = ["补充", "采用", "固定", "不需要", "不做", "支持", "优先", "模板结构"]
    concrete_fact_markers = ["GIS", "GeoPackage", "瓦片", "81433", "数据接入", "标准", "章节", "界面", "协同", "验收", "精度", "导出"]
    if any(marker in compact for marker in supplement_markers) and any(marker in compact for marker in concrete_fact_markers):
        return False
    return any(trigger in compact for trigger in REVIEW_TRIGGERS)

def _correction_requested(text):
    compact = re.sub(r"\s+", "", str(text or ""))
    return any(trigger in compact for trigger in CORRECTION_TRIGGERS)

def _is_draft_only(text):
    compact = re.sub(r"\s+", "", str(text or ""))
    if not any(trigger in compact for trigger in DRAFT_TRIGGERS):
        return False
    removed = compact
    for trigger in DRAFT_TRIGGERS + ["并", "请", "基于已确认信息", "保留未闭合问题", "需求规格说明", "一版", "当前", "信息"]:
        removed = removed.replace(trigger, "")
    return len(removed) <= 8

def _split_enumeration_items(part):
    if "、" not in part:
        return [part]
    nonfunctional_markers = [
        "非功能", "内网部署", "专网", "离线", "运行环境", "部署环境",
        "角色权限", "操作审计", "审计", "权限", "安全",
        "可追溯", "追溯", "质量", "精度", "性能", "可靠性",
    ]
    if sum(1 for marker in nonfunctional_markers if marker in part) < 2:
        return [part]
    items = [item.strip("，,、 ") for item in part.split("、") if item.strip("，,、 ")]
    return items or [part]

def _split_clauses(text):
    text = str(text or "").strip()
    if not text:
        return []
    cleaned = re.sub(r"\s+", "", text)
    parts = re.split(r"[。；;\n]|，(?=(?:主要|下游|主场景|数据|部署|系统|软件|用户|验收|不做|也不做|不承诺|不支持|不包含|只做|包含|支持|精度|导出|协同|刷新|界面|页面|异常|安全|性能|非功能|内网|角色权限|操作审计|结果可追溯))", cleaned)
    result = []
    for part in parts:
        for item in _split_enumeration_items(part.strip("，,、 ")):
            item = item.strip("，,、 ")
            if not item:
                continue
            if len(item) <= 1:
                continue
            result.append(item)
    return result[:12]

def _classify(text, active_section):
    t = str(text or "")
    if _contains(t, ["不做", "不希望", "不支持", "不包含", "不承诺", "边界", "范围", "只做", "排除", "不负责"]):
        return "2 项目概述 / 软件定位"
    if _contains(t, ["导出验收", "验收", "验收标准", "通过条件", "准则", "测试口径", "判定标准", "任务链验收"]):
        return "6 验收准则 / 验收准则"
    if _contains(t, ["异常", "失败", "补偿", "重试", "回滚", "告警处理", "错误"]):
        return "3 功能需求 / 异常与补偿"
    if _contains(t, ["主要界面", "界面", "页面", "入口", "态势总览", "列表", "看板"]):
        return "3 功能需求 / 功能分解总览"
    if _contains(t, ["部署分析", "部署影响分析"]) or ("部署" in t and _contains(t, ["覆盖", "冲突", "影响分析", "分析系统", "分析工具"])):
        return "3 功能需求 / 核心功能项说明"
    if _contains(t, ["业务专家复核", "成果导出复核", "导出地图", "导出结果", "导出参数", "导出说明", "给业务专家复核", "结果消费"]):
        return "3 功能需求 / 结果输出与共享"
    if _contains(t, ["协同", "共享", "任务接力", "批注", "协作", "共编", "多人"]):
        return "3 功能需求 / 结果输出与共享"
    if _contains(t, ["输入数据", "底图", "DEM", "地形数据", "矢量", "栅格", "业务对象数据", "分析参数", "内网数据加载", "文件导入", "数据接入", "导入"]):
        return "4 数据需求 / 输入数据"
    if _contains(t, ["输出", "地图图片", "工程文件", "结果参数表", "结果图层", "简要报告", "报告片段", "专题图件", "导出形式", "导出格式", "PDF", "GeoPackage"]):
        return "4 数据需求 / 输出数据与报表"
    if _contains(t, ["安全", "权限", "认证", "审计", "账号", "角色权限", "日志"]):
        return "5 非功能需求 / 安全与权限"
    if _contains(t, ["内网部署", "专网部署", "离线部署", "部署环境", "运行环境", "内网", "专网", "离线运行"]):
        return "5 非功能需求 / 部署与运行环境"
    if _contains(t, ["性能", "并发", "响应时间", "刷新", "可靠性", "高可用", "容灾", "流畅", "可接受时间"]):
        return "5 非功能需求 / 性能与可靠性"
    if _contains(t, ["精度", "精度口径", "超精度", "误差", "分辨率", "准确性", "数据来源", "算法参数", "适用限制", "质量", "追溯", "可追溯"]):
        return "5 非功能需求 / 精度与质量约束"
    if _contains(t, ["用户", "角色", "使用者", "下游", "指挥员", "参谋", "值班员", "管理员", "职责"]):
        return "3 功能需求 / 用户与角色"
    if _contains(t, ["通视", "量算", "坡度", "坡向", "高程剖面", "部署分析", "覆盖", "冲突", "影响分析", "分析工具", "大气光照", "态势工程管理", "态势编辑", "地图浏览", "图层控制", "标绘", "功能"]):
        return "3 功能需求 / 核心功能项说明"
    if _contains(t, ["流程", "场景", "实时", "展示", "GIS", "告警", "任务区", "标注", "报告导出", "报告"]):
        return "3 功能需求 / 核心业务流程"
    if _contains(t, ["软件名称", "系统叫", "叫", "名称", "领域", "编写目的", "目的", "背景", "系统名称", "主要解决", "解决", "平台", "软件"]):
        return "1 总则 / 编写目的"
    if active_section in SECTION_ANCHORS and active_section != "1 总则 / 编写目的":
        return active_section
    return ""

def _selected_option_fact(semantic, context):
    text = str(semantic or "").strip()
    match = re.match(r"^(?:我选|选择|选)?\s*([A-Da-d])(?:[\.。:：、\s]|$)", text)
    if not match:
        return ""
    key = match.group(1).upper()
    options = (context.get("normalized_context") or {}).get("last_options") or []
    for option in options:
        if isinstance(option, dict):
            option_key = str(option.get("key") or "").strip().upper()
            label = str(option.get("label") or option.get("content") or "").strip()
            if option_key == key and label:
                return label
        elif isinstance(option, str):
            idx = ord(key) - ord("A")
            if 0 <= idx < len(options):
                return str(options[idx]).strip()
    if len(text) <= 3:
        return f"用户选择了上一轮选项 {key}"
    return text

def _existing_fact_records(context):
    records = []
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    sources = []
    sources.extend(state.get("confirmed_facts") or [])
    sources.extend(state.get("confirmed_decisions") or [])
    sources.extend(context.get("confirmed_facts") or [])
    for item in sources:
        content = _clean_fact_text(_item_text(item))
        if not content or _is_uncertain_statement(content):
            continue
        section = ""
        if isinstance(item, dict):
            section = str(item.get("target_section") or "").strip()
        if not section:
            section = _classify(content, str(context.get("active_section") or ""))
        if not section:
            continue
        record = {"content": content, "target_section": section, "anchor_path": SECTION_ANCHORS.get(section, "REQ-1.1")}
        if record not in records:
            records.append(record)
    return records

def _records_from_working_document(context):
    records = []
    working = context.get("working_document") if isinstance(context.get("working_document"), dict) else {}
    for block in working.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        section = str(block.get("target_section") or block.get("section") or block.get("heading") or "").strip()
        content = _clean_fact_text(_content_text(block))
        if not content or _is_uncertain_statement(content):
            continue
        if not section:
            section = _classify(content, str(context.get("active_section") or ""))
        if not section:
            continue
        record = {"content": content, "target_section": section, "anchor_path": SECTION_ANCHORS.get(section, "REQ-1.1")}
        if record not in records:
            records.append(record)
    return records

def _extract_records(context):
    semantic = str(context.get("semantic") or "").strip()
    active_section = str(context.get("active_section") or "")
    if not semantic or _is_draft_only(semantic):
        return []
    option_fact = _selected_option_fact(semantic, context)
    source_text = option_fact or semantic
    records = []
    for clause in _split_clauses(source_text):
        if any(trigger in clause for trigger in DRAFT_TRIGGERS):
            continue
        section = _classify(clause, active_section)
        if not section:
            continue
        content = _clean_fact_text(clause)
        if not content or _is_uncertain_statement(content):
            continue
        record = {
            "content": content,
            "target_section": section,
            "anchor_path": SECTION_ANCHORS.get(section, context.get("anchor_path") or "REQ-1.1"),
        }
        if record not in records:
            records.append(record)
    return records

def _make_item(prefix, idx, content, section, status="active", source_turn_id="turn-0001"):
    return {
        "item_id": f"{prefix}-{idx:03d}",
        "content": content,
        "source_turn_id": source_turn_id,
        "target_section": section,
        "status": status,
    }

def _stable_question_id(text, idx):
    normalized = re.sub(r"\W+", "", str(text or ""))[:18]
    return f"open-question-{idx:03d}-{normalized}" if normalized else f"open-question-{idx:03d}"

def _is_stale_fallback(text):
    value = str(text or "").strip()
    return value == STALE_FALLBACK_QUESTION or "请继续补充一个可以写入需求规格说明的事实" in value

def _is_stale_gap(text):
    value = str(text or "").strip()
    return _is_stale_fallback(value) or any(marker in value for marker in STALE_GAP_MARKERS)

UNCERTAIN_MARKERS = ["没想清楚", "不确定", "暂时", "倾向", "可能", "希望你", "帮我想", "待确认"]
NOISE_PREFIXES = ["不完全是这些选项", "我选", "选择"]
UNCERTAIN_PREFIX_PATTERNS = [
    r"^这个我还没完全想清楚[，,但目前倾向于]*",
    r"^我还没完全想清楚[，,但目前倾向于]*",
    r"^但目前倾向于",
    r"^目前倾向于",
]

def _clean_fact_text(text):
    value = str(text or "").strip()
    for prefix in NOISE_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix):].strip("。；;，,、:： ")
    for pattern in UNCERTAIN_PREFIX_PATTERNS:
        value = re.sub(pattern, "", value).strip("。；;，,、:： ")
    value = re.sub(r"^【[^】]{1,24}】", "", value).strip()
    value = re.sub(r"[。；;]+$", "", value).strip()
    return value

def _is_decision_record(record):
    section = str(record.get("target_section") or "")
    content = _clean_fact_text(record.get("content") or "")
    if not content:
        return False
    if section in {
        "2 项目概述 / 软件定位",
        "3 功能需求 / 用户与角色",
        "3 功能需求 / 核心业务流程",
        "3 功能需求 / 结果输出与共享",
        "4 数据需求 / 输入数据",
        "4 数据需求 / 输出数据与报表",
        "5 非功能需求 / 性能与可靠性",
        "5 非功能需求 / 安全与权限",
        "5 非功能需求 / 部署与运行环境",
        "5 非功能需求 / 精度与质量约束",
        "6 验收准则 / 验收准则",
    }:
        return True
    return _contains(
        content,
        [
            "第一阶段",
            "主要用户",
            "核心流程",
            "不做",
            "不承诺",
            "作为辅助判断",
            "以文件导入导出",
            "内网数据加载",
            "验收",
            "权限",
            "审计",
            "部署",
            "精度",
            "性能",
        ],
    )

def _is_uncertain_statement(text):
    value = str(text or "").strip()
    if not value:
        return True
    if any(marker in value for marker in ["希望你来一块帮我想清楚", "当前用户", "使用模式", "没有想清楚"]):
        return True
    if any(marker in value for marker in UNCERTAIN_MARKERS):
        return not any(anchor in value for anchor in ["主要用户", "第一阶段", "不做", "需要", "包括", "输入", "输出", "验收", "异常"])
    return False

def _ensure_sentence(text):
    value = _clean_fact_text(text)
    if not value:
        return ""
    return value if value.endswith(("。", "；", ";")) else value + "。"

def _patches_from_records(records, write_policy):
    patches = []
    for idx, record in enumerate(records, 1):
        section = record["target_section"]
        heading = section.split("/")[-1].strip() or section
        patches.append({
            "plan_ref": f"BRAINSTORM-DIFY-AP-{idx:03d}",
            "operation": "append_or_update",
            "content": f"【{heading}】{record['content']}。",
            "write_policy": write_policy,
            "target_section": section,
            "anchor_path": record["anchor_path"],
        })
    return patches

def _status_review(context):
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    fact_texts = []
    for item in (state.get("confirmed_facts") or []) + (context.get("confirmed_facts") or []):
        text = _item_text(item)
        if text and text not in fact_texts:
            fact_texts.append(text)
    closed = fact_texts[:8]
    open_items = []
    for question in (context.get("normalized_context") or {}).get("open_question_summaries") or []:
        text = str(question or "").strip()
        if text and not _is_stale_gap(text) and text not in open_items:
            open_items.append(text)
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    for question in state.get("open_questions") or []:
        text = _item_text(question)
        if text and not _is_stale_gap(text) and text not in open_items:
            open_items.append(text)
    if not open_items:
        open_items = [
            "验收口径仍需确认。",
            "非功能约束仍需确认。",
            "是否直接输出草案仍需确认。",
        ]
    closed_text = "；".join(closed) if closed else "已确认的用户、流程、边界或质量要求将作为草案基础"
    open_text = "；".join(open_items[:5])
    return {
        "assistant_message": f"已闭合：{closed_text}。仍未闭合：{open_text}。建议下一步优先确认验收口径或直接输出当前草案。",
        "next_question": "接下来优先处理哪个未闭合项？",
        "quick_options": [
            {"key": "A", "label": "补齐验收口径", "recommended": True},
            {"key": "B", "label": "补齐非功能约束", "recommended": False},
            {"key": "C", "label": "直接输出当前草案", "recommended": False},
            {"key": "D", "label": "继续补充自定义事项", "recommended": False},
        ],
        "document_patch": [],
        "filled_document_text": "",
        "changed_sections": [],
        "decision_state_delta": {
            "confirmed_facts": [],
            "confirmed_decisions": [],
            "tentative_assumptions": [],
            "open_questions": [],
            "closed_question_refs": [],
            "deferred_question_refs": [],
            "superseded_question_refs": [],
            "rejected_directions": [],
            "chapter_projections": [],
            "next_focus": "review_followup",
        },
        "confirmed_facts_delta": [],
        "open_questions_delta": [],
        "question_state_changes": {
            "closed_question_ids": [],
            "deferred_question_ids": [],
            "superseded_question_ids": [],
            "removed_stale_question_ids": [],
            "created_question_ids": [],
        },
        "branch_taken": "review_status",
        "intent": "review_status",
        "retained_gaps": open_items[:5],
        "target_anchor_plan": [],
        "projection_rules_applied": [],
    }

def _group_by_section(records):
    grouped = {section: [] for section in SECTION_ANCHORS}
    for record in records:
        section = record.get("target_section") or ""
        content = _clean_fact_text(record.get("content") or "")
        if section in grouped and content and not _is_uncertain_statement(content) and content not in grouped[section]:
            grouped[section].append(content)
    return grouped

def _retained_gaps(context, grouped):
    known_questions = (context.get("normalized_context") or {}).get("open_question_summaries") or []
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    for question in state.get("open_questions") or []:
        text = _item_text(question)
        if text:
            known_questions.append(text)
    gaps = []
    for question in known_questions:
        text = str(question or "").strip()
        if _is_stale_gap(text):
            continue
        if _classify(text, "") in grouped and grouped.get(_classify(text, "")):
            continue
        if _contains(text, ["编写目的", "软件名称", "背景领域"]) and grouped.get("1 总则 / 编写目的"):
            continue
        if _contains(text, ["用户角色", "主要用户", "使用者"]) and grouped.get("3 功能需求 / 用户与角色"):
            continue
        if _contains(text, ["核心业务流程", "主线", "流程"]) and grouped.get("3 功能需求 / 核心业务流程"):
            continue
        if _contains(text, ["软件定位", "领域边界", "不做"]) and grouped.get("2 项目概述 / 软件定位"):
            continue
        if _contains(text, ["异常", "补偿", "失败", "缺数据"]) and grouped.get("3 功能需求 / 异常与补偿"):
            continue
        if _contains(text, ["响应", "稳定性", "安全", "部署", "非功能"]) and grouped.get("5 非功能需求 / 性能与可靠性"):
            continue
        if _contains(text, ["验收", "可接受"]) and grouped.get("6 验收准则 / 验收准则"):
            continue
        if text and not _is_stale_gap(text) and text not in gaps:
            gaps.append(text)
    defaults = [
        ("3 功能需求 / 用户与角色", "需确认各类用户角色的权限边界和操作职责。"),
        ("3 功能需求 / 核心业务流程", "需补充核心分析流程的输入、处理、输出和用户交互方式。"),
        ("5 非功能需求 / 性能与可靠性", "需确认响应时间、并发规模、可靠性和安全要求。"),
        ("6 验收准则 / 验收准则", "需确认验收场景、通过条件和测试数据口径。"),
    ]
    for section, question in defaults:
        if not grouped.get(section) and question not in gaps:
            gaps.append(question)
    return gaps[:8]

def _join_facts(facts, limit=6):
    cleaned = []
    for fact in facts:
        value = _clean_fact_text(fact)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:limit]

def _compose_section_content(section, facts):
    facts = _join_facts(facts)
    if not facts:
        return "本章节待确认。"
    if section == "1 总则 / 编写目的":
        return "本文档用于明确本软件的需求范围、核心能力、运行约束和验收口径，为后续设计、开发、测试和交付提供依据。已确认材料包括：" + "；".join(facts) + "。"
    if section == "2 项目概述 / 软件定位":
        return "本软件定位为态势展示、空间分析与阶段性成果汇报支撑工具。当前已确认的定位和边界包括：" + "；".join(facts) + "。后续仍可继续细化具体业务领域、第一阶段范围和不纳入范围。"
    if section == "3 功能需求 / 用户与角色":
        return "系统用户角色按当前已确认信息划分为以下几类：" + "；".join(facts) + "。需求规格后续应继续补齐各角色的权限边界、典型操作、协作关系和结果消费方式。"
    if section == "3 功能需求 / 核心业务流程":
        return "核心业务流程围绕态势工程准备、分析计算和结果输出展开。当前已确认流程信息为：" + "；".join(facts) + "。后续应把每条流程进一步拆成触发条件、输入、处理、输出和异常处理。"
    if section == "3 功能需求 / 功能分解总览":
        return "功能分解总览应覆盖态势管理、地图与图层操作、空间量算分析、结果管理和必要的系统管理能力。当前已确认功能范围包括：" + "；".join(facts) + "。"
    if section == "3 功能需求 / 核心功能项说明":
        return "核心功能项应逐项说明功能目标、输入对象、主要处理、输出结果和限制条件。当前已确认功能包括：" + "；".join(facts) + "。其中具体算法边界、参数默认值和分析结果解释口径仍可在后续继续细化。"
    if section == "3 功能需求 / 结果输出与共享":
        return "结果输出与共享用于支撑分析成果复核、汇报和后续追溯。当前已确认要求包括：" + "；".join(facts) + "。后续需继续明确导出格式、报告模板字段和共享权限。"
    if section == "3 功能需求 / 异常与补偿":
        return "系统应对用户操作、数据加载、计算执行、保存导出和权限校验中的异常提供提示与补偿。当前已确认异常处理要求包括：" + "；".join(facts) + "。"
    if section == "4 数据需求 / 输入数据":
        return "输入数据用于支撑地图展示、态势编辑和空间分析计算。当前已确认输入数据包括：" + "；".join(facts) + "。后续应继续明确数据格式、坐标系、更新方式和质量要求。"
    if section == "4 数据需求 / 输出数据与报表":
        return "输出数据与报表用于保存分析成果、支撑复核和汇报。当前已确认输出内容包括：" + "；".join(facts) + "。后续应继续明确文件格式、报告字段和版本追溯要求。"
    if section == "5 非功能需求 / 性能与可靠性":
        return "性能与可靠性应保证地图浏览、常规分析和结果输出具备可接受的用户体验。当前已确认约束包括：" + "；".join(facts) + "。后续应继续量化响应时间、并发规模和失败恢复口径。"
    if section == "5 非功能需求 / 安全与权限":
        return "安全与权限应支撑账号管理、角色授权、操作审计和结果追溯。当前已确认要求包括：" + "；".join(facts) + "。后续应继续细化权限矩阵、日志留存和导出控制。"
    if section == "5 非功能需求 / 部署与运行环境":
        return "部署与运行环境应满足当前数据安全、网络边界和运行维护要求。当前已确认约束包括：" + "；".join(facts) + "。后续应继续明确部署拓扑、硬件资源和外部依赖。"
    if section == "5 非功能需求 / 精度与质量约束":
        return "精度与质量约束用于说明分析结果的适用边界、数据来源和参数追溯要求。当前已确认约束包括：" + "；".join(facts) + "。后续应继续明确不同分析工具的精度口径和限制条件。"
    if section == "6 验收准则 / 验收准则":
        return "验收准则应围绕完整任务链、角色权限、异常提示、结果输出和追溯能力设计。当前已确认验收口径包括：" + "；".join(facts) + "。后续应继续转化为可执行测试用例和通过标准。"
    return "\n".join(f"- {_ensure_sentence(fact)}" for fact in facts if _ensure_sentence(fact))

def _compose_draft(context, records, write_policy):
    grouped = _group_by_section(records)
    all_record_texts = [_clean_fact_text(record.get("content") or "") for record in records]
    all_record_texts = [item for item in all_record_texts if item]
    all_text = "；".join(all_record_texts)
    if _contains(all_text, ["导出地图", "导出结果", "导出参数", "导出说明", "业务专家复核", "成果导出复核"]):
        result_facts = grouped.setdefault("3 功能需求 / 结果输出与共享", [])
        result_content = "系统应支持导出地图、结果、参数和说明，并提交给业务专家复核。"
        if result_content not in result_facts:
            result_facts.append(result_content)
    if _contains(all_text, ["地图浏览", "流畅", "可接受时间", "响应时间"]):
        performance_facts = grouped.setdefault("5 非功能需求 / 性能与可靠性", [])
        performance_content = "地图浏览应保持流畅，普通分析应在可接受时间内返回。"
        if performance_content not in performance_facts:
            performance_facts.append(performance_content)
    if _contains(all_text, ["验收时至少覆盖", "态势创建编辑", "分析工具使用", "成果导出复核", "结果追溯", "权限日志", "异常提示"]):
        acceptance_facts = grouped.setdefault("6 验收准则 / 验收准则", [])
        acceptance_content = "验收应覆盖态势创建编辑、分析工具使用、成果导出复核、结果追溯、权限日志和异常提示。"
        if acceptance_content not in acceptance_facts:
            acceptance_facts.append(acceptance_content)
    sections = []
    patches = []
    idx = 1
    name = "态势分析系统" if "态势" in all_text else ""
    if "空域" in all_text:
        name = "空域运算软件"
    capabilities = []
    for word in ["态势展示", "GIS分析", "GIS 分析", "通视量算", "坡度分析", "部署影响分析", "部署分析", "空域计算分析", "可用性", "冲突", "容量评估", "报告导出"]:
        if word in all_text and word not in capabilities:
            capabilities.append(word)
    scenario = ""
    if "实时态势展示" in all_text or "事前研判" in all_text:
        scenario = "实时态势展示与事前研判"
    elif "空域" in all_text:
        scenario = "空域规划与计算分析"
    general_has_only_name = grouped.get("1 总则 / 编写目的") and len("；".join(grouped.get("1 总则 / 编写目的") or [])) < 60
    if (not grouped.get("1 总则 / 编写目的") or general_has_only_name) and (name or len(capabilities) >= 2 or scenario):
        subject = name or "本系统"
        capability_text = "、".join(capabilities[:7]) if capabilities else "已确认的核心分析能力"
        scenario_text = f"系统面向{scenario}场景，" if scenario else ""
        grouped["1 总则 / 编写目的"] = [
            f"本文用于明确{subject}的需求范围、核心能力和验收口径，为后续设计、开发、测试和交付提供依据。{scenario_text}覆盖{capability_text}等能力。"
        ]
    retained_gaps = _retained_gaps(context, grouped)
    for section, anchor in SECTION_ANCHORS.items():
        facts = grouped.get(section) or []
        content = _compose_section_content(section, facts)
        sections.append(f"{section}\n{content}")
        patches.append({
            "plan_ref": f"BRAINSTORM-DIFY-DRAFT-{idx:03d}",
            "operation": "replace",
            "content": content,
            "write_policy": write_policy,
            "target_section": section,
            "anchor_path": anchor,
        })
        idx += 1
    if retained_gaps:
        sections.append("待确认事项\n" + "\n".join(f"- {gap}" for gap in retained_gaps))
    return "\n\n".join(sections), patches, retained_gaps

def _has_section(context, section, records=None):
    for record in records or []:
        content = _item_text(record)
        record_section = str(record.get("target_section") or "") if isinstance(record, dict) else ""
        if record_section == section:
            return True
        if section == _classify(content, str(context.get("active_section") or "")):
            return True
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    for source in [state.get("confirmed_facts") or [], state.get("confirmed_decisions") or [], context.get("confirmed_facts") or []]:
        for item in source:
            if isinstance(item, dict) and str(item.get("target_section") or "") == section:
                return True
            if section == _classify(_item_text(item), str(context.get("active_section") or "")):
                return True
    working = context.get("working_document") if isinstance(context.get("working_document"), dict) else {}
    for block in working.get("blocks") or []:
        if isinstance(block, dict) and str(block.get("target_section") or block.get("section") or block.get("heading") or "") == section:
            return True
    return False

def _has_keyword(context, keywords, records=None):
    state = context.get("decision_state") if isinstance(context.get("decision_state"), dict) else {}
    texts = []
    for record in records or []:
        texts.append(_content_text(record))
    for source in [state.get("confirmed_facts") or [], state.get("confirmed_decisions") or [], context.get("confirmed_facts") or []]:
        texts.extend(_content_text(item) for item in source)
    working = context.get("working_document") if isinstance(context.get("working_document"), dict) else {}
    texts.extend(_content_text(block) for block in working.get("blocks") or [])
    joined = "；".join(texts)
    return any(keyword in joined for keyword in keywords)

def _next_gap_plan(context, changed_sections, draft_requested, records=None):
    changed_sections = changed_sections or []
    records = records or []
    normalized = context.get("normalized_context") if isinstance(context.get("normalized_context"), dict) else {}
    last_question = str(normalized.get("last_question") or "")
    def has_section(section):
        return section in changed_sections or _has_section(context, section, records)
    def has_keyword(keywords):
        return _has_keyword(context, keywords, records)
    def count_satisfied_core_sections():
        sections = [
            "2 项目概述 / 软件定位",
            "3 功能需求 / 用户与角色",
            "3 功能需求 / 核心业务流程",
            "3 功能需求 / 核心功能项说明",
            "3 功能需求 / 结果输出与共享",
            "5 非功能需求 / 性能与可靠性",
        ]
        return sum(1 for section in sections if has_section(section))
    def has_conversation_base_for_exception_and_acceptance():
        return (
            has_section("2 项目概述 / 软件定位")
            and has_section("3 功能需求 / 用户与角色")
            and has_section("3 功能需求 / 核心业务流程")
            and has_section("4 数据需求 / 输入数据")
            and (
                has_section("4 数据需求 / 输出数据与报表")
                or has_section("3 功能需求 / 结果输出与共享")
                or has_keyword(["导出", "报告", "输出"])
            )
        )
    def review_or_draft_plan(reason):
        return {
            "assistant_message": "已吸收本轮信息，当前关键信息已较完整，建议先回看闭合项或直接输出草案。",
            "next_question": "当前关键信息已较完整，是否回看闭合项或直接输出草案？",
            "quick_options": [
                {"key": "A", "label": "回看已闭合和未闭合事项", "recommended": True},
                {"key": "B", "label": "输出当前草案", "recommended": False},
                {"key": "C", "label": "补充剩余自定义事项", "recommended": False},
                {"key": "D", "label": "结束追问并进入人工审阅", "recommended": False},
            ],
            "plan_reason": reason,
        }
    def focus_for(question):
        if any(word in question for word in ["用户", "使用者", "角色"]):
            return "roles"
        if any(word in question for word in ["核心流程", "数据接入", "接入模式"]):
            return "core"
        if any(word in question for word in ["边界", "不做", "范围"]):
            return "scope"
        if any(word in question for word in ["协同", "共享", "任务接力", "批注"]):
            return "collab"
        if any(word in question for word in ["导出", "报告", "图件", "消费"]):
            return "export"
        if any(word in question for word in ["性能", "刷新", "精度", "安全", "部署", "并发"]):
            return "quality"
        if any(word in question for word in ["异常", "补偿", "失败", "中断"]):
            return "exception"
        if any(word in question for word in ["验收", "通过标准", "任务链"]):
            return "acceptance"
        if any(word in question for word in ["界面", "页面", "工作区"]):
            return "ui"
        return ""
    last_focus = focus_for(last_question)
    candidates = []
    def add_candidate(focus, condition, plan):
        if condition:
            candidates.append((focus, plan))
    if draft_requested:
        return {
            "assistant_message": "已停止追问，并基于已确认信息生成章节化草案；未闭合内容已保留为待确认事项。",
            "next_question": "请确认是否接受当前草案，或选择继续细化哪个缺口？",
            "quick_options": [
                {"key": "A", "label": "接受草案并进入人工审阅", "recommended": True},
                {"key": "B", "label": "继续细化用户角色与权限", "recommended": False},
                {"key": "C", "label": "继续细化核心业务流程", "recommended": False},
                {"key": "D", "label": "补充非功能与验收准则", "recommended": False},
            ],
            "plan_reason": "用户明确要求停止追问并输出草案，因此进入草案审阅分支。",
        }
    can_review_or_draft = (
        len(records) >= 9
        and count_satisfied_core_sections() >= 4
        and has_section("2 项目概述 / 软件定位")
        and has_section("3 功能需求 / 核心功能项说明")
        and (has_keyword(["导出", "报告"]) or has_keyword(["验收"]))
        and has_section("3 功能需求 / 异常与补偿")
        and has_section("6 验收准则 / 验收准则")
    )
    if can_review_or_draft:
        return review_or_draft_plan("已覆盖用户、流程、边界、协同、非功能或导出信息，避免在长轮次中继续细节追问。")
    add_candidate("positioning", not has_section("2 项目概述 / 软件定位"), {
            "assistant_message": "已吸收本轮信息，下一步补齐软件定位、服务对象和第一阶段边界。",
            "next_question": "这个系统的软件定位、服务对象和第一阶段边界是什么？",
            "quick_options": [
                {"key": "A", "label": "科研分析与业务验证工具", "recommended": True},
                {"key": "B", "label": "基础态势编辑管理平台", "recommended": False},
                {"key": "C", "label": "二者兼具，结果只做辅助判断", "recommended": False},
                {"key": "D", "label": "自定义补充软件定位", "recommended": False},
            ],
            "plan_reason": "软件定位和第一阶段边界尚未形成正文，不能直接进入回看或草案。",
        })
    base_ready_for_tail = has_conversation_base_for_exception_and_acceptance()
    add_candidate("exception", base_ready_for_tail and not has_section("3 功能需求 / 异常与补偿"), {
            "assistant_message": "已吸收本轮信息，下一步确认异常与补偿机制。",
            "next_question": "数据缺失、坐标系不一致、计算失败、保存失败、权限不足或导出失败时如何处理？",
            "quick_options": [
                {"key": "A", "label": "提示原因并允许修正后重算", "recommended": True},
                {"key": "B", "label": "保留已有结果并标注不可用项", "recommended": False},
                {"key": "C", "label": "阻断流程并要求管理员处理", "recommended": False},
                {"key": "D", "label": "自定义补充异常处理", "recommended": False},
            ],
            "plan_reason": "定位、角色、流程和数据链路已具备，下一步应优先补齐异常与补偿，而不是继续追问低优先级章节缺口。",
        })
    add_candidate("acceptance", base_ready_for_tail and has_section("3 功能需求 / 异常与补偿") and not has_section("6 验收准则 / 验收准则"), {
            "assistant_message": "已吸收本轮信息，下一步把能力和异常处理转换为可执行验收链路。",
            "next_question": "验收任务链和通过标准是什么？",
            "quick_options": [
                {"key": "A", "label": "覆盖态势创建、分析、导出和复核", "recommended": True},
                {"key": "B", "label": "覆盖权限、审计和结果追溯", "recommended": False},
                {"key": "C", "label": "覆盖异常提示和失败补偿", "recommended": False},
                {"key": "D", "label": "自定义补充验收链路", "recommended": False},
            ],
            "plan_reason": "异常与补偿已形成正文，收束前应优先明确验收任务链和通过标准。",
        })
    add_candidate("function", not has_section("3 功能需求 / 核心功能项说明"), {
            "assistant_message": "已吸收本轮信息，下一步补齐核心功能清单和能力边界。",
            "next_question": "核心功能清单和各功能的能力边界是什么？",
            "quick_options": [
                {"key": "A", "label": "态势工程、地图浏览、标绘和量算", "recommended": True},
                {"key": "B", "label": "坡度、通视和大气光照辅助运算", "recommended": False},
                {"key": "C", "label": "部署分析与分析结果管理", "recommended": False},
                {"key": "D", "label": "自定义补充核心功能", "recommended": False},
            ],
            "plan_reason": "核心功能项说明尚未形成正文，不能仅凭流程、异常或验收信息进入回看或草案。",
        })
    add_candidate("roles", not has_section("3 功能需求 / 用户与角色"), {
            "assistant_message": "已吸收本轮信息，下一步优先补齐用户角色和消费方。",
            "next_question": "主要用户、下游使用者和主场景分别是什么？",
            "quick_options": [
                {"key": "A", "label": "参谋分析员使用，指挥员查看研判结果", "recommended": True},
                {"key": "B", "label": "值班员维护态势，分析员执行空间分析", "recommended": False},
                {"key": "C", "label": "多角色协同，按权限区分查看和编辑", "recommended": False},
                {"key": "D", "label": "自定义补充用户和场景", "recommended": False},
            ],
            "plan_reason": "用户角色仍是需求规格的基础缺口。",
        })
    add_candidate("core", not has_section("3 功能需求 / 核心业务流程") or not has_keyword(["数据接入", "导入", "流程", "实时接入"]), {
            "assistant_message": "已吸收本轮信息，下一步补齐核心流程和数据接入模式。",
            "next_question": "核心流程和数据接入模式是什么？",
            "quick_options": [
                {"key": "A", "label": "实时态势与告警接入，叠加静态底图数据", "recommended": True},
                {"key": "B", "label": "人工导入数据后执行离线分析", "recommended": False},
                {"key": "C", "label": "实时接入和批量导入混合模式", "recommended": False},
                {"key": "D", "label": "自定义补充数据和流程", "recommended": False},
            ],
            "plan_reason": "核心流程或数据接入仍未充分闭合。",
        })
    add_candidate("scope", not has_section("2 项目概述 / 软件定位"), {
            "assistant_message": "已吸收本轮信息，下一步收束系统边界和不做范围。",
            "next_question": "系统明确不做哪些范围，哪些能力只做辅助分析？",
            "quick_options": [
                {"key": "A", "label": "先确认不做范围和能力边界", "recommended": True},
                {"key": "B", "label": "先补充异常、失败和补偿处理", "recommended": False},
                {"key": "C", "label": "先补充验收场景和通过条件", "recommended": False},
                {"key": "D", "label": "停止追问并输出草案", "recommended": False},
            ],
            "plan_reason": "边界范围尚未闭合，需先避免需求外延失控。",
        })
    add_candidate("collab", not has_section("3 功能需求 / 结果输出与共享") and not has_keyword(["协同", "共享", "任务接力", "批注"]), {
            "assistant_message": "已吸收本轮信息，下一步确认协同与结果共享模式。",
            "next_question": "协同模式、结果共享、任务接力和批注要求是什么？",
            "quick_options": [
                {"key": "A", "label": "支持结果共享、任务接力和批注", "recommended": True},
                {"key": "B", "label": "只共享结果，不支持任务接力", "recommended": False},
                {"key": "C", "label": "先不做协同能力", "recommended": False},
                {"key": "D", "label": "自定义补充协同要求", "recommended": False},
            ],
            "plan_reason": "协同与共享是长轮次测试中需要稳定吸收的正向能力。",
        })
    add_candidate("export", not has_keyword(["导出", "报告", "专题图件"]), {
            "assistant_message": "已吸收本轮信息，下一步确认指挥消费和导出形式。",
            "next_question": "指挥员如何消费结果，系统需要导出哪些报告或图件？",
            "quick_options": [
                {"key": "A", "label": "系统内查看并导出报告和专题图件", "recommended": True},
                {"key": "B", "label": "只在系统内查看，不导出", "recommended": False},
                {"key": "C", "label": "导出专题图件、报告和过程记录", "recommended": False},
                {"key": "D", "label": "自定义补充消费方式", "recommended": False},
            ],
            "plan_reason": "结果消费和导出形式仍需明确。",
        })
    add_candidate("quality", not has_section("5 非功能需求 / 性能与可靠性") or not has_keyword(["秒", "并发", "精度", "安全", "审计"]), {
            "assistant_message": "已吸收本轮信息，下一步补齐性能、精度、安全或部署约束。",
            "next_question": "性能、刷新、精度、安全和部署约束分别是什么？",
            "quick_options": [
                {"key": "A", "label": "补充响应时间和并发验收", "recommended": True},
                {"key": "B", "label": "补充精度和追溯验收", "recommended": False},
                {"key": "C", "label": "补充安全和审计验收", "recommended": False},
                {"key": "D", "label": "输出当前草案", "recommended": False},
            ],
            "plan_reason": "非功能质量约束仍未充分闭合。",
        })
    add_candidate("exception", not base_ready_for_tail and not has_section("3 功能需求 / 异常与补偿"), {
            "assistant_message": "已吸收本轮信息，下一步确认异常与补偿机制。",
            "next_question": "数据缺失、坐标系不一致、计算失败或实时数据中断时如何处理？",
            "quick_options": [
                {"key": "A", "label": "提示原因并允许修正后重算", "recommended": True},
                {"key": "B", "label": "使用最近快照并标注时效", "recommended": False},
                {"key": "C", "label": "阻断流程并要求管理员处理", "recommended": False},
                {"key": "D", "label": "自定义补充异常处理", "recommended": False},
            ],
            "plan_reason": "异常与补偿机制尚未形成正文。",
        })
    add_candidate("acceptance", not base_ready_for_tail and not has_section("6 验收准则 / 验收准则"), {
            "assistant_message": "已吸收本轮信息，下一步把能力转换为可执行验收链路。",
            "next_question": "验收任务链和通过标准是什么？",
            "quick_options": [
                {"key": "A", "label": "导入数据、执行分析、导出报告", "recommended": True},
                {"key": "B", "label": "按角色权限和审计链路验收", "recommended": False},
                {"key": "C", "label": "按性能、精度和异常处理验收", "recommended": False},
                {"key": "D", "label": "自定义补充验收链路", "recommended": False},
            ],
            "plan_reason": "验收准则仍需闭合为可验证任务链。",
        })
    add_candidate("ui", not has_section("3 功能需求 / 功能分解总览"), {
            "assistant_message": "已吸收本轮信息，下一步确认主要界面和交互入口。",
            "next_question": "主要界面包括哪些页面或工作区？",
            "quick_options": [
                {"key": "A", "label": "态势总览、分析工具、图层管理、报告导出", "recommended": True},
                {"key": "B", "label": "任务区、结果对比、系统管理和审计查询", "recommended": False},
                {"key": "C", "label": "先按最小界面集合验收", "recommended": False},
                {"key": "D", "label": "自定义补充界面列表", "recommended": False},
            ],
            "plan_reason": "主要界面列表尚未明确。",
        })
    if candidates:
        for focus, plan in candidates:
            if focus != last_focus:
                return plan
        return candidates[0][1]
    return review_or_draft_plan("核心章节均已有信息，避免继续宽泛追问。")

def main(context_json: str, decision_state_delta_json: str) -> dict:
    context = _loads(context_json, {})
    _decision_output = _loads(decision_state_delta_json, {})
    write_policy = str(context.get("write_policy") or "patch_suggestion_only")
    semantic = str(context.get("semantic") or "")
    source_turn_id = str(context.get("turn_id") or (context.get("turn_context") or {}).get("turn_id") or "turn-0001")
    draft_requested = _draft_requested(context.get("semantic"), context)
    new_records = _extract_records(context)
    existing_records = _existing_fact_records(context)
    working_records = []
    all_records = existing_records + [r for r in working_records if r not in existing_records]
    all_records = all_records + [r for r in new_records if r not in all_records]

    if not draft_requested and not new_records and _review_requested(semantic):
        projection = _status_review(context)
        return {
            "document_projection_json": json.dumps(projection, ensure_ascii=False),
            "filled_document_text": projection["filled_document_text"],
        }

    if draft_requested:
        filled_document_text, document_patch, retained_gaps = _compose_draft(context, all_records, write_policy)
        changed_sections = [patch["target_section"] for patch in document_patch]
        branch = "draft_compose"
    else:
        document_patch = _patches_from_records(new_records, write_policy)
        changed_sections = []
        for patch in document_patch:
            section = patch["target_section"]
            if section not in changed_sections:
                changed_sections.append(section)
        filled_document_text = "\n".join(patch["content"] for patch in document_patch)
        retained_gaps = []
        branch = "document_projection"

    if not document_patch and not draft_requested:
        fallback_question = "请继续补充一个可以写入需求规格说明的事实，例如用户、场景、流程、边界或验收口径。"
        decision_delta = {
            "confirmed_facts": [],
            "confirmed_decisions": [],
            "tentative_assumptions": [],
            "open_questions": [
                _make_item(
                    "DS-Q",
                    1,
                    fallback_question,
                    str(context.get("active_section") or ""),
                    "active",
                    source_turn_id,
                )
            ],
            "rejected_directions": [],
            "chapter_projections": [],
            "next_focus": fallback_question,
        }
        next_plan = {
            "assistant_message": "本轮输入尚不足以稳定写入正文，我先保留为待澄清信息。",
            "next_question": fallback_question,
            "quick_options": [
                {"key": "A", "label": "补充用户和使用场景", "recommended": True},
                {"key": "B", "label": "补充核心功能流程", "recommended": False},
                {"key": "C", "label": "补充边界和不做范围", "recommended": False},
                {"key": "D", "label": "输出已有草案", "recommended": False},
            ],
            "plan_reason": "未提取到可稳定投影的章节事实。",
        }
    else:
        closed = []
        for idx, question in enumerate((context.get("normalized_context") or {}).get("open_question_summaries") or [], 1):
            if new_records and idx <= 6:
                closed.append(_stable_question_id(question, idx))
        confirmed_items = [
            _make_item("DS-F", idx, record["content"], record["target_section"], "active", source_turn_id)
            for idx, record in enumerate(new_records, 1)
        ]
        decision_items = [
            _make_item("DS-D", idx, record["content"], record["target_section"], "active", source_turn_id)
            for idx, record in enumerate([record for record in new_records if _is_decision_record(record)], 1)
        ]
        projection_items = [
            _make_item(
                "DS-P",
                idx,
                f"事实投影到 {record['target_section']}：{record['content']}",
                record["target_section"],
                "active",
                source_turn_id,
            )
            for idx, record in enumerate(new_records, 1)
        ]
        open_items = []
        if draft_requested:
            open_items = [
                _make_item("DS-Q", idx, gap, "待确认事项", "deferred_to_draft_gap", source_turn_id)
                for idx, gap in enumerate(retained_gaps, 1)
            ]
        if _correction_requested(semantic):
            rejected_text = semantic
            rejected_items = [_make_item("DS-R", 1, rejected_text, "", "active", source_turn_id)]
        else:
            rejected_items = []
        next_plan = _next_gap_plan(context, changed_sections, draft_requested, all_records)
        if new_records and not draft_requested:
            sections_for_message = "、".join(changed_sections[:3]) or "结构化状态"
            next_plan["assistant_message"] = f"本轮已吸收{len(new_records)}条信息，主要沉淀到{sections_for_message}。下一步建议继续确认：{next_plan['next_question']}"
        decision_delta = {
            "confirmed_facts": confirmed_items,
            "confirmed_decisions": decision_items,
            "tentative_assumptions": [],
            "open_questions": open_items,
            "closed_question_refs": [],
            "deferred_question_refs": [],
            "superseded_question_refs": [],
            "rejected_directions": rejected_items,
            "chapter_projections": projection_items,
            "next_focus": next_plan["next_question"],
        }

    target_anchor_plan = []
    for idx, patch in enumerate(document_patch, 1):
        target_anchor_plan.append({
            "plan_id": patch["plan_ref"],
            "decision_type": "append_existing_clause",
            "template_clause_id": patch.get("anchor_path") or SECTION_ANCHORS.get(patch.get("target_section"), "REQ-1.1"),
            "canonical_clause_heading": patch.get("target_section") or "",
            "display_heading": patch.get("target_section") or "",
            "anchor_path": patch.get("anchor_path") or SECTION_ANCHORS.get(patch.get("target_section"), "REQ-1.1"),
            "reason": "按事实语义映射到需求规格章节。",
            "confidence": "high",
        })

    projection = {
        "target_anchor_plan": target_anchor_plan,
        "document_patch": document_patch,
        "filled_document_text": filled_document_text,
        "changed_sections": changed_sections,
        "assistant_message": next_plan["assistant_message"],
        "next_question": next_plan["next_question"],
        "quick_options": next_plan["quick_options"],
        "plan_reason": next_plan["plan_reason"],
        "decision_state_delta": decision_delta,
        "confirmed_facts_delta": [item["content"] for item in decision_delta.get("confirmed_facts") or []],
        "open_questions_delta": [item["content"] for item in decision_delta.get("open_questions") or []],
        "question_state_changes": {
            "closed_question_ids": closed if "closed" in locals() else [],
            "deferred_question_ids": [item["item_id"] for item in decision_delta.get("open_questions") or [] if item.get("status") == "deferred_to_draft_gap"],
            "superseded_question_ids": [],
            "removed_stale_question_ids": [
                _stable_question_id(question, idx)
                for idx, question in enumerate((context.get("normalized_context") or {}).get("open_question_summaries") or [], 1)
                if _is_stale_fallback(question)
            ],
            "created_question_ids": [item["item_id"] for item in decision_delta.get("open_questions") or []],
        },
        "draft_requested": draft_requested,
        "branch_taken": branch,
        "intent": "draft_requested" if draft_requested else ("correction" if _correction_requested(semantic) else "fact_supplement"),
        "retained_gaps": retained_gaps,
        "projection_rules_applied": changed_sections,
        "completion_status": "partial",
    }
    return {
        "document_projection_json": json.dumps(projection, ensure_ascii=False),
        "filled_document_text": filled_document_text,
    }
