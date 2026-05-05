from __future__ import annotations

from dataclasses import dataclass

from app.requirement_analysis.input_normalizer import InputNormalizer
from app.requirement_analysis.input_relation_classifier import InputRelationClassifier
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.spec_tree_service import RequirementSpecTreeService
from app.requirement_analysis.turn_audit_service import RequirementAnalysisTurnAuditService


@dataclass(frozen=True)
class TurnContext:
    turn_id: str
    turn_index: int
    session_id: str
    topic: str
    template_id: str
    knowledge_package_id: str
    orchestrator_id: str
    provider_id: str
    model: str
    write_policy: str
    user_input: str
    normalized_input: dict
    previous_interaction: dict
    input_relation: dict
    spec_tree: list[dict]
    active_spec_node_id: str
    active_spec_node: dict
    working_document: dict
    questions: list[dict]
    facts: list[dict]
    patches: list[dict]
    last_quick_options: list[dict]


class TurnContextBuilder:
    def __init__(
        self,
        *,
        input_normalizer: InputNormalizer,
        input_relation_classifier: InputRelationClassifier,
        spec_tree_service: RequirementSpecTreeService,
        turn_audit_service: RequirementAnalysisTurnAuditService,
    ) -> None:
        self.input_normalizer = input_normalizer
        self.input_relation_classifier = input_relation_classifier
        self.spec_tree_service = spec_tree_service
        self.turn_audit_service = turn_audit_service

    def build(self, *, session: SessionSnapshot, turn_id: str, user_input: str) -> TurnContext:
        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        last_quick_options = self.input_normalizer.normalize_quick_options(state.get("last_quick_options"))
        normalized = self.input_normalizer.normalize_input(user_input, quick_options=last_quick_options)
        spec_tree = list(
            state.get("spec_tree")
            or self.spec_tree_service.new_spec_tree(session.template_id, orchestrator_id=session.orchestrator_id)
        )
        working_document = dict(state.get("working_document") or {})
        active_spec_node_id = str(
            state.get("active_spec_node_id") or self.spec_tree_service.first_open_spec_node_id(spec_tree) or ""
        )
        previous_interaction = self.turn_audit_service.previous_interaction(
            state.get("next_interaction"),
            last_quick_options=last_quick_options,
        )
        input_relation = self.input_relation_classifier.classify(
            previous_interaction,
            normalized,
            last_quick_options=last_quick_options,
        )
        return TurnContext(
            turn_id=turn_id,
            turn_index=len(turns) + 1,
            session_id=session.session_id,
            topic=session.topic,
            template_id=session.template_id,
            knowledge_package_id=session.knowledge_package_id,
            orchestrator_id=session.orchestrator_id,
            provider_id=session.provider_id,
            model=session.model,
            write_policy=session.write_policy,
            user_input=user_input,
            normalized_input=normalized,
            previous_interaction=previous_interaction,
            input_relation=input_relation,
            spec_tree=spec_tree,
            active_spec_node_id=active_spec_node_id,
            active_spec_node=self.spec_tree_service.active_spec_node_context(spec_tree, active_spec_node_id),
            working_document=working_document,
            questions=list(state.get("questions", [])),
            facts=list(state.get("facts", [])),
            patches=list(state.get("patches", [])),
            last_quick_options=last_quick_options,
        )
