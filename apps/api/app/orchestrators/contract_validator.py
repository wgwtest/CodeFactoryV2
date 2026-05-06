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
            "template_shape_assessment": self.normalize_template_shape_assessment(payload.get("template_shape_assessment")),
            "target_anchor_plan": self.normalize_target_anchor_plan(payload.get("target_anchor_plan")),
            "confirmed_facts_delta": self.string_list(payload.get("confirmed_facts_delta")),
            "open_questions_delta": self.string_list(payload.get("open_questions_delta")),
            "document_patch": self.normalize_document_patch(
                payload.get("document_patch"),
                write_policy=write_policy,
                target_anchor_plan=self.normalize_target_anchor_plan(payload.get("target_anchor_plan")),
            ),
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

    def normalize_template_shape_assessment(self, value: Any) -> dict:
        if not isinstance(value, dict):
            return {
                "shape_type": "coarse_grained_extensible",
                "reason": "",
                "allowed_write_modes": [],
                "forbidden_write_modes": [],
                "template_revision_recommendations": [],
            }
        shape_type = str(value.get("shape_type") or "coarse_grained_extensible")
        allowed = {
            "fine_grained_fixed",
            "fine_grained_extensible",
            "coarse_grained_extensible",
            "coarse_grained_fixed",
            "editable_template",
            "coarse_extensible",
        }
        if shape_type not in allowed:
            shape_type = "coarse_grained_extensible"
        return {
            "shape_type": shape_type,
            "reason": str(value.get("reason") or ""),
            "allowed_write_modes": self.string_list(value.get("allowed_write_modes")),
            "forbidden_write_modes": self.string_list(value.get("forbidden_write_modes")),
            "template_revision_recommendations": self.string_list(value.get("template_revision_recommendations")),
        }

    def normalize_target_anchor_plan(self, value: Any) -> list[dict]:
        if not isinstance(value, list):
            return []
        plans: list[dict] = []
        seen: set[str] = set()
        for index, item in enumerate(value[:8], start=1):
            if not isinstance(item, dict):
                continue
            plan_id = str(item.get("plan_id") or f"AP-{index:03d}").strip()
            if not plan_id or plan_id in seen:
                raise ValueError(f"invalid duplicate target_anchor_plan.plan_id: {plan_id}")
            seen.add(plan_id)
            template_clause_id = str(item.get("template_clause_id") or "").strip()
            if not template_clause_id:
                raise ValueError(f"target_anchor_plan {plan_id} missing template_clause_id")
            confidence = self.normalize_confidence(item.get("confidence"))
            plans.append(
                {
                    "plan_id": plan_id,
                    "decision_type": str(item.get("decision_type") or "append_existing_clause"),
                    "template_clause_id": template_clause_id,
                    "canonical_clause_heading": str(item.get("canonical_clause_heading") or ""),
                    "subtopic_action": str(item.get("subtopic_action") or "none"),
                    "subtopic_key": str(item.get("subtopic_key") or ""),
                    "subtopic_title": str(item.get("subtopic_title") or ""),
                    "display_heading": str(item.get("display_heading") or item.get("canonical_clause_heading") or template_clause_id),
                    "template_shape_ref": str(item.get("template_shape_ref") or ""),
                    "reason": str(item.get("reason") or ""),
                    "confidence": confidence,
                    "anchor_path": str(item.get("anchor_path") or ""),
                }
            )
        return plans

    @staticmethod
    def normalize_document_patch(value: Any, *, write_policy: str, target_anchor_plan: list[dict] | None = None) -> list[dict]:
        if not isinstance(value, list):
            return []
        known_plan_ids = {str(plan.get("plan_id")) for plan in list(target_anchor_plan or [])}
        patches = []
        for item in value[:6]:
            if not isinstance(item, dict):
                continue
            plan_ref = str(item.get("plan_ref") or "").strip()
            content = str(item.get("content") or "").strip()
            if not plan_ref or not content:
                continue
            if known_plan_ids and plan_ref not in known_plan_ids:
                raise ValueError(f"document_patch.plan_ref does not match target_anchor_plan: {plan_ref}")
            patches.append(
                {
                    "plan_ref": plan_ref,
                    "operation": str(item.get("operation") or "append_or_update"),
                    "content": content,
                    "write_policy": str(item.get("write_policy") or write_policy),
                }
            )
        return patches
