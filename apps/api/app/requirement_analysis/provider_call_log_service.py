from __future__ import annotations

from typing import Any

from app.requirement_analysis.session_snapshot import SessionSnapshot


class ProviderCallLogService:
    @staticmethod
    def provider_normalized_output(model_output: dict) -> dict:
        raw_model_response = dict(model_output.get("raw_model_response") or {})
        existing = raw_model_response.get("provider_normalized_output")
        if isinstance(existing, dict):
            return existing
        return {
            key: value
            for key, value in model_output.items()
            if key != "raw_model_response"
        }

    @staticmethod
    def service_output(model_output: dict) -> dict:
        return {
            key: value
            for key, value in model_output.items()
            if key != "raw_model_response"
        }

    def build(
        self,
        *,
        turn_id: str,
        session: SessionSnapshot,
        orchestrator: Any,
        user_input: str,
        normalized: dict,
        model_output: dict,
        provider_normalized_output: dict | None = None,
        service_output: dict | None = None,
        prompt_bundle_overrides: dict | None = None,
        provider_response_overrides: dict | None = None,
        stage_id: str | None = None,
        stage_type: str | None = None,
        created_at: str,
        call_index: int,
    ) -> dict:
        raw_model_response = dict(model_output.get("raw_model_response") or {})
        provider_request = dict(raw_model_response.get("provider_request") or {})
        provider_response = dict(raw_model_response.get("provider_response") or {})
        if prompt_bundle_overrides:
            prompt_bundle = dict(provider_request.get("prompt_bundle") or {})
            for key, value in prompt_bundle_overrides.items():
                current_value = prompt_bundle.get(key)
                if current_value in (None, "", [], {}):
                    prompt_bundle[key] = value
            provider_request["prompt_bundle"] = prompt_bundle
        if provider_response_overrides:
            provider_response.update(provider_response_overrides)
        return {
            "call_id": f"requirement-analysis-provider-call-{call_index:04d}",
            "turn_id": turn_id,
            "stage_id": stage_id or "stage-001",
            "stage_type": stage_type or "unknown",
            "provider_id": session.provider_id,
            "orchestrator_id": orchestrator.orchestrator_id,
            "orchestrator_mode": orchestrator.mode,
            "model": session.model,
            "status": "mocked" if raw_model_response.get("mock") else "completed",
            "created_at": created_at,
            "audit": {
                "user_input": str(raw_model_response.get("user_input") or user_input),
                "normalized_input": normalized,
                "provider_request": provider_request,
                "provider_response": provider_response,
                "provider_normalized_output": provider_normalized_output or self.provider_normalized_output(model_output),
                "service_output": service_output or self.service_output(model_output),
            },
        }
