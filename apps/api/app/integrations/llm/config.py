from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(slots=True)
class ResolvedLLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None
    temperature: float
    context_window: int | None
    supports_function_calling: bool | None
    supports_chat: bool | None


_PROVIDER_DEFAULTS: dict[str, dict[str, object]] = {
    "openai": {
        "base_url": None,
        "model": None,
        "context_window": None,
        "supports_function_calling": None,
        "supports_chat": None,
    },
    "openai_compatible": {
        "base_url": None,
        "model": None,
        "context_window": 32000,
        "supports_function_calling": True,
        "supports_chat": True,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "context_window": 64000,
        "supports_function_calling": True,
        "supports_chat": True,
    },
}


def resolve_llm_config(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    context_window: int | None = None,
    supports_function_calling: bool | None = None,
    supports_chat: bool | None = None,
) -> ResolvedLLMConfig:
    resolved_provider = (provider or settings.llm_provider or "openai").strip().lower()
    defaults = _PROVIDER_DEFAULTS.get(resolved_provider, _PROVIDER_DEFAULTS["openai_compatible"])

    resolved_api_key = api_key or settings.llm_api_key or settings.openai_api_key
    if not resolved_api_key:
        raise ValueError("LLM api key is not configured")

    resolved_model = model or settings.llm_model or settings.openai_model or defaults["model"]
    if not resolved_model:
        raise ValueError("LLM model is not configured")

    resolved_base_url = base_url if base_url is not None else settings.llm_base_url
    if resolved_base_url is None:
        resolved_base_url = defaults["base_url"]

    resolved_temperature = temperature if temperature is not None else settings.llm_temperature
    resolved_context_window = (
        context_window
        if context_window is not None
        else settings.llm_context_window if settings.llm_context_window is not None else defaults["context_window"]
    )
    resolved_supports_function_calling = (
        supports_function_calling
        if supports_function_calling is not None
        else settings.llm_supports_function_calling
        if settings.llm_supports_function_calling is not None
        else defaults["supports_function_calling"]
    )
    resolved_supports_chat = (
        supports_chat
        if supports_chat is not None
        else settings.llm_supports_chat
        if settings.llm_supports_chat is not None
        else defaults["supports_chat"]
    )

    return ResolvedLLMConfig(
        provider=resolved_provider,
        api_key=resolved_api_key,
        model=resolved_model,
        base_url=resolved_base_url,
        temperature=resolved_temperature,
        context_window=resolved_context_window,
        supports_function_calling=resolved_supports_function_calling,
        supports_chat=resolved_supports_chat,
    )
