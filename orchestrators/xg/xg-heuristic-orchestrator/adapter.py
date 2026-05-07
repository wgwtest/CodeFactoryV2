from __future__ import annotations

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest, OrchestratorRunResult


class LocalXGOrchestratorPluginAdapter:
    def __init__(self, *, manifest: OrchestratorPluginManifest, package=None, runtime_host=None) -> None:
        self.manifest = manifest
        self.runtime_host = runtime_host

    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        turn_result = self._run_policy_interpreted(request)
        return OrchestratorRunResult(
            contract_version=request.contract_version,
            plugin={
                "plugin_id": self.manifest.plugin_id,
                "plugin_type": self.manifest.plugin_type,
                "observability_level": self.manifest.observability_level,
            },
            final_output={
                "filled_document_text": "",
                "document_patch": list(turn_result.turn.get("spec_execution", {}).get("document_patch") or []),
                "changed_sections": [
                    str(node.get("target_section") or node.get("node_id") or "")
                    for node in list(turn_result.turn.get("spec_execution", {}).get("affected_spec_nodes") or [])
                    if str(node.get("target_section") or node.get("node_id") or "").strip()
                ],
                "completion_status": "partial",
                "confidence": str(turn_result.turn.get("confidence") or "medium"),
            },
            interaction_output={
                "assistant_message": str(turn_result.turn.get("spec_execution", {}).get("assistant_message") or ""),
                "next_question": str(turn_result.turn.get("next_interaction", {}).get("prompt") or ""),
                "quick_options": list(turn_result.turn.get("next_interaction", {}).get("options") or []),
                "suggested_focus": dict(turn_result.turn.get("next_interaction") or {}),
            },
            process_output={
                "stage_results": [],
                "stage_audits": list(turn_result.turn.get("stage_audits") or []),
                "decision_trace": list(turn_result.turn.get("decision_trace") or []),
                "provider_logs": list(turn_result.provider_logs),
                "review_after_apply_result": dict(turn_result.turn.get("review_after_apply_result") or {}),
                "annotations": list(turn_result.state_patch.get("annotations") or []),
                "risks": list(turn_result.state_patch.get("risks") or []),
            },
            state_output={
                "confirmed_facts_delta": list(turn_result.turn.get("spec_execution", {}).get("confirmed_facts") or []),
                "open_questions_delta": list(turn_result.turn.get("next_interaction_plan", {}).get("quick_options") or []),
                "spec_tree_update": {},
                "working_document_update": dict(turn_result.turn.get("spec_execution", {}).get("working_document_update") or {}),
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": {"turn": turn_result.turn},
                "raw_model_response": dict(turn_result.turn.get("raw_model_response") or {}),
                "raw_workflow_trace": {},
                "turn_execution_result": turn_result,
            },
        )

    def _run_policy_interpreted(self, request: OrchestratorRunRequest):
        if self.runtime_host is None:
            raise RuntimeError("runtime_host_missing")
        return self.runtime_host.run_policy_interpreted(request, self.manifest)
