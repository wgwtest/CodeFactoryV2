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
    display_heading = _display_heading(context, clause_id, target_section)
    fact = _render_rule_template(clause_id, semantic, template_key="fact_template")
    patch = _render_rule_template(clause_id, semantic, template_key="patch_template")
    template_shape_assessment = {
        "shape_type": "coarse_grained_extensible",
        "reason": "强规则组织器只生成协议结构，业务章节判断由输入上下文中的活动锚点提供。",
        "allowed_write_modes": ["append_existing_clause", "revise_existing_anchor", "create_subtopic_under_clause"],
        "forbidden_write_modes": ["invent_new_template_clause", "invent_new_section_number"],
        "template_revision_recommendations": [],
    }
    target_anchor_plan = [
        {
            "plan_id": "AP-001",
            "decision_type": "append_existing_clause",
            "template_clause_id": clause_id or "REQ-1.1",
            "canonical_clause_heading": display_heading,
            "subtopic_action": "none",
            "subtopic_key": "",
            "subtopic_title": "",
            "display_heading": display_heading,
            "template_shape_ref": "coarse_grained_extensible",
            "reason": "强规则组织器使用当前活动规格节点作为目标锚点。",
            "confidence": "medium",
            "anchor_path": clause_id or "REQ-1.1",
        }
    ]

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
        "template_shape_assessment": template_shape_assessment,
        "target_anchor_plan": target_anchor_plan,
        "confirmed_facts_delta": [fact],
        "open_questions_delta": [str(active_spec_node.get("question") or "请继续补充需求规格说明。")],
        "document_patch": [
            {
                "plan_ref": "AP-001",
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


def _display_heading(context: dict, clause_id: str, fallback: str) -> str:
    chapter_context = dict(context.get("chapter_configuration_context") or {})
    canonical_clause_map = dict(chapter_context.get("canonical_clause_map") or {})
    clause = dict(canonical_clause_map.get(clause_id) or {})
    return str(clause.get("display_heading") or clause.get("heading") or fallback)
