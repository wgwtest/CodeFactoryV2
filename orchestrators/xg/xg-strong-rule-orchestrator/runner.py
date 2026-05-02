from __future__ import annotations

import json
from pathlib import Path


ARTIFACT_RULES = json.loads((Path(__file__).with_name("artifact_rules.json")).read_text(encoding="utf-8"))


def run_turn(context: dict) -> dict:
    session = dict(context.get("session") or {})
    normalized = dict(context.get("normalized") or {})
    active_spec_node = dict(context.get("active_spec_node") or {})
    semantic = str(normalized.get("semantic") or context.get("user_input") or "待补充需求信息")
    target_section = str(active_spec_node.get("target_section") or "未绑定模板章节")
    clause_id = str(active_spec_node.get("node_id") or "").removeprefix("SPEC-")
    fact = _render_rule_template(clause_id, semantic, template_key="fact_template")
    patch = _render_rule_template(clause_id, semantic, template_key="patch_template")

    return {
        "organizer_interpretation": {
            "summary": f"强规则组织器将用户输入投影到 {target_section}，并按固定审计顺序处理。",
            "intent": "supplement_requirement",
            "confidence": "high",
        },
        "assistant_message": f"强规则组织器已按固定闭环更新：{target_section}。",
        "next_suggestion": {
            "kind": "topic",
            "content": "",
            "reason": "",
            "related_spec_node_ids": [],
        },
        "next_question": str(active_spec_node.get("question") or "请继续补充需求规格说明。"),
        "quick_options": [],
        "confirmed_facts_delta": [fact],
        "open_questions_delta": [str(active_spec_node.get("question") or "请继续补充需求规格说明。")],
        "document_patch": [
            {
                "section": target_section,
                "operation": "append_or_update",
                "content": patch,
                "write_policy": str(session.get("write_policy") or "patch_suggestion_only"),
            }
        ],
        "annotations": [
            "该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。",
            "强规则组织器按固定状态机执行：输入关系 -> 规格补充 -> 回看 -> 闭环 -> 下一轮设计。",
        ],
        "risks": [],
        "confidence": "medium",
        "raw_model_response": {
            "provider_id": str(session.get("provider_id") or "mock"),
            "model": str(session.get("model") or "mock-requirement-analysis-v1"),
            "mock": True,
        },
    }


def _render_rule_template(clause_id: str, semantic: str, *, template_key: str) -> str:
    clauses = ARTIFACT_RULES.get("clauses") if isinstance(ARTIFACT_RULES.get("clauses"), dict) else {}
    defaults = ARTIFACT_RULES.get("defaults") if isinstance(ARTIFACT_RULES.get("defaults"), dict) else {}
    rule = clauses.get(clause_id) if isinstance(clauses, dict) else None
    template = str((rule or defaults or {}).get(template_key) or "{semantic}")
    return template.replace("{semantic}", semantic)
