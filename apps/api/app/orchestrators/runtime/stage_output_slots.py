from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StageOutputSlots:
    values: dict[str, object] = field(default_factory=dict)
    stage_outputs: dict[str, dict] = field(default_factory=dict)
    stage_adoptions: dict[str, list[str]] = field(default_factory=dict)

    def set_stage_output(self, *, stage_id: str, output: dict, adopted_fields: list[str]) -> None:
        self.stage_outputs[stage_id] = dict(output)
        self.stage_adoptions[stage_id] = list(adopted_fields)

    def set(self, key: str, value: object) -> None:
        self.values[str(key)] = value

    def get(self, key: str, default: object = None) -> object:
        return self.values.get(str(key), default)

    def adopted_fields(self, stage_id: str) -> list[str]:
        return list(self.stage_adoptions.get(stage_id, []))

    def context_values(self, keys: list[str] | tuple[str, ...]) -> dict:
        return {str(key): self.values[str(key)] for key in keys if str(key) in self.values}
