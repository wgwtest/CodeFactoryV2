from __future__ import annotations


class QuestionnairePolicyService:
    def validate(self, questionnaire_policy: dict | None) -> list[dict]:
        if questionnaire_policy is None:
            return []
        if not isinstance(questionnaire_policy, dict):
            return [{"field": "questionnaire_policy", "message": "questionnaire_policy must be an object"}]
        return []

    def summarize_for_analysis(self, template_payload: dict) -> dict:
        return dict(template_payload.get("questionnaire_policy", {}))

