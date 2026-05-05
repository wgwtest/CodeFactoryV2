from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
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
    ) -> ProviderRunResult:
        if orchestrator.mode == "local_runner":
            return self.run_local_runner(session, user_input, normalized, orchestrator=orchestrator)
        return self.run_provider(session, user_input, normalized, orchestrator=orchestrator)

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
            run_turn_kwargs = {"session": session, "user_input": user_input, "normalized": normalized}
            if "orchestrator_id" in signature(client.run_turn).parameters:
                run_turn_kwargs["orchestrator_id"] = orchestrator.orchestrator_id
            return self._to_provider_run_result(client.run_turn(**run_turn_kwargs))
        return self.mock_model_output(session, user_input, normalized, orchestrator=orchestrator)

    def mock_model_output(
        self,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> ProviderRunResult:
        semantic = normalized["semantic"]
        state = dict(session.payload or {})
        spec_tree = list(
            state.get("spec_tree")
            or self.spec_tree_service.new_spec_tree(session.template_id, orchestrator_id=orchestrator.orchestrator_id)
        )
        active_node = self.spec_tree_service.find_spec_node(
            spec_tree,
            str(state.get("active_spec_node_id") or ""),
        )
        active_section = active_node.get("target_section") if active_node else "未绑定模板章节"
        fact = self.process_artifact_service.fact_for_node(orchestrator.orchestrator_id, active_node, semantic)
        patch_content = self.process_artifact_service.patch_for_node(orchestrator.orchestrator_id, active_node, semantic)
        next_question = str(active_node.get("question") if active_node else "请继续补充需求规格说明。")
        quick_options = self.process_artifact_service.quick_options_for_node(orchestrator.orchestrator_id, active_node)

        provider_request = {
            "mock_context": {
                "topic": session.topic,
                "template_id": session.template_id,
                "knowledge_package_id": session.knowledge_package_id,
                "write_policy": session.write_policy,
                "user_input": user_input,
                "normalized_input": normalized,
                "working_document": dict(state.get("working_document") or {}),
                "active_spec_node": active_node or {},
            }
        }
        provider_response = {
            "organizer_interpretation": {
                "summary": f"用户输入可转化为 {active_section} 的需求规格材料。",
                "intent": "supplement_requirement",
                "confidence": "medium",
            },
            "assistant_message": f"基于你的输入，本轮更新了：{active_section}。",
            "next_suggestion": {
                "kind": "topic",
                "content": "",
                "reason": "",
                "related_spec_node_ids": [],
            },
            "next_question": next_question,
            "quick_options": quick_options,
            "confirmed_facts_delta": [fact],
            "open_questions_delta": [next_question],
            "document_patch": [
                {
                    "section": active_section,
                    "operation": "append_or_update",
                    "content": patch_content,
                    "write_policy": session.write_policy,
                }
            ],
            "annotations": ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
            "risks": [],
            "confidence": "medium",
        }

        return self._to_provider_run_result({
            **provider_response,
            "organizer_interpretation": {
                "summary": f"用户输入可转化为 {active_section} 的需求规格材料。",
                "intent": "supplement_requirement",
                "confidence": "medium",
            },
            "assistant_message": f"基于你的输入，本轮更新了：{active_section}。",
            "next_suggestion": {
                "kind": "topic",
                "content": "",
                "reason": "",
                "related_spec_node_ids": [],
            },
            "next_question": next_question,
            "quick_options": quick_options,
            "confirmed_facts_delta": [fact],
            "open_questions_delta": [next_question],
            "document_patch": [
                {
                    "section": active_section,
                    "operation": "append_or_update",
                    "content": patch_content,
                    "write_policy": session.write_policy,
                }
            ],
            "annotations": ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
            "risks": [],
            "confidence": "medium",
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
