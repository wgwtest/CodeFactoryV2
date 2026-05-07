from __future__ import annotations

from dataclasses import dataclass

from app.orchestrators.plugin_contracts import OrchestratorPluginManifest, OrchestratorRunRequest
from app.requirement_analysis.models import RequirementAnalysisTurnCreate
from app.requirement_analysis.session_snapshot import SessionSnapshot


@dataclass(frozen=True)
class OrchestratorRuntimeInput:
    session_snapshot: SessionSnapshot
    turn_payload: RequirementAnalysisTurnCreate


class OrchestratorRunRequestMapper:
    def build(
        self,
        *,
        request: OrchestratorRunRequest,
        manifest: OrchestratorPluginManifest,
    ) -> OrchestratorRuntimeInput:
        session = dict(request.session or {})
        context = dict(request.document_context or {})
        payload = dict(context.get("state") or {})
        payload.setdefault("turns", [])
        payload.setdefault("messages", [])
        payload.setdefault("confirmed_facts", list(context.get("confirmed_facts") or []))
        payload.setdefault("open_questions", [])
        payload.setdefault("document_patch", [])
        payload.setdefault("working_document", dict(context.get("working_document") or {}))
        payload.setdefault("questions", list(context.get("open_questions") or []))
        payload.setdefault("facts", [])
        payload.setdefault("patches", list(context.get("patches") or []))
        payload.setdefault("spec_tree", list(context.get("spec_tree") or []))
        payload.setdefault("active_spec_node_id", str((context.get("active_spec_node") or {}).get("node_id") or ""))
        payload.setdefault("turn_path", [])
        payload.setdefault("next_interaction", dict(request.turn.get("previous_interaction") or {}))
        payload.setdefault("last_quick_options", [])
        payload.setdefault("annotations", [])
        payload.setdefault("risks", [])
        payload.setdefault("provider_logs", [])
        return OrchestratorRuntimeInput(
            session_snapshot=SessionSnapshot(
                session_id=str(session.get("session_id") or ""),
                topic=str(session.get("topic") or ""),
                orchestrator_id=manifest.plugin_id,
                provider_id=str(session.get("provider_id") or "mock"),
                model=str(session.get("model") or "mock-requirement-analysis-v1"),
                template_id=str(session.get("template_id") or "81433号"),
                knowledge_package_id=str(session.get("knowledge_package_id") or ""),
                write_policy=str(session.get("write_policy") or "patch_suggestion_only"),
                status="created",
                payload=payload,
            ),
            turn_payload=RequirementAnalysisTurnCreate(
                user_input=str(request.turn.get("user_input") or ""),
            ),
        )
