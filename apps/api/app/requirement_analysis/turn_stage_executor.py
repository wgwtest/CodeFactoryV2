from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.provider_call_service import ProviderRunResult, RequirementAnalysisProviderCallService
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.turn_context_builder import TurnContext


@dataclass(frozen=True)
class TurnStageResult:
    stage_id: str
    stage_type: str
    provider_run_result: ProviderRunResult
    model_output: dict


class TurnStageExecutor:
    def __init__(self, *, provider_call_service: RequirementAnalysisProviderCallService) -> None:
        self.provider_call_service = provider_call_service

    def run(
        self,
        *,
        stage: dict,
        orchestrator: OrchestratorPackage,
        session: SessionSnapshot,
        context: TurnContext,
    ) -> TurnStageResult:
        stage_type = str(stage.get("stage_type") or orchestrator.mode)
        if stage_type == "server_review":
            provider_run_result = self._run_server_review(stage=stage, context=context)
        else:
            provider_run_result = self.provider_call_service.run_orchestrator(
                orchestrator=orchestrator,
                session=session,
                user_input=context.user_input,
                normalized=context.normalized_input,
            )
        return TurnStageResult(
            stage_id=str(stage.get("stage_id") or "stage-001"),
            stage_type=stage_type,
            provider_run_result=provider_run_result,
            model_output=provider_run_result.model_output,
        )

    @staticmethod
    def _run_server_review(*, stage: dict, context: TurnContext) -> ProviderRunResult:
        semantic = str(context.normalized_input.get("semantic") or context.user_input).strip()
        prompt = (
            str(context.previous_interaction.get("prompt") or "").strip()
            if isinstance(context.previous_interaction, dict)
            else ""
        )
        review_summary = (
            f"系统复核：本轮输入“{semantic}”已被吸收，下一步继续围绕“{prompt or context.active_spec_node.get('question') or '需求规格补充'}”推进。"
        )
        model_output = {
            "organizer_interpretation": {
                "summary": review_summary,
                "intent": "supplement_requirement",
                "confidence": "medium",
            },
            "assistant_message": "",
            "next_suggestion": {
                "kind": "topic",
                "content": prompt,
                "reason": "服务端复核阶段补充下一轮建议。",
                "related_spec_node_ids": [str(context.active_spec_node_id)] if context.active_spec_node_id else [],
            },
            "next_question": prompt,
            "quick_options": [],
            "confirmed_facts_delta": [],
            "open_questions_delta": [],
            "document_patch": [],
            "annotations": [f"服务端复核阶段 {stage.get('stage_id') or 'review'} 已执行。"],
            "risks": [],
            "confidence": "medium",
            "raw_model_response": {
                "provider_id": "server_review",
                "model": str(stage.get("model") or "server-review"),
                "mock": True,
                "user_input": context.user_input,
                "provider_request": {
                    "review_context": {
                        "previous_interaction": context.previous_interaction,
                        "active_spec_node": context.active_spec_node,
                        "normalized_input": context.normalized_input,
                    }
                },
                "provider_response": {
                    "raw_content": review_summary,
                    "parsed_json": {
                        "organizer_interpretation": {
                            "summary": review_summary,
                            "intent": "supplement_requirement",
                            "confidence": "medium",
                        }
                    },
                },
                "provider_normalized_output": {
                    "organizer_interpretation": {
                        "summary": review_summary,
                        "intent": "supplement_requirement",
                        "confidence": "medium",
                    }
                },
            },
        }
        return ProviderRunResult(
            model_output=model_output,
            provider_request=dict(model_output["raw_model_response"]["provider_request"]),
            provider_response=dict(model_output["raw_model_response"]["provider_response"]),
            normalized_output=dict(model_output["raw_model_response"]["provider_normalized_output"]),
        )
