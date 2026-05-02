from __future__ import annotations

from typing import Any

from app.db.models.requirements import RequirementAnalysisSession
from app.requirement_analysis.models import RequirementAnalysisTurnCreate


class RequirementAnalysisTurnEngine:
    def __init__(self, owner: Any) -> None:
        self.owner = owner

    def add_turn(self, session: RequirementAnalysisSession, payload: RequirementAnalysisTurnCreate) -> dict:
        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        turn_id = f"turn-{len(turns) + 1:04d}"
        user_input = payload.user_input.strip()
        last_quick_options = self.owner._normalize_quick_options(state.get("last_quick_options"))
        normalized = self.owner._normalize_input(user_input, quick_options=last_quick_options)
        now = self.owner._now()
        facts = list(state.get("facts", []))
        questions = list(state.get("questions", []))
        patches = list(state.get("patches", []))
        spec_tree = list(state.get("spec_tree") or self.owner._new_spec_tree(session.template_id))
        active_spec_node_id = str(state.get("active_spec_node_id") or self.owner._first_open_spec_node_id(spec_tree) or "")
        orchestrator = self.owner._orchestrator(session.orchestrator_id)
        model_output = self.owner._run_orchestrator(
            orchestrator=orchestrator,
            session=session,
            user_input=user_input,
            normalized=normalized,
        )
        previous_interaction = self.owner._previous_interaction(
            state.get("next_interaction"),
            last_quick_options=last_quick_options,
        )
        input_relation = self.owner._classify_input_relation(
            previous_interaction,
            normalized,
            last_quick_options=last_quick_options,
        )
        model_output = self.owner._normalize_turn_model_output(model_output, session=session)
        projection_spec_node_id = self.owner._select_projection_spec_node_id(spec_tree, model_output, active_spec_node_id)
        projection_spec_node = self.owner._active_spec_node_context(spec_tree, projection_spec_node_id)
        model_output = self.owner._ensure_patch_target_section(
            model_output=model_output,
            current_spec_node=projection_spec_node,
            session=session,
        )
        next_open_before_update = self.owner._first_open_spec_node_id(spec_tree)
        decision_trace_seed = self.owner._decision_trace_seed(
            projection_spec_node=projection_spec_node,
            normalized=normalized,
            next_open_before_update=next_open_before_update,
            orchestrator=orchestrator,
        )
        structured_update = self.owner._build_structured_summary_update(
            model_output=model_output,
            normalized=normalized,
            questions=questions,
            facts=facts,
            patches=patches,
            target_spec_node=projection_spec_node,
            turn_id=turn_id,
            session=session,
        )
        spec_update = self.owner._update_spec_tree(
            spec_tree=spec_tree,
            active_node_id=projection_spec_node_id,
            answer_summary=structured_update["answer_summary"],
            turn_id=turn_id,
        )
        next_spec_node = self.owner._active_spec_node_context(spec_update["spec_tree"], spec_update["active_spec_node_id"])
        model_output = self.owner._align_model_output_to_next_node(
            model_output=model_output,
            next_spec_node=next_spec_node,
            current_spec_node=projection_spec_node,
            session=session,
        )
        structured_update["questions"] = self.owner._ensure_next_open_question(
            questions=structured_update["questions"],
            next_question=model_output["next_question"],
            next_spec_node=next_spec_node,
            turn_id=turn_id,
        )
        affected_spec_nodes = self.owner._affected_spec_nodes(
            spec_tree=spec_update["spec_tree"],
            node_ids=spec_update["closed_node_ids"] or [projection_spec_node_id],
        )
        state_changes = self.owner._state_changes(
            previous_questions=questions,
            updated_questions=structured_update["questions"],
            closed_spec_node_ids=spec_update["closed_node_ids"],
            next_active_spec_node_id=spec_update["active_spec_node_id"],
        )
        spec_execution = self.owner._spec_execution(
            model_output=model_output,
            affected_spec_nodes=affected_spec_nodes,
            state_changes=state_changes,
        )
        post_update_review = self.owner._post_update_review(
            previous_interaction=previous_interaction,
            next_spec_node=next_spec_node,
            closed_spec_node_ids=spec_update["closed_node_ids"],
        )
        closure_decision = self.owner._closure_decision(
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closed_spec_node_ids=spec_update["closed_node_ids"],
        )
        next_interaction = self.owner._next_interaction(
            next_spec_node=next_spec_node,
            model_output=model_output,
            turn_index=len(turns) + 1,
        )
        decision_trace = self.owner._decision_trace(
            previous_interaction=previous_interaction,
            input_relation=input_relation,
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closure_decision=closure_decision,
            next_interaction=next_interaction,
            seed=decision_trace_seed,
        )

        turn = {
            "turn_id": turn_id,
            "session_id": session.id,
            "user_input": user_input,
            "previous_interaction": previous_interaction,
            "normalized_input": normalized,
            "input_relation": input_relation,
            "spec_execution": spec_execution,
            "post_update_review": post_update_review,
            "closure_decision": closure_decision,
            "next_interaction": next_interaction,
            "decision_trace": decision_trace,
            "confidence": model_output["confidence"],
            "service_steps": self.owner._service_steps(),
            "raw_model_response": model_output["raw_model_response"],
            "created_at": now,
        }
        turns.append(turn)

        state["turns"] = turns
        state["messages"] = [
            *list(state.get("messages", [])),
            {"id": f"msg-{len(turns) * 2:04d}", "role": "user", "content": user_input, "turn_id": turn_id, "created_at": now},
            {
                "id": f"msg-{len(turns) * 2 + 1:04d}",
                "role": "assistant",
                "content": spec_execution["assistant_message"],
                "turn_id": turn_id,
                "created_at": now,
            },
        ]
        state["confirmed_facts"] = self.owner._append_unique(
            list(state.get("confirmed_facts", [])), model_output["confirmed_facts_delta"]
        )
        state["open_questions"] = self.owner._append_unique(
            list(state.get("open_questions", [])), model_output["open_questions_delta"]
        )
        state["document_patch"] = model_output["document_patch"]
        state["questions"] = structured_update["questions"]
        state["facts"] = structured_update["facts"]
        state["patches"] = structured_update["patches"]
        state["spec_tree"] = spec_update["spec_tree"]
        state["active_spec_node_id"] = spec_update["active_spec_node_id"]
        state["turn_path"] = [
            *list(state.get("turn_path", [])),
            {
                "turn_id": turn_id,
                "node_id": projection_spec_node_id,
                "question_id": structured_update["source_question_id"],
                "previous_interaction_id": previous_interaction.get("interaction_id"),
                "input_relation": input_relation["relation"],
                "affected_node_ids": [node["node_id"] for node in affected_spec_nodes if node.get("node_id")],
                "next_interaction_id": next_interaction.get("interaction_id"),
                "closed_node_ids": spec_update["closed_node_ids"],
                "answer_summary": structured_update["answer_summary"],
            },
        ]
        state["next_interaction"] = next_interaction
        state["last_quick_options"] = next_interaction.get("options", [])
        state["annotations"] = self.owner._append_unique(list(state.get("annotations", [])), model_output["annotations"])
        state["risks"] = self.owner._append_unique(list(state.get("risks", [])), model_output["risks"])
        state["provider_logs"] = [
            *list(state.get("provider_logs", [])),
            {
                "call_id": f"requirement-analysis-provider-call-{len(turns):04d}",
                "provider_id": session.provider_id,
                "orchestrator_id": orchestrator.orchestrator_id,
                "orchestrator_mode": orchestrator.mode,
                "model": session.model,
                "status": "mocked" if model_output["raw_model_response"].get("mock") else "completed",
                "created_at": now,
            },
        ]
        session.payload = state
        session.status = "waiting_user"
        return turn
