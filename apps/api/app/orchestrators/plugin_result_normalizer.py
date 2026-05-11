from __future__ import annotations

from app.orchestrators.plugin_contracts import OrchestratorRunResult


class OrchestratorPluginResultNormalizer:
    def normalize(self, result: OrchestratorRunResult) -> dict:
        final_output = dict(result.final_output or {})
        interaction_output = dict(result.interaction_output or {})
        process_output = dict(result.process_output or {})
        raw_output = dict(result.raw_output or {})

        model_output = {
            "assistant_message": str(interaction_output.get("assistant_message") or ""),
            "next_question": str(interaction_output.get("next_question") or ""),
            "quick_options": self._normalize_quick_options(interaction_output.get("quick_options")),
            "next_suggestion": dict(interaction_output.get("suggested_focus") or {}),
            "interaction_mode": str(dict(interaction_output.get("suggested_focus") or {}).get("interaction_mode") or ""),
            "should_ask_user": dict(interaction_output.get("suggested_focus") or {}).get("should_ask_user"),
            "document_patch": list(final_output.get("document_patch") or []),
            "filled_document_text": str(final_output.get("filled_document_text") or ""),
            "confidence": str(final_output.get("confidence") or "medium"),
            "confirmed_facts_delta": list((result.state_output or {}).get("confirmed_facts_delta") or []),
            "open_questions_delta": list((result.state_output or {}).get("open_questions_delta") or []),
            "annotations": list(process_output.get("annotations") or []),
            "risks": list(process_output.get("risks") or []),
        }
        return {
            "model_output": model_output,
            "process_output": {
                "stage_audits": list(process_output.get("stage_audits") or []),
                "decision_trace": list(process_output.get("decision_trace") or []),
                "provider_logs": list(process_output.get("provider_logs") or []),
                "review_after_apply_result": dict(process_output.get("review_after_apply_result") or {}),
                "annotations": list(process_output.get("annotations") or []),
                "risks": list(process_output.get("risks") or []),
            },
            "state_output": {
                "confirmed_facts_delta": list((result.state_output or {}).get("confirmed_facts_delta") or []),
                "open_questions_delta": list((result.state_output or {}).get("open_questions_delta") or []),
                "spec_tree_update": dict((result.state_output or {}).get("spec_tree_update") or {}),
                "working_document_update": dict((result.state_output or {}).get("working_document_update") or {}),
                "turn_path_update": dict((result.state_output or {}).get("turn_path_update") or {}),
            },
            "raw_plugin_response": {
                "contract_version": result.contract_version,
                "plugin": dict(result.plugin or {}),
                "raw_output": raw_output,
            },
        }

    @staticmethod
    def _normalize_quick_options(value: object) -> list[dict]:
        if not isinstance(value, list):
            return []
        normalized: list[dict] = []
        fallback_keys = ("A", "B", "C", "D", "E")
        for index, item in enumerate(value[:5]):
            if isinstance(item, dict):
                key = str(item.get("key") or "").strip().upper()[:4]
                label = str(item.get("label") or "").strip()
                if key and label:
                    normalized.append({"key": key, "label": label, "recommended": bool(item.get("recommended"))})
                continue
            if isinstance(item, str):
                label = item.strip()
                if not label:
                    continue
                key = fallback_keys[index] if index < len(fallback_keys) else f"OPT{index + 1}"
                normalized.append({"key": key, "label": label, "recommended": index == 0})
        return normalized
