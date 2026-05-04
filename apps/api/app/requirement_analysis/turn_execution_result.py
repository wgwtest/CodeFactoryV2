from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurnExecutionResult:
    turn: dict
    state_patch: dict
    provider_logs: list[dict]
