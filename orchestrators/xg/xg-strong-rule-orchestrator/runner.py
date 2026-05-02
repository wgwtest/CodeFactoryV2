from __future__ import annotations


def run_turn(context: dict) -> dict:
    session = dict(context.get("session") or {})
    normalized = dict(context.get("normalized") or {})
    active_spec_node = dict(context.get("active_spec_node") or {})
    semantic = str(normalized.get("semantic") or context.get("user_input") or "待补充需求信息")
    target_section = str(active_spec_node.get("target_section") or "未绑定模板章节")
    clause_id = str(active_spec_node.get("node_id") or "").removeprefix("SPEC-")
    fact = _fact_for_clause(clause_id, semantic)
    patch = _patch_for_clause(clause_id, semantic)

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


def _fact_for_clause(clause_id: str, semantic: str) -> str:
    if clause_id == "REQ-1.1":
        return f"编写目的初步确认：{semantic}"
    if clause_id == "REQ-2.1":
        return f"软件定位初步确认：{semantic}"
    if clause_id == "REQ-3.1":
        return f"用户与角色初步确认：{semantic}"
    if clause_id == "REQ-3.2":
        return f"核心业务流程初步确认：{semantic}"
    if clause_id == "REQ-3.3":
        return f"异常与补偿初步确认：{semantic}"
    if clause_id == "REQ-4.1":
        return f"性能与可靠性初步确认：{semantic}"
    if clause_id == "REQ-5.1":
        return f"验收准则初步确认：{semantic}"
    return f"需求规格信息初步确认：{semantic}"


def _patch_for_clause(clause_id: str, semantic: str) -> str:
    if clause_id == "REQ-1.1":
        return f"本文档用于定义{semantic}相关的软件需求边界、功能行为和验收准则。"
    if clause_id == "REQ-2.1":
        return f"软件定位为：{semantic}"
    if clause_id == "REQ-3.1":
        return f"本软件的主要使用对象和职责包括：{semantic}"
    if clause_id == "REQ-3.2":
        return f"核心业务流程为：{semantic}"
    if clause_id == "REQ-3.3":
        return f"异常与补偿要求为：{semantic}"
    if clause_id == "REQ-4.1":
        return f"性能与可靠性要求为：{semantic}"
    if clause_id == "REQ-5.1":
        return f"验收准则为：{semantic}"
    return semantic
