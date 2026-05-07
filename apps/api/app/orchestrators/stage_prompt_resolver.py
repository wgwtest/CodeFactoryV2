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
        prompt_id = str(stage.get("prompt_id") or self._prompt_id_from_stage(stage))
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

    @staticmethod
    def _prompt_id_from_stage(stage: dict) -> str:
        stage_kind = str(stage.get("stage_kind") or "")
        stage_id = str(stage.get("stage_id") or "")
        if stage_kind == "intent" or "intent" in stage_id:
            return "intent_understanding"
        if stage_kind == "decision_state_delta" or "decision_state_delta" in stage_id:
            return "decision_state_delta"
        if stage_kind == "next_interaction" or "next_interaction" in stage_id or "planning" in stage_id:
            return "next_interaction_planning"
        if stage_kind == "review" or "review" in stage_id:
            return "review_after_apply"
        return "write"
