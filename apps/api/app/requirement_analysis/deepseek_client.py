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

    def run_turn(self, *, session: SessionSnapshot, user_input: str, normalized: dict, orchestrator_id: str | None = None) -> dict:
        prompt_bundle = self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=orchestrator_id or session.orchestrator_id,
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
        )

    def _build_prompt_bundle(
        self,
        *,
        session: SessionSnapshot,
        user_input: str,
        normalized: dict,
        orchestrator_id: str,
    ) -> dict:
        state = dict(session.payload or {})
        spec_tree = list(state.get("spec_tree", []))
        context = {
            "topic": session.topic,
            "template_id": session.template_id,
            "knowledge_package_id": session.knowledge_package_id,
            "write_policy": session.write_policy,
            "previous_interaction": state.get("next_interaction"),
            "last_quick_options": list(state.get("last_quick_options", [])),
            "spec_tree": spec_tree,
            "messages": list(state.get("messages", []))[-8:],
            "confirmed_facts": list(state.get("confirmed_facts", [])),
            "open_questions": list(state.get("open_questions", [])),
            "user_input": user_input,
            "normalized_input": normalized,
        }
        schema = {
            "organizer_interpretation": {
                "summary": "你对用户本轮输入的理解",
                "intent": "supplement_requirement|ask_question|correct_direction|challenge|continue",
                "confidence": "low|medium|high",
            },
            "assistant_message": "给用户看的简短回答和推进建议",
            "next_suggestion": {
                "kind": "topic",
                "content": "下一轮建议话题，可为空字符串",
                "reason": "为什么建议这个方向",
                "related_spec_node_ids": ["SPEC-REQ-x.x"],
            },
            "quick_options": [
                {"key": "A", "label": "选项文本", "recommended": True},
                {"key": "B", "label": "选项文本", "recommended": False},
            ],
            "confirmed_facts_delta": ["本轮新增确认事实"],
            "open_questions_delta": ["本轮新增待确认问题"],
            "document_patch": [
                {
                    "section": "需求规格章节号或标题",
                    "operation": "append_or_update",
                    "content": "建议写入正式需求规格的片段",
                    "write_policy": session.write_policy,
                }
            ],
            "annotations": ["给系统读取的注记"],
            "risks": ["风险或空数组"],
            "confidence": "low|medium|high",
        }
        return self.runner_host.build_provider_prompt_bundle(
            orchestrator_id,
            context=context,
            output_schema=schema,
        )

    def _build_prompt(self, *, session: SessionSnapshot, user_input: str, normalized: dict) -> str:
        runner_host = getattr(self, "runner_host", None) or OrchestratorRunnerHost()
        self.runner_host = runner_host
        return self._build_prompt_bundle(
            session=session,
            user_input=user_input,
            normalized=normalized,
            orchestrator_id=session.orchestrator_id,
        )["assembled_prompt"]

    def _find_spec_node(self, nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            found = self._find_spec_node(list(node.get("children", [])), node_id)
            if found is not None:
                return found
        return None

    def _spec_node_path(self, nodes: list[dict], node_id: str, current: list[str] | None = None) -> list[str]:
        current = current or []
        for node in nodes:
            next_path = [*current, str(node.get("title") or node.get("node_id"))]
            if node.get("node_id") == node_id:
                return next_path
            child_path = self._spec_node_path(list(node.get("children", [])), node_id, next_path)
            if child_path:
                return child_path
        return []

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
    ) -> dict:
        normalized_output = {
            "organizer_interpretation": self._normalize_organizer_interpretation(payload.get("organizer_interpretation")),
            "assistant_message": str(payload.get("assistant_message") or "已接收，本轮需要继续补齐需求信息。"),
            "next_suggestion": self._normalize_next_suggestion(payload.get("next_suggestion")),
            "next_question": str(payload.get("next_question") or ""),
            "quick_options": self._normalize_quick_options(payload.get("quick_options")),
            "confirmed_facts_delta": self._string_list(payload.get("confirmed_facts_delta")),
            "open_questions_delta": self._string_list(payload.get("open_questions_delta")),
            "document_patch": self._normalize_document_patch(payload.get("document_patch"), session=session),
            "annotations": self._string_list(payload.get("annotations")),
            "risks": self._string_list(payload.get("risks")),
            "confidence": self._normalize_confidence(payload.get("confidence")),
        }
        return {
            **normalized_output,
            "raw_model_response": {
                "provider_id": "deepseek",
                "model": self.model,
                "mock": False,
                "user_input": user_input,
                "orchestrator_id": str((prompt_bundle or {}).get("orchestrator_id") or session.orchestrator_id),
                "mode": str((prompt_bundle or {}).get("mode") or "provider"),
                "provider_request": {
                    "messages": list(request_messages or []),
                    "prompt_bundle": {
                        "assembled_prompt": str((prompt_bundle or {}).get("assembled_prompt") or ""),
                        "context_json": str((prompt_bundle or {}).get("context_json") or ""),
                        "schema_json": str((prompt_bundle or {}).get("schema_json") or ""),
                        "policy_text": str((prompt_bundle or {}).get("policy_text") or ""),
                        "prompt_text": str((prompt_bundle or {}).get("prompt_text") or ""),
                    },
                },
                "provider_response": {
                    "raw_content": str(raw_content or ""),
                    "parsed_json": payload,
                },
                "provider_normalized_output": normalized_output,
            },
        }

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        confidence = str(value or "medium").lower()
        return confidence if confidence in {"low", "medium", "high"} else "medium"

    @staticmethod
    def _normalize_organizer_interpretation(value: Any) -> dict:
        if not isinstance(value, dict):
            return {"summary": "已理解用户本轮输入。", "intent": "supplement_requirement", "confidence": "medium"}
        return {
            "summary": str(value.get("summary") or "已理解用户本轮输入。"),
            "intent": str(value.get("intent") or "supplement_requirement"),
            "confidence": DeepSeekRequirementAnalysisClient._normalize_confidence(value.get("confidence")),
        }

    @staticmethod
    def _normalize_next_suggestion(value: Any) -> dict:
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
    def _normalize_quick_options(value: Any) -> list[dict]:
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
    def _normalize_document_patch(value: Any, *, session: SessionSnapshot) -> list[dict]:
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
                    "write_policy": str(item.get("write_policy") or session.write_policy),
                }
            )
        return patches

    @staticmethod
    def _find_spec_node_static(nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            found = DeepSeekRequirementAnalysisClient._find_spec_node_static(list(node.get("children", [])), node_id)
            if found is not None:
                return found
        return None
