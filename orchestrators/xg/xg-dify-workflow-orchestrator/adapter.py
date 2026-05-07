from __future__ import annotations

from app.orchestrators.adapters.plugin_turn_result_materializer import PluginTurnResultMaterializer
from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest, OrchestratorRunResult


class DifyWorkflowOrchestratorPluginAdapter:
    def __init__(self, *, manifest: OrchestratorPluginManifest) -> None:
        self.manifest = manifest
        self.materializer = PluginTurnResultMaterializer()

    def run(self, request: OrchestratorRunRequest) -> OrchestratorRunResult:
        semantic = str(request.turn.get("normalized_input", {}).get("semantic") or request.turn.get("user_input") or "")
        template_content = str(request.template.get("content") or "# 需求规格说明\n")
        filled_document_text = f"{template_content.rstrip()}\n\n## 本轮补充\n\n{semantic}\n"
        result = OrchestratorRunResult(
            contract_version=request.contract_version,
            plugin={
                "plugin_id": self.manifest.plugin_id,
                "plugin_type": self.manifest.plugin_type,
                "observability_level": self.manifest.observability_level,
            },
            final_output={
                "filled_document_text": filled_document_text,
                "document_patch": [],
                "changed_sections": [],
                "completion_status": "partial",
                "confidence": "medium",
            },
            interaction_output={
                "assistant_message": "Dify workflow 预留插件已生成整篇正文草稿。",
                "next_question": "请继续补充下一项需求规格信息。",
                "quick_options": [],
                "suggested_focus": {},
            },
            process_output={
                "stage_results": [],
                "stage_audits": [],
                "decision_trace": [],
                "provider_logs": [],
                "review_after_apply_result": {},
                "annotations": ["该结果来自 fake Dify workflow 插件，仅验证有限观测合同。"],
                "risks": [],
            },
            state_output={
                "confirmed_facts_delta": [semantic] if semantic else [],
                "open_questions_delta": ["请继续补充下一项需求规格信息。"],
                "spec_tree_update": {},
                "working_document_update": {},
                "turn_path_update": {},
            },
            raw_output={
                "raw_plugin_response": {},
                "raw_model_response": {},
                "raw_workflow_trace": {
                    "fake": True,
                    "workflow_id": "fake-xg-dify-workflow",
                    "run_id": f"fake-{request.turn.get('turn_id', 'turn')}",
                },
            },
        )
        materialized_turn = self.materializer.materialize(request=request, result=result)
        return result.model_copy(
            update={
                "raw_output": {
                    **dict(result.raw_output or {}),
                    "turn_execution_result": materialized_turn,
                }
            }
        )
