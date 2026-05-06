from __future__ import annotations

from typing import Protocol

from app.orchestrators.plugin_contracts import OrchestratorRunRequest, OrchestratorRunResult


class OrchestratorPluginAdapter(Protocol):
    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        ...
