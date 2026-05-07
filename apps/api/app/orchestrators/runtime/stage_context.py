from __future__ import annotations

from dataclasses import dataclass

from app.requirement_analysis.chapter_configuration_context_builder import ChapterConfigurationContextBuilder
from app.requirement_analysis.session_snapshot import SessionSnapshot
from app.requirement_analysis.turn_context_builder import TurnContext
from app.requirement_analysis.working_document_service import WorkingDocumentService
from .stage_output_slots import StageOutputSlots


@dataclass(frozen=True)
class StageRuntimeContext:
    stage_id: str
    stage_kind: str
    prompt_id: str
    turn_context: dict
    intent_understanding_result: dict
    target_document_structure: dict
    chapter_configuration_context: dict
    stage_task_definition: dict
    stage_quality_constraints: dict
    template_shape_assessment: dict
    target_anchor_plan: list[dict]
    decision_state: dict
    decision_state_document: dict
    working_document: dict
    working_document_after_apply: dict
    working_document_update: dict
    review_after_apply_result: dict
    recent_revision_fragments: list[str]
    review_target_paths: list[str]

    def to_prompt_context(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "stage_kind": self.stage_kind,
            "prompt_id": self.prompt_id,
            "turn_context": self.turn_context,
            "intent_understanding_result": self.intent_understanding_result,
            "target_document_structure": self.target_document_structure,
            "chapter_configuration_context": self.chapter_configuration_context,
            "stage_task_definition": self.stage_task_definition,
            "stage_quality_constraints": self.stage_quality_constraints,
            "template_shape_assessment": self.template_shape_assessment,
            "target_anchor_plan": list(self.target_anchor_plan),
            "decision_state": self.decision_state,
            "decision_state_document": self.decision_state_document,
            "working_document": self.working_document,
            "working_document_after_apply": self.working_document_after_apply,
            "working_document_update": self.working_document_update,
            "review_after_apply_result": self.review_after_apply_result,
            "recent_revision_fragments": list(self.recent_revision_fragments),
            "review_target_paths": list(self.review_target_paths),
        }


class StageRuntimeContextBuilder:
    def __init__(
        self,
        *,
        working_document_service: WorkingDocumentService | None = None,
        chapter_configuration_context_builder: ChapterConfigurationContextBuilder | None = None,
    ) -> None:
        self.working_document_service = working_document_service or WorkingDocumentService()
        self.chapter_configuration_context_builder = (
            chapter_configuration_context_builder or ChapterConfigurationContextBuilder()
        )

    def build(
        self,
        *,
        session: SessionSnapshot,
        context: TurnContext,
        stage: dict,
        stage_output_slots: StageOutputSlots | None = None,
        intent_understanding_result: dict | None = None,
        target_document_structure: dict | None = None,
        stage_task_definition: dict | None = None,
        stage_quality_constraints: dict | None = None,
        template_shape_assessment: dict | None = None,
        target_anchor_plan: list[dict] | None = None,
        decision_state: dict | None = None,
        decision_state_document: dict | None = None,
        working_document: dict | None = None,
        working_document_after_apply: dict | None = None,
        working_document_update: dict | None = None,
        review_after_apply_result: dict | None = None,
    ) -> StageRuntimeContext:
        state = dict(session.payload or {})
        slot_values = (stage_output_slots or StageOutputSlots()).context_values(list(stage.get("input_sources") or []))
        if intent_understanding_result is None and isinstance(slot_values.get("intent_understanding_result"), dict):
            intent_understanding_result = dict(slot_values["intent_understanding_result"])
        if target_document_structure is None and isinstance(slot_values.get("target_document_structure"), dict):
            target_document_structure = dict(slot_values["target_document_structure"])
        if stage_task_definition is None and isinstance(slot_values.get("stage_task_definition"), dict):
            stage_task_definition = dict(slot_values["stage_task_definition"])
        if stage_quality_constraints is None and isinstance(slot_values.get("stage_quality_constraints"), dict):
            stage_quality_constraints = dict(slot_values["stage_quality_constraints"])
        if template_shape_assessment is None and isinstance(slot_values.get("template_shape_assessment"), dict):
            template_shape_assessment = dict(slot_values["template_shape_assessment"])
        if target_anchor_plan is None and isinstance(slot_values.get("target_anchor_plan"), list):
            target_anchor_plan = list(slot_values["target_anchor_plan"])
        if decision_state is None and isinstance(slot_values.get("decision_state"), dict):
            decision_state = dict(slot_values["decision_state"])
        if decision_state_document is None and isinstance(slot_values.get("decision_state_document"), dict):
            decision_state_document = dict(slot_values["decision_state_document"])
        if working_document is None and isinstance(slot_values.get("working_document"), dict):
            working_document = dict(slot_values["working_document"])
        if working_document_after_apply is None and isinstance(slot_values.get("working_document_after_apply"), dict):
            working_document_after_apply = dict(slot_values["working_document_after_apply"])
        if working_document_update is None and isinstance(slot_values.get("working_document_update"), dict):
            working_document_update = dict(slot_values["working_document_update"])
        if review_after_apply_result is None and isinstance(slot_values.get("review_after_apply_result"), dict):
            review_after_apply_result = dict(slot_values["review_after_apply_result"])
        working_doc = dict(
            working_document
            or context.working_document
            or state.get("working_document")
            or self.working_document_service.initialize(topic=session.topic, template_id=session.template_id)
        )
        review_paths = self._review_target_paths(
            target_document_structure=target_document_structure or {},
            active_spec_node=context.active_spec_node,
        )
        return StageRuntimeContext(
            stage_id=str(stage.get("stage_id") or "stage-001"),
            stage_kind=str(stage.get("stage_kind") or ""),
            prompt_id=str(stage.get("prompt_id") or stage.get("stage_id") or "write"),
            turn_context=self._turn_context(session=session, context=context),
            intent_understanding_result=dict(intent_understanding_result or {}),
            target_document_structure=dict(target_document_structure or {}),
            chapter_configuration_context=self.chapter_configuration_context_builder.build(
                template_id=session.template_id,
                spec_tree=context.spec_tree,
                working_document=working_doc,
            ),
            stage_task_definition=dict(stage_task_definition or {}),
            stage_quality_constraints=dict(stage_quality_constraints or {}),
            template_shape_assessment=dict(template_shape_assessment or {}),
            target_anchor_plan=list(target_anchor_plan or []),
            decision_state=dict(decision_state if decision_state is not None else state.get("decision_state") or {}),
            decision_state_document=dict(
                decision_state_document if decision_state_document is not None else state.get("decision_state_document") or {}
            ),
            working_document=working_doc,
            working_document_after_apply=dict(working_document_after_apply or {}),
            working_document_update=dict(working_document_update or {}),
            review_after_apply_result=dict(review_after_apply_result or {}),
            recent_revision_fragments=self._recent_revision_fragments(working_doc),
            review_target_paths=review_paths,
        )

    @staticmethod
    def _turn_context(*, session: SessionSnapshot, context: TurnContext) -> dict:
        return {
            "turn_id": context.turn_id,
            "turn_index": context.turn_index,
            "session_id": context.session_id,
            "topic": session.topic,
            "template_id": session.template_id,
            "knowledge_package_id": session.knowledge_package_id,
            "orchestrator_id": session.orchestrator_id,
            "provider_id": session.provider_id,
            "model": session.model,
            "write_policy": session.write_policy,
            "user_input": context.user_input,
            "normalized_input": context.normalized_input,
            "previous_interaction": context.previous_interaction,
            "input_relation": context.input_relation,
            "active_spec_node_id": context.active_spec_node_id,
            "active_spec_node": context.active_spec_node,
            "last_quick_options": context.last_quick_options,
            "questions": context.questions,
            "facts": context.facts,
            "patches": context.patches,
            "decision_state": dict((session.payload or {}).get("decision_state") or {}),
            "session_phase": str((session.payload or {}).get("session_phase") or "exploration_convergence"),
        }

    @staticmethod
    def _recent_revision_fragments(working_document: dict) -> list[str]:
        fragments = []
        for fragment in list(working_document.get("revision_fragments", []))[-5:]:
            if isinstance(fragment, dict) and fragment.get("fragment_id"):
                fragments.append(str(fragment["fragment_id"]))
        return fragments

    @staticmethod
    def _review_target_paths(*, target_document_structure: dict, active_spec_node: dict) -> list[str]:
        candidates = target_document_structure.get("target_anchor_paths") or target_document_structure.get("target_sections")
        if isinstance(candidates, list):
            paths = [str(item) for item in candidates if str(item).strip()]
            if paths:
                return paths
        target = str(active_spec_node.get("target_section") or "").strip()
        return [target] if target else []
