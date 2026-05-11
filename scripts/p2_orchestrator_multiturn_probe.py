#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


DEFAULT_TURNS = [
    "我希望创建一个态势分析系统。这个态势分析系统里面要有态势的展示，要有一些一系列的这种态势分析工具。你比如说地理信息的分析工具、同时量算、坡度，还有一些这个部署的这个分析系统。啊，这个，但是当前的用户啊、使用模式啊，我都没有想清楚，希望你来一块帮我想清楚",
    "主用户参谋分析员，下游查看者指挥员。",
    "主场景实时态势辅助研判，兼顾任务前区域研判，给出典型流程。",
    "数据接入混合模式：实时态势/告警/位置更新 + 导入底图/DEM/任务区域/禁限区/部署点位/标注。",
    "部署分析边界：覆盖、冲突、影响范围、可行性辅助判断，不做最优推荐。",
    "中等协同：结果共享、任务接力、批注、报告传递，不做强实时共编。",
    "指挥员消费：系统内指挥视图、态势摘要、风险清单、导出专题图件/报告。",
    "准实时刷新：普通态势 10-30 秒，关键告警尽快推送，复杂分析人工触发。",
    "角色权限：管理员、数据管理员、参谋分析员、指挥员、情报分析员、值班操作员。",
    "非功能：地图查询 2 秒，分析 10 秒到 3 分钟，30 并发，权限分级、审计、内网/专网。",
    "精度：辅助研判级，不承诺测绘工程级；结果标注数据来源、时间、算法参数。",
    "导出：专题图件、结果表、简化研判报告、任务记录；报告模板先固定。",
    "不做范围：自动指挥决策、火力分配、大规模仿真、自动最优部署、强实时共编。",
    "异常补偿：数据缺失降级分析；坐标系不一致提示转换；实时中断显示最后时间；DEM 缺块标识影响；参数不合法提示。",
    "验收任务链：任务前区域研判、任务中态势变化、部署冲突检查、专题图导出、报告生成、历史记录追溯。",
    "主要界面：态势总览图、任务管理、图层数据管理、分析工具箱、结果面板、部署分析面板、报告导出、系统配置、审计日志。",
    "安全：认证、角色权限、操作审计、数据分级、内网部署、日志留存、导出水印/密级。",
    "回看：哪些关键决策已闭合，哪些未闭合，不要急着写全文。",
    "补充未闭合：GIS 数据接入优先文件导入和接口接入；报告模板第一阶段固定；算法参数管理员配置默认值，分析员任务内调整。",
    "强制停止追问，基于当前所有信息输出完整需求规格说明草案，并列出仍需后续确认事项。",
]

DYNAMIC_INITIAL_INPUT = (
    "我希望创建一个态势分析系统。这个态势分析系统里面要有态势的展示，要有一系列态势分析工具，"
    "比如地理信息分析工具、通视量算、坡度分析，还有部署分析系统。"
    "但是当前用户、使用模式我都没有想清楚，希望你来一块帮我想清楚。"
)

DYNAMIC_EXAMINER_FACTS = [
    {
        "domain": "user_roles",
        "triggers": ["用户", "角色", "谁用", "使用者", "人员", "权限", "专家"],
        "action": "answer_question",
        "text": "这个我还没完全想清楚，但目前倾向于主要用户是科研分析人员；业务专家参与结果复核，数据管理员维护基础数据，系统管理员负责账号、权限、日志和系统配置。",
    },
    {
        "domain": "software_positioning",
        "triggers": ["定位", "目标", "价值", "解决", "建设", "目的", "范围", "领域", "应用", "名称"],
        "action": "answer_question",
        "text": "它既像地理分析计算器，也像基础态势编辑管理平台，主要支撑日常地理信息分析、典型业务场景验证、基础数据分析和成果汇报。",
    },
    {
        "domain": "workflow",
        "triggers": ["流程", "怎么用", "场景", "步骤", "业务过程", "使用模式"],
        "action": "answer_question",
        "text": "可以先按三个主流程考虑：创建工程、加载图层、添加对象和保存工程；选择分析工具、输入对象或参数、执行计算并查看结果；最后导出地图、结果、参数和说明给业务专家复核。",
    },
    {
        "domain": "core_functions",
        "triggers": ["功能", "工具", "能力", "模块", "态势", "展示", "编辑"],
        "action": "answer_question",
        "text": "核心功能先考虑态势工程管理、地图浏览、图层控制、点线面和文字标绘、距离面积坐标量算、坡度坡向高程剖面、通视分析、大气光照辅助运算和分析结果管理。",
    },
    {
        "domain": "data_interfaces",
        "triggers": ["数据", "接口", "导入", "导出", "图层", "底图", "DEM", "矢量", "栅格"],
        "action": "answer_question",
        "text": "输入数据包括底图、地形数据、矢量数据、栅格数据、业务对象数据和分析参数；输出包括态势工程文件、地图图片、分析结果图层、结果参数表和简要报告片段。第一阶段以文件导入导出和内网数据加载为主，不做实时数据总线。",
    },
    {
        "domain": "scope_boundary",
        "triggers": ["边界", "不做", "排除", "限制", "范围", "协同", "决策"],
        "action": "answer_question",
        "text": "第一阶段不做实时多源情报接入，不做自动决策推荐，不承诺高精度测绘级或工程级计算，也不做多单位在线协同指挥。分析结果只能作为辅助判断。",
    },
    {
        "domain": "quality_constraints",
        "triggers": ["非功能", "性能", "安全", "可靠", "部署", "精度", "质量"],
        "action": "answer_question",
        "text": "非功能先按内网部署、角色权限、操作审计、结果可追溯考虑；地图浏览要比较流畅，普通分析应在可接受时间内返回，所有分析结果都要标注数据来源、参数和适用限制。",
    },
    {
        "domain": "exceptions_acceptance",
        "triggers": ["异常", "补偿", "验收", "测试", "失败", "错误", "准则"],
        "action": "answer_question",
        "text": "异常方面要处理数据缺失、坐标系不一致、计算失败、保存失败、权限不足和导出失败。验收时至少覆盖态势创建编辑、分析工具使用、成果导出复核、结果追溯、权限日志和异常提示。",
    },
]

DYNAMIC_CORRECTIONS = [
    {
        "triggers": ["自动决策", "自动推荐", "指挥决策", "正式指挥", "处置"],
        "action": "light_correction",
        "text": "这里你理解得有点重了，第一阶段只做科研分析和业务验证中的辅助分析，不做自动决策推荐，也不把结果表述为正式指挥结论。",
    },
    {
        "triggers": ["通用模板", "模板"],
        "action": "light_correction",
        "text": "这里要区分模板和当前项目事实。态势展示、空间分析、通视这些是态势分析系统样例项目的业务功能，不是通用需求规格模板本身。",
    },
]

DYNAMIC_REVIEW_INPUT = "你先回看一下：目前哪些关键决策已经闭合，哪些还没有闭合？先不要急着完整定稿。"
DYNAMIC_CONVERGENCE_INPUT = "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。"


def post_json(base_url: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.post(f"{base_url.rstrip('/')}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def post_json_with_retry(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout: float,
    *,
    retries: int = 1,
    retry_delay_seconds: float = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return post_json(base_url, path, payload, timeout)
        except Exception as exc:  # noqa: BLE001 - probe runner preserves transient service failures.
            last_error = exc
            if attempt >= retries:
                break
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in {502, 503, 504}:
                break
            time.sleep(retry_delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError("post_json_with_retry failed without captured exception")


def get_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.get(f"{base_url.rstrip('/')}{path}")
        response.raise_for_status()
        return response.json()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def jsonl_append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def http_error_payload(exc: httpx.HTTPStatusError) -> dict[str, Any]:
    return {
        "http_status": exc.response.status_code,
        "http_reason": exc.response.reason_phrase,
        "response_body": exc.response.text,
    }


def count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def short_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").replace("\r\n", "\n").strip()
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def working_document_block_count(working_document: dict[str, Any]) -> int:
    for key in ("blocks", "revision_fragments", "sections"):
        value = working_document.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def working_document_text_chars(working_document: dict[str, Any]) -> int:
    blocks = working_document.get("blocks")
    if not isinstance(blocks, list):
        return 0
    return sum(len(str(block.get("text") or "")) for block in blocks if isinstance(block, dict))


def normalize_text_for_match(value: Any) -> str:
    return str(value or "").lower()


def latest_assistant_message(session: dict[str, Any]) -> str:
    messages = list(session.get("messages") or [])
    assistant_messages = [dict(item) for item in messages if dict(item).get("role") == "assistant"]
    return str(assistant_messages[-1].get("content") or "") if assistant_messages else ""


def should_stop_dynamic_probe_after_turn(session: dict[str, Any]) -> bool:
    next_interaction = dict(session.get("next_interaction") or {})
    interaction_type = str(next_interaction.get("type") or "").strip()
    return interaction_type in {"deliverable", "draft_delivery", "draft_with_gaps"}


def option_prefix(options: list[Any], *, fact_text: str) -> str:
    if not options:
        return ""
    normalized_fact = normalize_text_for_match(fact_text)
    for option in options:
        item = dict(option) if isinstance(option, dict) else {}
        label = str(item.get("label") or "").strip()
        key = str(item.get("key") or "A").strip() or "A"
        if label and label.lower() in normalized_fact:
            return f"{key}，我倾向于{label}。"
    return "不完全是这些选项。"


def choose_dynamic_examiner_input(
    *,
    turn_index: int,
    max_turns: int,
    last_session: dict[str, Any] | None,
    used_domains: set[str],
    recent_questions: list[str],
) -> dict[str, str]:
    if turn_index == 1 or not last_session:
        return {
            "user_input": DYNAMIC_INITIAL_INPUT,
            "examiner_action": "initial_intent",
            "examiner_reason": "首轮只输入基准起始描述。",
            "released_domain": "initial_intent",
        }
    if turn_index == max_turns:
        return {
            "user_input": DYNAMIC_CONVERGENCE_INPUT,
            "examiner_action": "convergence_request",
            "examiner_reason": "达到动态测试轮次上限，要求停止追问并输出带待确认事项的草案。",
            "released_domain": "convergence",
        }

    next_interaction = dict(last_session.get("next_interaction") or {})
    question = str(next_interaction.get("prompt") or latest_assistant_message(last_session))
    question_text = normalize_text_for_match(question)
    options = list(next_interaction.get("options") or [])

    if "scope_boundary" not in used_domains and any(
        trigger in question_text
        for trigger in [
            "不做哪些范围",
            "能力只做辅助分析",
            "第一阶段",
            "全部纳入第一阶段",
            "后续阶段再引入",
            "不纳入范围",
        ]
    ):
        fact = next(item for item in DYNAMIC_EXAMINER_FACTS if item["domain"] == "scope_boundary")
        prefix = option_prefix(options, fact_text=str(fact["text"]))
        user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
        return {
            "user_input": user_input,
            "examiner_action": "option_answer_with_supplement" if prefix else fact["action"],
            "examiner_reason": "组织器询问第一阶段范围、排除范围或辅助分析边界，优先释放 scope_boundary 事实。",
            "released_domain": "scope_boundary",
        }

    for fact in DYNAMIC_EXAMINER_FACTS:
        if fact["domain"] in used_domains:
            continue
        if any(trigger.lower() in question_text for trigger in fact["triggers"]):
            prefix = option_prefix(options, fact_text=str(fact["text"]))
            user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
            return {
                "user_input": user_input,
                "examiner_action": "option_answer_with_supplement" if prefix else fact["action"],
                "examiner_reason": f"按组织器当前问题释放 {fact['domain']} 主题事实。",
                "released_domain": fact["domain"],
            }

    for correction in DYNAMIC_CORRECTIONS:
        if any(trigger.lower() in question_text for trigger in correction["triggers"]):
            return {
                "user_input": correction["text"],
                "examiner_action": correction["action"],
                "examiner_reason": f"组织器输出触发纠偏关键词：{', '.join(correction['triggers'])}",
                "released_domain": "correction",
            }

    if len(recent_questions) >= 2 and len({item.strip() for item in recent_questions[-2:] if item.strip()}) == 1:
        for fact in DYNAMIC_EXAMINER_FACTS:
            if fact["domain"] not in used_domains:
                return {
                    "user_input": fact["text"],
                    "examiner_action": "small_guidance",
                    "examiner_reason": "组织器连续重复追问，按手册释放一个具体主题例子观察其归纳能力。",
                    "released_domain": fact["domain"],
                }

    if "review" in used_domains:
        return {
            "user_input": DYNAMIC_CONVERGENCE_INPUT,
            "examiner_action": "convergence_request",
            "examiner_reason": "已执行过回看请求，避免重复回看污染测试，转入收束交付验证。",
            "released_domain": "convergence",
        }

    if turn_index >= max_turns - 2:
        return {
            "user_input": DYNAMIC_REVIEW_INPUT,
            "examiner_action": "review_request",
            "examiner_reason": "接近轮次上限，要求先回看闭合与未闭合事项。",
            "released_domain": "review",
        }

    for fact in DYNAMIC_EXAMINER_FACTS:
        if fact["domain"] not in used_domains:
            prefix = option_prefix(options, fact_text=str(fact["text"]))
            user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
            return {
                "user_input": user_input,
                "examiner_action": "small_supplement",
                "examiner_reason": f"当前问题未命中特定主题，按信息释放限额补充 {fact['domain']}。",
                "released_domain": fact["domain"],
            }

    return {
        "user_input": DYNAMIC_REVIEW_INPUT,
        "examiner_action": "review_request",
        "examiner_reason": "事实池已释放完毕，要求组织器回看当前闭合状态。",
        "released_domain": "review",
    }


def extract_turn_metrics(
    *,
    orchestrator_id: str,
    turn_index: int,
    elapsed_seconds: float,
    user_input: str,
    response_payload: dict[str, Any],
    previous_provider_log_count: int,
    examiner_action: str = "",
    examiner_reason: str = "",
    released_domain: str = "",
) -> dict[str, Any]:
    session = dict(response_payload.get("session") or {})
    turn = dict(response_payload.get("turn") or {})
    decision_state = dict(session.get("decision_state") or {})
    working_document = dict(session.get("working_document") or {})
    messages = list(session.get("messages") or [])
    provider_logs = list(session.get("provider_logs") or [])
    spec_execution = dict(turn.get("spec_execution") or {})
    next_interaction = dict(turn.get("next_interaction") or {})
    post_update_review = dict(turn.get("post_update_review") or {})
    review_result = dict(turn.get("review_after_apply_result") or {})
    stage_audits = list(turn.get("stage_audits") or [])
    document_patch = list(spec_execution.get("document_patch") or session.get("document_patch") or [])
    assistant_message = spec_execution.get("assistant_message")
    if not assistant_message and messages:
        assistant_messages = [item for item in messages if dict(item).get("role") == "assistant"]
        assistant_message = dict(assistant_messages[-1]).get("content") if assistant_messages else ""

    return {
        "orchestrator_id": orchestrator_id,
        "turn_index": turn_index,
        "turn_id": turn.get("turn_id"),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": "ok",
        "user_input": short_text(user_input, 500),
        "examiner_action": examiner_action,
        "examiner_reason": short_text(examiner_reason, 500),
        "released_domain": released_domain,
        "assistant_message": short_text(assistant_message, 1200),
        "assistant_message_chars": len(str(assistant_message or "")),
        "next_question": short_text(next_interaction.get("prompt"), 800),
        "quick_options_count": count_list(next_interaction.get("options")),
        "confirmed_facts_count": count_list(session.get("confirmed_facts")),
        "session_open_questions_count": count_list(session.get("open_questions")),
        "decision_state_confirmed_facts_count": count_list(decision_state.get("confirmed_facts")),
        "decision_state_confirmed_decisions_count": count_list(decision_state.get("confirmed_decisions")),
        "decision_state_tentative_assumptions_count": count_list(decision_state.get("tentative_assumptions")),
        "decision_state_open_questions_count": count_list(decision_state.get("open_questions")),
        "decision_state_rejected_directions_count": count_list(decision_state.get("rejected_directions")),
        "decision_state_chapter_projections_count": count_list(decision_state.get("chapter_projections")),
        "document_patch_count": len(document_patch),
        "document_patch_chars": sum(len(str(item.get("content") or "")) for item in document_patch if isinstance(item, dict)),
        "working_document_block_count": working_document_block_count(working_document),
        "working_document_text_chars": working_document_text_chars(working_document),
        "provider_log_count_total": len(provider_logs),
        "provider_log_count_delta": max(0, len(provider_logs) - previous_provider_log_count),
        "stage_audit_count": len(stage_audits),
        "stage_audits": [
            {
                "stage_id": dict(item).get("stage_id"),
                "stage_kind": dict(item).get("stage_kind"),
                "validation_status": dict(item).get("validation_status"),
                "adopted_fields": dict(item).get("adopted_fields"),
            }
            for item in stage_audits
        ],
        "post_update_review": post_update_review,
        "review_after_apply_result": review_result,
        "closure_decision": dict(turn.get("closure_decision") or {}),
        "session_phase": session.get("session_phase"),
    }


def run_orchestrator(
    *,
    base_url: str,
    orchestrator_id: str,
    provider_id: str,
    model: str,
    template_id: str,
    topic: str,
    mode: str,
    max_turns: int,
    timeout: float,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl = output_dir / f"{orchestrator_id}.turns.raw.jsonl"
    metrics_jsonl = output_dir / f"{orchestrator_id}.turns.metrics.jsonl"
    summary_path = output_dir / f"{orchestrator_id}.summary.json"
    final_session_path = output_dir / f"{orchestrator_id}.final-session.json"

    session_payload = {
        "topic": topic,
        "orchestrator_id": orchestrator_id,
        "provider_id": provider_id,
        "model": model,
        "template_id": template_id,
        "knowledge_package_id": "airspace-domain-demo",
        "write_policy": "patch_suggestion_only",
    }
    started_at = datetime.now().isoformat(timespec="seconds")
    try:
        session_response = post_json_with_retry(
            base_url,
            "/api/requirement-analysis/sessions",
            session_payload,
            timeout,
            retries=1,
        )
    except Exception as exc:  # noqa: BLE001 - setup failure is still a test result.
        setup_error = {
            "orchestrator_id": orchestrator_id,
            "phase": "create_session",
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if isinstance(exc, httpx.HTTPStatusError):
            setup_error.update(http_error_payload(exc))
        json_dump(output_dir / f"{orchestrator_id}.session-create-error.json", setup_error)
        summary = {
            "orchestrator_id": orchestrator_id,
            "session_id": None,
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "requested_turns": max_turns,
            "completed_turns": 0,
            "error_count": 1,
            "turn_success_rate": 0,
            "last_error": setup_error,
        }
        json_dump(summary_path, summary)
        return summary
    session_id = str(session_response["session_id"])
    json_dump(output_dir / f"{orchestrator_id}.session-created.json", session_response)

    metrics: list[dict[str, Any]] = []
    previous_provider_log_count = count_list(session_response.get("provider_logs"))
    last_session: dict[str, Any] | None = dict(session_response)
    used_domains: set[str] = set()
    recent_questions: list[str] = []
    for turn_index in range(1, max_turns + 1):
        if mode == "fixed":
            if turn_index > len(DEFAULT_TURNS):
                break
            examiner_decision = {
                "user_input": DEFAULT_TURNS[turn_index - 1],
                "examiner_action": "fixed_regression_input",
                "examiner_reason": "历史 20 回合固定回归链路。",
                "released_domain": f"fixed-{turn_index:02d}",
            }
        else:
            examiner_decision = choose_dynamic_examiner_input(
                turn_index=turn_index,
                max_turns=max_turns,
                last_session=last_session,
                used_domains=used_domains,
                recent_questions=recent_questions,
            )
        user_input = examiner_decision["user_input"]
        turn_started = time.monotonic()
        try:
            response_payload = post_json(
                base_url,
                f"/api/requirement-analysis/sessions/{session_id}/turns",
                {"user_input": user_input},
                timeout,
            )
            elapsed = time.monotonic() - turn_started
            jsonl_append(
                raw_jsonl,
                {
                    "turn_index": turn_index,
                    "elapsed_seconds": round(elapsed, 3),
                    "examiner_decision": examiner_decision,
                    "payload": response_payload,
                },
            )
            item = extract_turn_metrics(
                orchestrator_id=orchestrator_id,
                turn_index=turn_index,
                elapsed_seconds=elapsed,
                user_input=user_input,
                response_payload=response_payload,
                previous_provider_log_count=previous_provider_log_count,
                examiner_action=examiner_decision.get("examiner_action", ""),
                examiner_reason=examiner_decision.get("examiner_reason", ""),
                released_domain=examiner_decision.get("released_domain", ""),
            )
            previous_provider_log_count = int(item["provider_log_count_total"])
            metrics.append(item)
            jsonl_append(metrics_jsonl, item)
            last_session = dict(response_payload.get("session") or {})
            released_domain = str(examiner_decision.get("released_domain") or "")
            if released_domain and not released_domain.startswith("fixed-") and released_domain not in {"convergence", "correction", "initial_intent"}:
                used_domains.add(released_domain)
            if item.get("next_question"):
                recent_questions.append(str(item.get("next_question") or ""))
                recent_questions = recent_questions[-3:]
            print(
                f"{orchestrator_id} turn {turn_index:02d}: ok "
                f"{elapsed:.1f}s assistant={item['assistant_message_chars']} "
                f"patch={item['document_patch_count']} provider_delta={item['provider_log_count_delta']} "
                f"examiner={item['examiner_action']}",
                flush=True,
            )
            if mode == "dynamic" and should_stop_dynamic_probe_after_turn(last_session):
                print(
                    f"{orchestrator_id} turn {turn_index:02d}: stop after {dict(last_session.get('next_interaction') or {}).get('type')}",
                    flush=True,
                )
                break
        except Exception as exc:  # noqa: BLE001 - test runner must preserve exact failure.
            elapsed = time.monotonic() - turn_started
            error_payload = {
                "orchestrator_id": orchestrator_id,
                "turn_index": turn_index,
                "elapsed_seconds": round(elapsed, 3),
                "status": "error",
                "user_input": short_text(user_input, 500),
                "examiner_action": examiner_decision.get("examiner_action", ""),
                "examiner_reason": short_text(examiner_decision.get("examiner_reason", ""), 500),
                "released_domain": examiner_decision.get("released_domain", ""),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            if isinstance(exc, httpx.HTTPStatusError):
                error_payload.update(http_error_payload(exc))
            metrics.append(error_payload)
            jsonl_append(metrics_jsonl, error_payload)
            print(f"{orchestrator_id} turn {turn_index:02d}: error {type(exc).__name__}: {exc}", flush=True)
            break

    try:
        if session_id:
            last_session = get_json(base_url, f"/api/requirement-analysis/sessions/{session_id}", timeout)
            json_dump(final_session_path, last_session)
    except Exception as exc:  # noqa: BLE001
        json_dump(output_dir / f"{orchestrator_id}.final-session-error.json", {"error": str(exc), "error_type": type(exc).__name__})

    ok_count = len([item for item in metrics if item.get("status") == "ok"])
    error_count = len(metrics) - ok_count
    final_decision_state = dict((last_session or {}).get("decision_state") or {})
    final_working_document = dict((last_session or {}).get("working_document") or {})
    summary = {
        "orchestrator_id": orchestrator_id,
        "session_id": session_id,
        "mode": mode,
        "started_at": started_at,
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "requested_turns": max_turns,
        "completed_turns": ok_count,
        "error_count": error_count,
        "turn_success_rate": round(ok_count / max_turns, 4) if max_turns else 0,
        "assistant_message_chars_total": sum(int(item.get("assistant_message_chars") or 0) for item in metrics),
        "document_patch_chars_total": sum(int(item.get("document_patch_chars") or 0) for item in metrics),
        "final_provider_log_count": count_list((last_session or {}).get("provider_logs")),
        "examiner_action_distribution": {
            action: len([item for item in metrics if item.get("examiner_action") == action])
            for action in sorted({str(item.get("examiner_action") or "") for item in metrics if item.get("examiner_action")})
        },
        "released_domains": [
            domain
            for domain in sorted({str(item.get("released_domain") or "") for item in metrics if item.get("released_domain")})
        ],
        "final_working_document_block_count": working_document_block_count(final_working_document),
        "final_working_document_text_chars": working_document_text_chars(final_working_document),
        "final_decision_state_counts": {
            "confirmed_facts": count_list(final_decision_state.get("confirmed_facts")),
            "confirmed_decisions": count_list(final_decision_state.get("confirmed_decisions")),
            "tentative_assumptions": count_list(final_decision_state.get("tentative_assumptions")),
            "open_questions": count_list(final_decision_state.get("open_questions")),
            "rejected_directions": count_list(final_decision_state.get("rejected_directions")),
            "chapter_projections": count_list(final_decision_state.get("chapter_projections")),
        },
        "last_next_question": metrics[-1].get("next_question") if metrics else "",
        "last_error": metrics[-1] if metrics and metrics[-1].get("status") == "error" else None,
    }
    json_dump(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P2 requirement-analysis orchestrator multi-turn probes.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--orchestrator", action="append", required=True, help="Orchestrator id. Repeatable.")
    parser.add_argument("--provider", default="deepseek", help="P2 provider id.")
    parser.add_argument("--model", default="provider-default", help="P2 model id.")
    parser.add_argument(
        "--template-id",
        default="xg-template-81433-默认运算软件需求规格说明模板实例-v1-0",
        help="Requirement template instance id.",
    )
    parser.add_argument("--topic", default="态势分析系统需求规格探索", help="Session topic.")
    parser.add_argument(
        "--mode",
        choices=["dynamic", "fixed"],
        default="dynamic",
        help="dynamic uses the controlled examiner strategy; fixed uses the historical 20-turn regression chain.",
    )
    parser.add_argument("--max-turns", type=int, default=20, help="Maximum turns to submit.")
    parser.add_argument("--timeout", type=float, default=180, help="Per-request timeout seconds.")
    parser.add_argument("--output-dir", default=".run-logs/p2-orchestrator-iteration", help="Output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for orchestrator_id in args.orchestrator:
        summary = run_orchestrator(
            base_url=args.base_url,
            orchestrator_id=orchestrator_id,
            provider_id=args.provider,
            model=args.model,
            template_id=args.template_id,
            topic=args.topic,
            mode=args.mode,
            max_turns=args.max_turns,
            timeout=args.timeout,
            output_dir=output_root,
        )
        summaries.append(summary)
    json_dump(output_root / "summary.json", summaries)
    print(json.dumps(summaries, ensure_ascii=False, indent=2), flush=True)
    return 1 if any(item.get("error_count") for item in summaries) else 0


if __name__ == "__main__":
    sys.exit(main())
