from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from llama_index.core.types import PydanticProgramMode
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI
from openai import OpenAI as OpenAIClient

from app.integrations.llm.config import resolve_llm_config
from app.integrations.llm.openai_compatible import OpenAICompatibleLLM

_VALID_ITEM_TYPES = {"entity", "event", "process"}
_DEFAULT_CATEGORIES = {
    "entity": "domain_concept",
    "event": "timeline_event",
    "process": "domain_process",
}
_VALID_RELATION_TYPES = {
    "describes",
    "owned_by",
    "part_of",
    "operational_exchange",
    "participates_in_exchange",
    "scoped_by",
    "process_scoped_by",
}


def build_llm(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    context_window: int | None = None,
    supports_function_calling: bool | None = None,
    supports_chat: bool | None = None,
):
    config = resolve_llm_config(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        context_window=context_window,
        supports_function_calling=supports_function_calling,
        supports_chat=supports_chat,
    )

    explicit_metadata_required = any(
        value is not None
        for value in [config.base_url, config.context_window, config.supports_function_calling, config.supports_chat]
    ) and config.provider != "openai"

    if explicit_metadata_required:
        llm = OpenAICompatibleLLM(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
            api_base=config.base_url,
            context_window=config.context_window or 32000,
            supports_chat=config.supports_chat if config.supports_chat is not None else True,
            supports_function_calling=(
                config.supports_function_calling if config.supports_function_calling is not None else True
            ),
            pydantic_program_mode=PydanticProgramMode.LLM,
        )
    else:
        llm = LlamaIndexOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
            api_base=config.base_url,
        )

    return llm, {
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
    }


class JSONModeStructuredLLM:
    def __init__(
        self,
        *,
        output_schema,
        api_key: str,
        model: str,
        base_url: str | None,
        temperature: float,
    ) -> None:
        self.output_schema = output_schema
        self.model = model
        self.temperature = temperature
        self.client = OpenAIClient(api_key=api_key, base_url=base_url)

    def complete(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Return valid json only that matches the requested schema."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        content = self._extract_content(response)
        try:
            payload = self._normalize_payload(json.loads(content))
            validated = self.output_schema.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"本地 schema 校验失败：{exc}") from exc
        return SimpleNamespace(raw=validated, text=content)

    @staticmethod
    def _extract_content(response) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("结构化大模型未返回 choices")

        message = getattr(choices[0], "message", None)
        if message is None:
            raise ValueError("结构化大模型未返回 message")

        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif hasattr(item, "text"):
                    text_parts.append(getattr(item, "text"))
            merged = "".join(part for part in text_parts if part)
            if merged.strip():
                return merged

        raise ValueError("结构化大模型响应中缺少可解析的 JSON 文本")

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        candidates = []
        for item in payload.get("candidates", []):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            if "item_type" not in normalized and "type" in normalized:
                normalized["item_type"] = normalized["type"]
            if "canonical_name" not in normalized and "name" in normalized:
                normalized["canonical_name"] = normalized["name"]
            item_type = normalized.get("item_type")
            if item_type not in _VALID_ITEM_TYPES:
                normalized["item_type"] = "entity"
            normalized.setdefault("category", _DEFAULT_CATEGORIES[normalized["item_type"]])
            candidates.append(normalized)

        relations = []
        for item in payload.get("relations", []):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            if "source_name" not in normalized and "source" in normalized:
                normalized["source_name"] = normalized["source"]
            if "source_name" not in normalized and "from" in normalized:
                normalized["source_name"] = normalized["from"]
            if "source_name" not in normalized and "head" in normalized:
                normalized["source_name"] = normalized["head"]
            if "target_name" not in normalized and "target" in normalized:
                normalized["target_name"] = normalized["target"]
            if "target_name" not in normalized and "to" in normalized:
                normalized["target_name"] = normalized["to"]
            if "target_name" not in normalized and "tail" in normalized:
                normalized["target_name"] = normalized["tail"]
            if normalized.get("relation_type") not in _VALID_RELATION_TYPES:
                continue
            relations.append(normalized)

        normalized_payload = dict(payload)
        normalized_payload["candidates"] = candidates
        normalized_payload["relations"] = relations
        return normalized_payload


def build_structured_llm(*, output_schema, **kwargs) -> tuple[Any, dict[str, str | None]]:
    config = resolve_llm_config(**kwargs)
    return (
        JSONModeStructuredLLM(
            output_schema=output_schema,
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
        ),
        {
            "provider": config.provider,
            "model": config.model,
            "base_url": config.base_url,
        },
    )
