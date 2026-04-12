from __future__ import annotations

from pydantic import PrivateAttr

from llama_index.core.base.llms.types import LLMMetadata, MessageRole
from llama_index.llms.openai import OpenAI


class OpenAICompatibleLLM(OpenAI):
    _explicit_metadata: LLMMetadata = PrivateAttr()

    def __init__(
        self,
        *,
        context_window: int,
        supports_chat: bool,
        supports_function_calling: bool,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._explicit_metadata = LLMMetadata(
            context_window=context_window,
            num_output=self.max_tokens or -1,
            is_chat_model=supports_chat,
            is_function_calling_model=supports_function_calling,
            model_name=self.model,
            system_role=MessageRole.SYSTEM,
        )

    @property
    def metadata(self) -> LLMMetadata:
        return self._explicit_metadata
