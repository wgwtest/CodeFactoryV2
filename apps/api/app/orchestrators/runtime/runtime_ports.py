from __future__ import annotations

from typing import Protocol

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest


class OrchestratorRuntimeHostPort(Protocol):
    def build_policy_interpreted_runtime(self): ...

    def run_policy_interpreted(
        self,
        request: OrchestratorRunRequest,
        manifest: OrchestratorPluginManifest,
    ): ...

    def build_local_xg_turn_runtime(
        self,
        *,
        runtime_cls,
        turn_strategy_service_cls,
        turn_stage_planner_cls,
        turn_stage_executor_cls,
        turn_stage_reducer_cls,
    ): ...
