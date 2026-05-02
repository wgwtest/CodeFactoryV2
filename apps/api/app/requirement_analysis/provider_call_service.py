from __future__ import annotations

from inspect import signature
from typing import Any

from app.config import settings
from app.db.models.requirements import RequirementAnalysisSession
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.orchestrators.package_loader import OrchestratorPackage
from app.requirement_analysis.deepseek_client import DeepSeekRequirementAnalysisClient


class RequirementAnalysisProviderCallService:
    def __init__(self, owner: Any) -> None:
        self.owner = owner
        self.runner_host = OrchestratorRunnerHost()

    def run_orchestrator(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
    ) -> dict:
        if orchestrator.mode == "local_runner":
            return self.run_local_runner(session, user_input, normalized, orchestrator=orchestrator)
        return self.run_provider(session, user_input, normalized, orchestrator=orchestrator)

    def run_local_runner(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        state = dict(session.payload or {})
        active_node = self.owner._find_spec_node(
            list(state.get("spec_tree") or self.owner._new_spec_tree(session.template_id)),
            str(state.get("active_spec_node_id") or ""),
        )
        return self.runner_host.execute_local_runner(
            orchestrator.orchestrator_id,
            context={
                "session": {
                    "session_id": session.id,
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
            },
        )

    def run_provider(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
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
            return client.run_turn(**run_turn_kwargs)
        return self.mock_model_output(session, user_input, normalized, orchestrator=orchestrator)

    def mock_model_output(
        self,
        session: RequirementAnalysisSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        semantic = normalized["semantic"]
        state = dict(session.payload or {})
        active_node = self.owner._find_spec_node(
            list(state.get("spec_tree") or self.owner._new_spec_tree(session.template_id)),
            str(state.get("active_spec_node_id") or ""),
        )
        active_section = active_node.get("target_section") if active_node else "未绑定模板章节"
        clause_id = self.owner._clause_id_from_node(active_node)
        fact = self.owner._fact_for_active_node(clause_id, semantic)
        patch_content = self.owner._patch_for_active_node(clause_id, semantic)
        next_question = str(active_node.get("question") if active_node else "请继续补充需求规格说明。")
        quick_options = self.owner._quick_options_for_node(active_node)

        return {
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
            },
        }

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
