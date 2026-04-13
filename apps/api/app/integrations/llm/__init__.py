from __future__ import annotations

from typing import Any

from llama_index.core.types import PydanticProgramMode
from llama_index.llms.openai import OpenAI

from app.integrations.llm.config import resolve_llm_config
from app.integrations.llm.openai_compatible import OpenAICompatibleLLM


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
        llm = OpenAI(
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


def build_structured_llm(*, output_schema, **kwargs) -> tuple[Any, dict[str, str | None]]:
    llm, metadata = build_llm(**kwargs)
    return llm.as_structured_llm(output_schema), metadata
