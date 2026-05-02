from __future__ import annotations


PROVIDER_DEFINITIONS = [
    {"provider_id": "mock", "name": "Mock Provider"},
    {"provider_id": "deepseek", "name": "DeepSeek"},
    {"provider_id": "openai", "name": "OpenAI"},
]


def supported_provider_ids() -> set[str]:
    return {item["provider_id"] for item in PROVIDER_DEFINITIONS}
