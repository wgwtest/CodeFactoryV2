from __future__ import annotations

from app.requirement_analysis.input_normalizer import InputNormalizer


class InputRelationClassifier:
    def __init__(self, normalizer: InputNormalizer | None = None) -> None:
        self.normalizer = normalizer or InputNormalizer()

    def classify(
        self,
        previous_interaction: object,
        normalized: dict,
        *,
        last_quick_options: list[dict],
    ) -> dict:
        if normalized.get("input_type") == "quick_option_answer":
            matched_option = str(normalized.get("matched_option") or "").strip().upper()
            previous_option = self.normalizer.find_quick_option(last_quick_options, matched_option)
            if previous_option:
                return {
                    "relation": "selected_option",
                    "reason": f"用户选择了上轮选项 {matched_option}：{previous_option.get('label')}。",
                }
        if not isinstance(previous_interaction, dict) or previous_interaction.get("type") == "none":
            return {"relation": "none", "reason": "本轮之前没有上轮系统留题。"}
        semantic = str(normalized.get("semantic") or "")
        prompt = str(previous_interaction.get("prompt") or "")
        if any(token in semantic for token in ["不是", "先不", "不对", "别", "反对"]):
            return {"relation": "challenge", "reason": "用户输入包含否定或纠正意图，优先按反驳/修正处理。"}
        if any(token in semantic for token in ["先", "按", "确认", "可以", "继续"]):
            return {"relation": "answered", "reason": "用户输入承接了上轮系统留题并给出确认或推进指令。"}
        if "软件定位" in prompt or "定位" in prompt:
            if any(token in semantic for token in ["工具", "平台", "领域", "第一阶段", "系统"]):
                return {"relation": "answered", "reason": "用户输入回答了上轮系统留题中的软件定位信息。"}
        if "用户" in prompt or "角色" in prompt:
            if any(token in semantic for token in ["用户", "专家", "管理员", "角色", "使用"]):
                return {"relation": "answered", "reason": "用户输入回答了上轮系统留题中的用户或角色信息。"}
        return {"relation": "partially_answered", "reason": "用户输入部分承接上轮系统留题，但仍需要结合需求规格继续分析。"}
