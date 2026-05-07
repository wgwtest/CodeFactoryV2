from __future__ import annotations

import json
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings
from app.orchestrators.runner_host import OrchestratorRunnerHost
from app.requirement_analysis.session_snapshot import SessionSnapshot


class DeepSeekRequirementAnalysisClient:
    def __init__(self, *, api_key: str, base_url: str, model: str, runner_host: OrchestratorRunnerHost | None = None) -> None:
        self.model = model
        self.runner_host = runner_host or OrchestratorRunnerHost()
        self.client = OpenAI(api_key=api_key, base_url=base_url, http_client=httpx.Client(trust_env=False))

    def run_stage(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator_id: str,
        stage: dict,
        stage_input: dict | None = None,
    ) -> dict:
        prompt_bundle = self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=orchestrator_id,
            stage=stage,
            stage_input=stage_input or {},
        )
        request_messages = [
            {
                "role": "system",
                "content": (
                    "你是 CodeFactory V2 P2 XG 需求分析组织器 Lab 的可插拔组织器 Provider。"
                    "你只返回 JSON，不要返回 Markdown。"
                ),
            },
            {"role": "user", "content": prompt_bundle["assembled_prompt"]},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=request_messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = self._extract_content(response)
        parsed = json.loads(content)
        return self._normalize_output(
            parsed,
            session=session,
            user_input=user_input,
            prompt_bundle=prompt_bundle,
            request_messages=request_messages,
            raw_content=content,
            stage=stage,
        )

    def _build_prompt_bundle(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator_id: str,
        stage: dict | None = None,
        stage_input: dict | None = None,
    ) -> dict:
        state = dict(session.payload or {})
        stage = stage or {"stage_id": "write", "stage_kind": "write", "prompt_id": "write"}
        context = dict(stage_input or self._base_stage_context(session=session, user_input=user_input, normalized=normalized))
        extra_prompt_bundle = {
            "decision_state_json": json.dumps(context.get("decision_state") or state.get("decision_state") or {}, ensure_ascii=False),
            "decision_state_document_json": json.dumps(context.get("decision_state_document") or state.get("decision_state_document") or {}, ensure_ascii=False),
            "working_document_json": json.dumps(context.get("working_document") or {}, ensure_ascii=False),
            "working_document_after_apply_json": json.dumps(context.get("working_document_after_apply") or {}, ensure_ascii=False),
            "working_document_update_json": json.dumps(context.get("working_document_update") or {}, ensure_ascii=False),
            "chapter_configuration_context_json": json.dumps(context.get("chapter_configuration_context") or {}, ensure_ascii=False),
            "template_shape_assessment_json": json.dumps(context.get("template_shape_assessment") or {}, ensure_ascii=False),
            "target_anchor_plan_json": json.dumps(context.get("target_anchor_plan") or [], ensure_ascii=False),
            "working_document_excerpt": str((context.get("working_document_after_apply") or {}).get("excerpt") or context.get("working_document_excerpt") or ""),
            "review_target_paths": list(context.get("review_target_paths") or []),
            "recent_revision_fragments": list(context.get("recent_revision_fragments") or []),
            "review_goal": str(context.get("review_goal") or ""),
            "stage_task_definition_json": json.dumps(context.get("stage_task_definition") or {}, ensure_ascii=False),
            "quality_constraints_json": json.dumps(context.get("stage_quality_constraints") or {}, ensure_ascii=False),
        }
        runner_host = getattr(self, "runner_host", None) or OrchestratorRunnerHost()
        self.runner_host = runner_host
        return runner_host.build_stage_prompt_bundle(
            orchestrator_id,
            stage=stage,
            context=context,
            extra_prompt_bundle=extra_prompt_bundle,
        )

    @staticmethod
    def _base_stage_context(*, session: SessionSnapshot, user_input: str, normalized: dict) -> dict:
        state = dict(getattr(session, "payload", {}) or {})
        return {
            "turn_context": {
                "topic": getattr(session, "topic", ""),
                "template_id": getattr(session, "template_id", ""),
                "knowledge_package_id": getattr(session, "knowledge_package_id", ""),
                "write_policy": getattr(session, "write_policy", ""),
                "previous_interaction": state.get("next_interaction"),
                "last_quick_options": list(state.get("last_quick_options", [])),
                "messages": list(state.get("messages", []))[-8:],
                "confirmed_facts": list(state.get("confirmed_facts", [])),
                "open_questions": list(state.get("open_questions", [])),
                "user_input": user_input,
                "normalized_input": normalized,
                "active_spec_node_id": str(state.get("active_spec_node_id") or ""),
            },
            "working_document": dict(state.get("working_document") or {}),
            "spec_tree": list(state.get("spec_tree", [])),
            "previous_interaction": state.get("next_interaction"),
            "user_input": user_input,
            "normalized_input": normalized,
        }

    def _build_prompt(self, *, session: SessionSnapshot, user_input: str, normalized: dict) -> str:
        runner_host = getattr(self, "runner_host", None) or OrchestratorRunnerHost()
        self.runner_host = runner_host
        return self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=session.orchestrator_id,
        )["assembled_prompt"]

    @staticmethod
    def _extract_content(response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("DeepSeek 未返回 choices")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 响应缺少 JSON 文本")
        return content

    def _normalize_output(
        self,
        payload: dict[str, Any],
        *,
        session: SessionSnapshot,
        user_input: str,
        prompt_bundle: dict[str, Any] | None = None,
        request_messages: list[dict[str, str]] | None = None,
        raw_content: str | None = None,
        stage: dict | None = None,
    ) -> dict:
        normalized_output = dict(payload)
        if isinstance(normalized_output.get("document_patch"), list):
            normalized_output["document_patch"] = [
                {**item, "write_policy": str(item.get("write_policy") or session.write_policy)}
                if isinstance(item, dict)
                else item
                for item in normalized_output["document_patch"]
            ]
        return {
            **normalized_output,
            "raw_model_response": self._stage_raw_model_response(
                session=session,
                user_input=user_input,
                prompt_bundle=prompt_bundle,
                request_messages=request_messages,
                raw_content=raw_content,
                payload=payload,
                normalized_output=normalized_output,
                stage=stage,
            ),
        }

    @staticmethod
    def _stage_raw_model_response(
        *,
        session: SessionSnapshot,
        user_input: str,
        prompt_bundle: dict[str, Any] | None,
        request_messages: list[dict[str, str]] | None,
        raw_content: str | None,
        payload: dict[str, Any],
        normalized_output: dict[str, Any],
        stage: dict | None,
    ) -> dict:
        safe_prompt_bundle = {
            "assembled_prompt": str((prompt_bundle or {}).get("assembled_prompt") or ""),
            "context_json": str((prompt_bundle or {}).get("context_json") or ""),
            "decision_state_json": str((prompt_bundle or {}).get("decision_state_json") or ""),
            "decision_state_document_json": str((prompt_bundle or {}).get("decision_state_document_json") or ""),
            "working_document_json": str((prompt_bundle or {}).get("working_document_json") or ""),
            "working_document_after_apply_json": str((prompt_bundle or {}).get("working_document_after_apply_json") or ""),
            "working_document_update_json": str((prompt_bundle or {}).get("working_document_update_json") or ""),
            "chapter_configuration_context_json": str((prompt_bundle or {}).get("chapter_configuration_context_json") or ""),
            "template_shape_assessment_json": str((prompt_bundle or {}).get("template_shape_assessment_json") or ""),
            "target_anchor_plan_json": str((prompt_bundle or {}).get("target_anchor_plan_json") or ""),
            "working_document_excerpt": str((prompt_bundle or {}).get("working_document_excerpt") or ""),
            "review_target_paths": list((prompt_bundle or {}).get("review_target_paths") or []),
            "recent_revision_fragments": list((prompt_bundle or {}).get("recent_revision_fragments") or []),
            "review_goal": str((prompt_bundle or {}).get("review_goal") or ""),
            "schema_json": str((prompt_bundle or {}).get("schema_json") or ""),
            "adoption_policy_json": str((prompt_bundle or {}).get("adoption_policy_json") or ""),
            "stage_task_definition_json": str((prompt_bundle or {}).get("stage_task_definition_json") or ""),
            "quality_constraints_json": str((prompt_bundle or {}).get("quality_constraints_json") or ""),
            "policy_text": str((prompt_bundle or {}).get("policy_text") or ""),
            "prompt_text": str((prompt_bundle or {}).get("prompt_text") or ""),
            "stage_id": str((prompt_bundle or {}).get("stage_id") or ""),
            "prompt_id": str((prompt_bundle or {}).get("prompt_id") or ""),
        }
        return {
            "provider_id": "deepseek",
            "model": str(getattr(session, "model", "") or "deepseek-chat"),
            "mock": False,
            "user_input": user_input,
            "orchestrator_id": str((prompt_bundle or {}).get("orchestrator_id") or session.orchestrator_id),
            "mode": str((prompt_bundle or {}).get("mode") or "provider"),
            "stage_id": str((prompt_bundle or {}).get("stage_id") or (stage or {}).get("stage_id") or ""),
            "provider_request": {
                "messages": list(request_messages or []),
                "prompt_bundle": safe_prompt_bundle,
            },
            "provider_response": {
                "raw_content": str(raw_content or ""),
                "parsed_json": payload,
            },
            "provider_normalized_output": normalized_output,
        }

    @staticmethod
    def _find_spec_node_static(nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            found = DeepSeekRequirementAnalysisClient._find_spec_node_static(list(node.get("children", [])), node_id)
            if found is not None:
                return found
        return None
