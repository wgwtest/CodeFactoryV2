from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.package_loader import LoadedOrchestratorPackage


@dataclass(frozen=True)
class StagePrompt:
    prompt_id: str
    base_contract_text: str
    system_prompt_text: str
    user_prompt_text: str

    @property
    def stage_prompt_text(self) -> str:
        return "\n\n".join(
            text
            for text in [self.system_prompt_text.strip(), self.user_prompt_text.strip()]
            if text
        )


class StagePromptResolver:
    def resolve(self, loaded: LoadedOrchestratorPackage, *, stage: dict) -> StagePrompt:
        prompt_id = str(stage.get("prompt_id") or stage.get("stage_id") or "write")
        system_prompt = loaded.stage_prompts.get(f"{prompt_id}.system", "")
        user_prompt = loaded.stage_prompts.get(f"{prompt_id}.user", "")
        if not system_prompt and not user_prompt:
            system_prompt = loaded.prompt_text
        return StagePrompt(
            prompt_id=prompt_id,
            base_contract_text=loaded.stage_prompts.get("base_contract", ""),
            system_prompt_text=system_prompt,
            user_prompt_text=user_prompt,
        )
