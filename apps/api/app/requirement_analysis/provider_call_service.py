from __future__ import annotations

from dataclasses import dataclass
from app.config import settings
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.deepseek_client import DeepSeekRequirementAnalysisClient
from app.requirement_analysis.process_artifact_service import ProcessArtifactService
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService


@dataclass(frozen=True)
class ProviderRunResult:
    model_output: dict
    provider_request: dict
    provider_response: dict
    normalized_output: dict


class RequirementAnalysisProviderCallService:
    def __init__(
        self,
        *,
        spec_tree_service: RequirementSpecTreeService,
        process_artifact_service: ProcessArtifactService,
    ) -> None:
        self.spec_tree_service = spec_tree_service
        self.process_artifact_service = process_artifact_service
        self.runner_host = OrchestratorRunnerHost()

    def run_orchestrator(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        stage: dict | None = None,
        stage_input: dict | None = None,
    ) -> ProviderRunResult:
        if orchestrator.mode == "local_runner":
            return self.run_local_runner(session, user_input, normalized, orchestrator=orchestrator)
        return self.run_provider(
            session,
            user_input,
            normalized,
            orchestrator=orchestrator,
            stage=stage,
            stage_input=stage_input,
        )

    def run_local_runner(
        self,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> ProviderRunResult:
        state = dict(session.payload or {})
        spec_tree = list(
            state.get("spec_tree")
            or self.spec_tree_service.new_spec_tree(session.template_id, orchestrator_id=orchestrator.orchestrator_id)
        )
        active_node = self.spec_tree_service.find_spec_node(
            spec_tree,
            str(state.get("active_spec_node_id") or ""),
        )
        context = {
            "session": {
                "session_id": session.session_id,
                "topic": session.topic,
                "provider_id": session.provider_id,
                "model": session.model,
                "template_id": session.template_id,
                "knowledge_package_id": session.knowledge_package_id,
                "write_policy": session.write_policy,
            },
            "user_input": user_input,
            "normalized": normalized,
            "active_spec_node": active_node or {},
            "state": state,
        }
        output = self.runner_host.execute_local_runner(
            orchestrator.orchestrator_id,
            context=context,
        )
        raw_model_response = dict(output.get("raw_model_response") or {})
        output["raw_model_response"] = {
            **raw_model_response,
            "provider_request": {
                "runner_context": context,
            },
            "provider_response": {
                "raw_content": raw_model_response.get("runner_entry", "local_runner"),
                "parsed_json": {
                    key: value for key, value in output.items() if key != "raw_model_response"
                },
            },
            "provider_normalized_output": {
                key: value for key, value in output.items() if key != "raw_model_response"
            },
        }
        return self._to_provider_run_result(output)

    def run_provider(
        self,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
        stage: dict | None = None,
        stage_input: dict | None = None,
    ) -> ProviderRunResult:
        if session.provider_id == "deepseek":
            if not settings.requirement_analysis_deepseek_api_key:
                raise ValueError("DeepSeek provider is not configured")
            client_class = self._deepseek_client_class()
            client = client_class(
                api_key=settings.requirement_analysis_deepseek_api_key,
                base_url=settings.requirement_analysis_deepseek_base_url,
                model=session.model or settings.requirement_analysis_deepseek_model,
            )
            run_stage = getattr(client, "run_stage", None)
            if callable(run_stage) and stage is not None:
                run_stage_kwargs = {
                    "session": session,
                    "user_input": user_input,
                    "normalized": normalized,
                    "orchestrator_id": orchestrator.orchestrator_id,
                    "stage": stage,
                    "stage_input": stage_input or {},
                }
                return self._to_provider_run_result(run_stage(**run_stage_kwargs))
            raise RuntimeError("DeepSeek provider must be invoked through run_stage(stage=...)")
        return self.mock_model_output(
            session,
            user_input,
            normalized,
            orchestrator=orchestrator,
            stage=stage,
            stage_input=stage_input,
        )

    def mock_model_output(
        self,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
        stage: dict | None = None,
        stage_input: dict | None = None,
    ) -> ProviderRunResult:
        semantic = normalized["semantic"]
        provider_response = {
            "assistant_message": f"Mock provider received: {semantic}",
            "filled_document_text": semantic,
            "document_patch": [],
            "confirmed_facts_delta": [semantic] if semantic else [],
            "open_questions_delta": [],
            "annotations": ["通用 Mock Provider 只回显输入；组织器特定 Mock 行为应由插件实现。"],
            "risks": [],
            "confidence": "medium",
        }
        provider_request = self._mock_provider_request(
            session=session,
            user_input=user_input,
            normalized=normalized,
            stage=stage or {},
            stage_input=stage_input or {},
        )

        return self._to_provider_run_result({
            **provider_response,
            "raw_model_response": {
                "provider_id": session.provider_id,
                "model": session.model,
                "mock": True,
                "orchestrator_id": orchestrator.orchestrator_id,
                "mode": orchestrator.mode,
                "user_input": user_input,
                "provider_request": provider_request,
                "provider_response": {
                    "raw_content": "mock_model_output",
                    "parsed_json": provider_response,
                },
                "provider_normalized_output": provider_response,
            },
        })

    def _mock_provider_request(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        stage: dict,
        stage_input: dict,
    ) -> dict:
        stage_payload = dict(stage)
        return {
            "messages": [{"role": "user", "content": user_input}],
            "stage": stage_payload,
            "stage_input": stage_input,
            "mock_context": {
                "topic": session.topic,
                "template_id": session.template_id,
                "knowledge_package_id": session.knowledge_package_id,
                "write_policy": session.write_policy,
                "user_input": user_input,
                "normalized_input": normalized,
                "stage": stage_payload,
            },
        }

    @staticmethod
    def _to_provider_run_result(model_output: dict) -> ProviderRunResult:
        raw_model_response = dict(model_output.get("raw_model_response") or {})
        normalized_output = raw_model_response.get("provider_normalized_output")
        if not isinstance(normalized_output, dict):
            normalized_output = {
                key: value for key, value in model_output.items() if key != "raw_model_response"
            }
        return ProviderRunResult(
            model_output=model_output,
            provider_request=dict(raw_model_response.get("provider_request") or {}),
            provider_response=dict(raw_model_response.get("provider_response") or {}),
            normalized_output=normalized_output,
        )

    @staticmethod
    def _deepseek_client_class():
        try:
            from app.requirement_analysis import deepseek_client as requirement_analysis_client_module

            return getattr(
                requirement_analysis_client_module,
                "DeepSeekRequirementAnalysisClient",
                DeepSeekRequirementAnalysisClient,
            )
        except Exception:
            return DeepSeekRequirementAnalysisClient
