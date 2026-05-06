from __future__ import annotations

from app.orchestrators.orchestrator_id_mapper import local_package_id_for_orchestrator
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest, OrchestratorRunResult
from app.orchestrators.runner_host import OrchestratorRunnerHost


class LocalXGOrchestratorPluginAdapter:
    def __init__(self, *, manifest: OrchestratorPluginManifest, runner_host: OrchestratorRunnerHost | None = None) -> None:
        self.manifest = manifest
        self.runner_host = runner_host or OrchestratorRunnerHost()

    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        package_id = local_package_id_for_orchestrator(self.manifest.plugin_id)
        output = self.runner_host.execute_local_runner(
            package_id,
            context={
                "session": request.session,
                "user_input": request.turn["user_input"],
                "normalized": request.turn["normalized_input"],
                "active_spec_node": request.document_context.get("active_spec_node") or {},
                "state": {
                    "working_document": request.document_context.get("working_document") or {},
                    "spec_tree": request.document_context.get("spec_tree") or [],
                    "confirmed_facts": request.document_context.get("confirmed_facts") or [],
                    "open_questions": request.document_context.get("open_questions") or [],
                    "patches": request.document_context.get("patches") or [],
                },
            },
        )
        document_patch = list(output.get("document_patch") or [])
        raw_model_response = dict(output.get("raw_model_response") or {})
        return OrchestratorRunResult(
            contract_version=request.contract_version,
            plugin={
                "plugin_id": self.manifest.plugin_id,
                "plugin_type": self.manifest.plugin_type,
                "observability_level": self.manifest.observability_level,
            },
            final_output={
                "filled_document_text": "",
                "document_patch": document_patch,
                "changed_sections": [
                    str(plan.get("template_clause_id") or "")
                    for plan in list(output.get("target_anchor_plan") or [])
                    if str(plan.get("template_clause_id") or "").strip()
                ],
                "completion_status": "partial",
                "confidence": str(output.get("confidence") or "medium"),
            },
            interaction_output={
                "assistant_message": str(output.get("assistant_message") or ""),
                "next_question": str(output.get("next_question") or ""),
                "quick_options": list(output.get("quick_options") or []),
                "suggested_focus": dict(output.get("next_suggestion") or {}),
            },
            process_output={
                "stage_results": [],
                "stage_audits": [
                    {
                        "stage_id": "run",
                        "stage_kind": "local_runner",
                        "status": "completed",
                        "summary": "本地 XG 组织器 runner 已返回可观测插件结果。",
                    }
                ],
                "decision_trace": list(output.get("annotations") or []),
                "provider_logs": [],
                "review_after_apply_result": {},
                "annotations": list(output.get("annotations") or []),
                "risks": list(output.get("risks") or []),
            },
            state_output={
                "confirmed_facts_delta": list(output.get("confirmed_facts_delta") or []),
                "open_questions_delta": list(output.get("open_questions_delta") or []),
                "spec_tree_update": {},
                "working_document_update": {},
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": output,
                "raw_model_response": raw_model_response,
                "raw_workflow_trace": {},
            },
        )
