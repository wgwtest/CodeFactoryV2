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
        created_at: str,
        call_index: int,
    ) -> dict:
        raw_model_response = dict(model_output.get("raw_model_response") or {})
        return {
            "call_id": f"requirement-analysis-provider-call-{call_index:04d}",
            "turn_id": turn_id,
            "provider_id": session.provider_id,
            "orchestrator_id": orchestrator.orchestrator_id,
            "orchestrator_mode": orchestrator.mode,
            "model": session.model,
            "status": "mocked" if raw_model_response.get("mock") else "completed",
            "created_at": created_at,
            "audit": {
                "user_input": str(raw_model_response.get("user_input") or user_input),
                "normalized_input": normalized,
                "provider_request": raw_model_response.get("provider_request") or {},
                "provider_response": raw_model_response.get("provider_response") or {},
                "provider_normalized_output": provider_normalized_output or self.provider_normalized_output(model_output),
                "service_output": self.service_output(model_output),
            },
        }
