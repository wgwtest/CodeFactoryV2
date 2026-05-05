from __future__ import annotations


class InputNormalizer:
    def normalize_input(self, user_input: str, *, quick_options: list[dict] | None = None) -> dict:
        stripped = user_input.strip()
        option = stripped[:1].upper() if stripped else ""
        if option in {"A", "B", "C"}:
            option_text = stripped[1:].lstrip("，,、.。:： ").strip()
            matched_quick_option = self.find_quick_option(quick_options or [], option)
            return {
                "input_type": "quick_option_answer",
                "matched_option": option,
                "matched_option_label": matched_quick_option.get("label") if matched_quick_option else None,
                "semantic": option_text or str(matched_quick_option.get("label") if matched_quick_option else "") or option,
            }
        if stripped in {"继续", "可以", "下一步"}:
            return {
                "input_type": "short_command",
                "matched_option": None,
                "matched_option_label": None,
                "semantic": "用户要求继续推进。",
            }
        return {"input_type": "free_text", "matched_option": None, "matched_option_label": None, "semantic": stripped}

    def normalize_quick_options(self, value: object) -> list[dict]:
        if not isinstance(value, list):
            return []
        normalized: list[dict] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip().upper()
            label = str(item.get("label") or "").strip()
            if key and label:
                normalized.append({**item, "key": key, "label": label})
        return normalized

    def find_quick_option(self, options: list[dict], key: str) -> dict | None:
        normalized_key = key.strip().upper()
        for option in options:
            if str(option.get("key") or "").strip().upper() == normalized_key:
                return option
        return None
