from __future__ import annotations

from dataclasses import dataclass

from app.db.models.requirements import RequirementAnalysisSession


@dataclass(frozen=True)
class ArtifactUpdateResult:
    questions: list[dict]
    facts: list[dict]
    patches: list[dict]
    answer_summary: str
    source_question_id: str | None

    def to_dict(self) -> dict:
        return {
            "questions": self.questions,
            "facts": self.facts,
            "patches": self.patches,
            "answer_summary": self.answer_summary,
            "source_question_id": self.source_question_id,
        }


class RequirementAnalysisSummaryArtifactService:
    def build_structured_summary_update(
        self,
        *,
        model_output: dict,
        normalized: dict,
        questions: list[dict],
        facts: list[dict],
        patches: list[dict],
        target_spec_node: dict,
        turn_id: str,
        session: RequirementAnalysisSession,
    ) -> dict:
        plan_by_id = {
            str(plan.get("plan_id") or "").strip(): dict(plan)
            for plan in list(model_output.get("target_anchor_plan") or [])
            if isinstance(plan, dict) and str(plan.get("plan_id") or "").strip()
        }
        current_target_section = self.target_section_from_plan(
            model_output["document_patch"][0],
            plan_by_id=plan_by_id,
        ) if model_output["document_patch"] else None
        source_question = self.resolve_answering_question(
            questions,
            target_section=current_target_section,
            target_spec_node=target_spec_node,
            turn_id=turn_id,
        )
        source_question_id = source_question.get("question_id") if source_question else None
        new_fact_ids: list[str] = []
        for fact_content in model_output["confirmed_facts_delta"]:
            existing = next((fact for fact in facts if fact.get("content") == fact_content), None)
            if existing:
                new_fact_ids.append(existing["fact_id"])
                continue
            fact_id = f"F-{len(facts) + 1:03d}"
            fact_target_section = (
                str(source_question.get("target_section") or "")
                if source_question
                else (current_target_section or (target_spec_node.get("target_section") if target_spec_node else None))
            )
            facts.append(
                {
                    "fact_id": fact_id,
                    "content": fact_content,
                    "source_turn_id": turn_id,
                    "source_question_ids": [source_question_id] if source_question_id else [],
                    "target_section": fact_target_section,
                }
            )
            new_fact_ids.append(fact_id)

        if source_question:
            source_index = next(
                index for index, question in enumerate(questions) if question.get("question_id") == source_question_id
            )
            questions[source_index] = {
                **questions[source_index],
                "status": "confirmed",
                "resolution_fact_ids": self.append_unique(
                    list(questions[source_index].get("resolution_fact_ids", [])), new_fact_ids
                ),
            }

        for open_question in model_output["open_questions_delta"]:
            target_section = current_target_section or target_spec_node.get("target_section") or "未绑定模板章节"
            if any(question.get("content") == open_question for question in questions):
                continue
            if source_question and self.is_same_question_content(open_question, str(source_question.get("content") or "")):
                continue
            questions.append(
                {
                    "question_id": f"Q-{len(questions) + 1:03d}",
                    "content": open_question,
                    "status": "open",
                    "target_section": target_section,
                    "source_turn_id": turn_id,
                    "resolution_fact_ids": [],
                }
            )

        for patch in model_output["document_patch"]:
            patch_id = f"P-{len(patches) + 1:03d}"
            target_section = self.target_section_from_plan(patch, plan_by_id=plan_by_id)
            patches.append(
                {
                    "patch_id": patch_id,
                    "target_section": target_section,
                    "plan_ref": patch.get("plan_ref") or "",
                    "operation": patch.get("operation") or "append_or_update",
                    "content": patch.get("content") or "",
                    "write_policy": patch.get("write_policy") or session.write_policy,
                    "status": "proposed",
                    "source_turn_id": turn_id,
                    "source_fact_ids": new_fact_ids,
                    "source_question_ids": [source_question_id] if source_question_id else [],
                }
            )

        answer_summary = model_output["confirmed_facts_delta"][0] if model_output["confirmed_facts_delta"] else normalized["semantic"]
        return ArtifactUpdateResult(
            questions=questions,
            facts=facts,
            patches=patches,
            answer_summary=answer_summary,
            source_question_id=source_question_id,
        )

    def resolve_answering_question(
        self,
        questions: list[dict],
        *,
        target_section: str | None,
        target_spec_node: dict,
        turn_id: str,
    ) -> dict | None:
        if target_section:
            for question in questions:
                if question.get("status") == "open" and question.get("target_section") == target_section:
                    return question
            target_spec_section = str(target_spec_node.get("target_section") or "").strip()
            if target_spec_section:
                for question in questions:
                    if question.get("status") == "open" and str(question.get("target_section") or "").strip() == target_spec_section:
                        return question
            if target_spec_node.get("node_id"):
                question = {
                    "question_id": f"Q-{len(questions) + 1:03d}",
                    "content": self.suggestion_content_for_node(target_spec_node),
                    "status": "open",
                    "target_section": target_section,
                    "source_turn_id": turn_id,
                    "resolution_fact_ids": [],
                }
                questions.append(question)
                return question
        for question in questions:
            if question.get("status") == "open":
                return question
        return questions[-1] if questions else None

    @staticmethod
    def target_section_from_plan(patch: dict, *, plan_by_id: dict[str, dict]) -> str:
        plan = plan_by_id.get(str(patch.get("plan_ref") or "").strip())
        if not plan:
            return "未绑定模板章节"
        return str(
            plan.get("display_heading")
            or plan.get("canonical_clause_heading")
            or plan.get("template_clause_id")
            or "未绑定模板章节"
        )

    @staticmethod
    def suggestion_content_for_node(node: dict | None) -> str:
        if node is None:
            return "请直接描述你希望形成的需求规格说明内容。"
        return f"可以补齐：{node.get('question') or node.get('title')}"

    @staticmethod
    def append_unique(current: list[str], additions: list[str]) -> list[str]:
        result = list(current)
        for item in additions:
            if item not in result:
                result.append(item)
        return result

    @staticmethod
    def is_same_question_content(candidate: str, existing: str) -> bool:
        normalized_candidate = candidate.replace("可以补齐：", "").strip()
        normalized_existing = existing.replace("可以补齐：", "").strip()
        return bool(normalized_candidate) and (
            normalized_candidate == normalized_existing
            or normalized_candidate in normalized_existing
            or normalized_existing in normalized_candidate
        )
