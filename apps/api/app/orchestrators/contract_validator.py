from __future__ import annotations

from typing import Any


class OrchestratorContractValidator:
    def normalize_turn_output(
        self,
        payload: dict[str, Any],
        *,
        provider_id: str,
        model: str,
        write_policy: str,
        raw_response: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "organizer_interpretation": self.normalize_organizer_interpretation(payload.get("organizer_interpretation")),
            "assistant_message": str(payload.get("assistant_message") or "已接收，本轮需要继续补齐需求信息。"),
            "next_suggestion": self.normalize_next_suggestion(payload.get("next_suggestion")),
            "next_question": str(payload.get("next_question") or ""),
            "quick_options": self.normalize_quick_options(payload.get("quick_options")),
            "confirmed_facts_delta": self.string_list(payload.get("confirmed_facts_delta")),
            "open_questions_delta": self.string_list(payload.get("open_questions_delta")),
            "document_patch": self.normalize_document_patch(payload.get("document_patch"), write_policy=write_policy),
            "annotations": self.string_list(payload.get("annotations")),
            "risks": self.string_list(payload.get("risks")),
            "confidence": self.normalize_confidence(payload.get("confidence")),
            "raw_model_response": {
                "provider_id": provider_id,
                "model": model,
                **dict(raw_response or {}),
            },
        }

    @staticmethod
    def string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def normalize_confidence(value: Any) -> str:
        confidence = str(value or "medium").lower()
        return confidence if confidence in {"low", "medium", "high"} else "medium"

    def normalize_organizer_interpretation(self, value: Any) -> dict:
        if not isinstance(value, dict):
            return {"summary": "已理解用户本轮输入。", "intent": "supplement_requirement", "confidence": "medium"}
        return {
            "summary": str(value.get("summary") or "已理解用户本轮输入。"),
            "intent": str(value.get("intent") or "supplement_requirement"),
            "confidence": self.normalize_confidence(value.get("confidence")),
        }

    @staticmethod
    def normalize_next_suggestion(value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "kind": "topic",
                "content": "",
                "reason": "Provider 未生成下一轮建议。",
                "related_spec_node_ids": [],
            }
        related = value.get("related_spec_node_ids")
        return {
            "kind": str(value.get("kind") or "topic"),
            "content": str(value.get("content") or ""),
            "reason": str(value.get("reason") or ""),
            "related_spec_node_ids": [str(item) for item in related if str(item).strip()] if isinstance(related, list) else [],
        }

    @staticmethod
    def normalize_quick_options(value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []
        options = []
        for item in value[:5]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()[:4]
            label = str(item.get("label") or "").strip()
            if key and label:
                options.append({"key": key, "label": label, "recommended": bool(item.get("recommended"))})
        return options

    @staticmethod
    def normalize_document_patch(value: Any, *, write_policy: str) -> list[dict]:
        if not isinstance(value, list):
            return []
        patches = []
        for item in value[:6]:
            if not isinstance(item, dict):
                continue
            section = str(item.get("section") or "").strip()
            content = str(item.get("content") or "").strip()
            if not section or not content:
                continue
            patches.append(
                {
                    "section": section,
                    "operation": str(item.get("operation") or "append_or_update"),
                    "content": content,
                    "write_policy": str(item.get("write_policy") or write_policy),
                }
            )
        return patches
