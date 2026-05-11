from __future__ import annotations

from dataclasses import dataclass


DECISION_STATE_SECTIONS = (
    ("confirmed_facts", "一、已确认事实"),
    ("confirmed_decisions", "二、已确认决策"),
    ("tentative_assumptions", "三、暂定假设"),
    ("open_questions", "四、未闭合问题"),
    ("rejected_directions", "五、被否定方向"),
    ("next_focus", "六、下一步交互焦点"),
    ("chapter_projections", "七、章节投影"),
)


@dataclass(frozen=True)
class DecisionStateApplyResult:
    decision_state: dict
    decision_state_delta: dict
    decision_state_change_summary: dict


class DecisionStateService:
    def initialize(
        self,
        *,
        topic: str,
        initial_question: str,
        active_spec_node: dict | None = None,
    ) -> dict:
        return {
            "topic": topic,
            "confirmed_facts": [],
            "confirmed_decisions": [],
            "tentative_assumptions": [],
            "open_questions": [
                self._state_item(
                    item_id="DS-Q-001",
                    content=initial_question,
                    source_turn_id=None,
                    target_section=str((active_spec_node or {}).get("target_section") or ""),
                    status="open",
                )
            ]
            if initial_question
            else [],
            "rejected_directions": [],
            "next_focus": initial_question,
            "chapter_projections": [],
        }

    def apply_delta(
        self,
        *,
        decision_state: dict,
        delta: dict,
        turn_id: str,
        target_spec_node: dict | None = None,
        next_focus: str = "",
    ) -> DecisionStateApplyResult:
        state = self.normalize_state(decision_state)
        normalized_delta = self.normalize_delta(
            delta,
            turn_id=turn_id,
            target_spec_node=target_spec_node,
            next_focus=next_focus,
        )
        before_counts = self._counts(state)
        for key in [
            "confirmed_facts",
            "confirmed_decisions",
            "tentative_assumptions",
            "open_questions",
            "rejected_directions",
            "chapter_projections",
        ]:
            state[key] = self._append_unique_items(
                list(state.get(key, [])),
                list(normalized_delta.get(key, [])),
                prefix=self._prefix_for_section(key),
            )
        if normalized_delta.get("next_focus"):
            state["next_focus"] = str(normalized_delta["next_focus"])
        after_counts = self._counts(state)
        lifecycle_counts = self._apply_question_lifecycle(
            state,
            lifecycle_refs={
                "closed": normalized_delta.get("closed_question_refs", []),
                "deferred": normalized_delta.get("deferred_question_refs", []),
                "superseded": normalized_delta.get("superseded_question_refs", []),
            },
        )
        return DecisionStateApplyResult(
            decision_state=state,
            decision_state_delta=normalized_delta,
            decision_state_change_summary={
                "turn_id": turn_id,
                "added_counts": {
                    key: max(0, after_counts.get(key, 0) - before_counts.get(key, 0))
                    for key in after_counts
                },
                "question_lifecycle_counts": lifecycle_counts,
                "next_focus": state.get("next_focus") or "",
            },
        )

    def defer_open_questions_for_delivery(self, *, decision_state: dict, reason: str) -> DecisionStateApplyResult:
        state = self.normalize_state(decision_state)
        counts = self._defer_current_open_questions(state, reason=reason)
        return DecisionStateApplyResult(
            decision_state=state,
            decision_state_delta={},
            decision_state_change_summary={
                "turn_id": "",
                "added_counts": {key: 0 for key in self._counts(state)},
                "question_lifecycle_counts": counts,
                "next_focus": state.get("next_focus") or "",
            },
        )

    def render_document(self, *, decision_state: dict, session_phase: str) -> dict:
        state = self.normalize_state(decision_state)
        sections: list[dict] = []
        for section_id, heading in DECISION_STATE_SECTIONS:
            if section_id == "next_focus":
                focus = str(state.get("next_focus") or "").strip()
                items = [self._state_item(item_id="DS-FOCUS", content=focus, status="active")] if focus else []
            else:
                items = list(state.get(section_id, []))
            sections.append({"section_id": section_id, "heading": heading, "items": items})
        return {
            "document_id": "decision-state-document",
            "title": "需求分析结构化状态",
            "phase": session_phase,
            "sections": sections,
        }

    def normalize_state(self, value: object) -> dict:
        state = dict(value) if isinstance(value, dict) else {}
        return {
            "topic": str(state.get("topic") or ""),
            "confirmed_facts": self._uniquify_item_ids(
                self._item_list(state.get("confirmed_facts")),
                prefix=self._prefix_for_section("confirmed_facts"),
            ),
            "confirmed_decisions": self._uniquify_item_ids(
                self._item_list(state.get("confirmed_decisions")),
                prefix=self._prefix_for_section("confirmed_decisions"),
            ),
            "tentative_assumptions": self._uniquify_item_ids(
                self._item_list(state.get("tentative_assumptions")),
                prefix=self._prefix_for_section("tentative_assumptions"),
            ),
            "open_questions": self._uniquify_item_ids(
                self._item_list(state.get("open_questions")),
                prefix=self._prefix_for_section("open_questions"),
            ),
            "rejected_directions": self._uniquify_item_ids(
                self._item_list(state.get("rejected_directions")),
                prefix=self._prefix_for_section("rejected_directions"),
            ),
            "next_focus": str(state.get("next_focus") or ""),
            "chapter_projections": self._uniquify_item_ids(
                self._item_list(state.get("chapter_projections")),
                prefix=self._prefix_for_section("chapter_projections"),
            ),
        }

    def normalize_delta(
        self,
        value: object,
        *,
        turn_id: str,
        target_spec_node: dict | None = None,
        next_focus: str = "",
    ) -> dict:
        delta = dict(value) if isinstance(value, dict) else {}
        return {
            "confirmed_facts": self._item_list(
                delta.get("confirmed_facts"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-F",
            ),
            "confirmed_decisions": self._item_list(
                delta.get("confirmed_decisions"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-D",
            ),
            "tentative_assumptions": self._item_list(
                delta.get("tentative_assumptions"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-A",
            ),
            "open_questions": self._item_list(
                delta.get("open_questions"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-Q",
                default_status="open",
            ),
            "rejected_directions": self._item_list(
                delta.get("rejected_directions"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-R",
            ),
            "chapter_projections": self._item_list(
                delta.get("chapter_projections"),
                turn_id=turn_id,
                target_spec_node=target_spec_node,
                prefix="DS-P",
            ),
            "closed_question_refs": self._question_lifecycle_ref_list(delta.get("closed_question_refs"), default_status="closed"),
            "deferred_question_refs": self._question_lifecycle_ref_list(delta.get("deferred_question_refs"), default_status="deferred"),
            "superseded_question_refs": self._question_lifecycle_ref_list(
                delta.get("superseded_question_refs"),
                default_status="superseded",
            ),
            "next_focus": str(delta.get("next_focus") or next_focus or ""),
        }

    def build_delta_from_legacy_output(
        self,
        *,
        model_output: dict,
        turn_id: str,
        target_spec_node: dict | None,
        next_focus: str,
    ) -> dict:
        chapter_projection = []
        for plan in list(model_output.get("target_anchor_plan") or []):
            if not isinstance(plan, dict):
                continue
            heading = str(
                plan.get("display_heading")
                or plan.get("canonical_clause_heading")
                or plan.get("template_clause_id")
                or ""
            ).strip()
            if heading:
                chapter_projection.append(
                    {
                        "content": heading,
                        "source_turn_id": turn_id,
                        "target_section": str((target_spec_node or {}).get("target_section") or ""),
                        "status": "projected",
                    }
                )
        return {
            "confirmed_facts": [
                {"content": str(item), "source_turn_id": turn_id}
                for item in list(model_output.get("confirmed_facts_delta") or [])
                if str(item).strip()
            ],
            "confirmed_decisions": [],
            "tentative_assumptions": [],
            "open_questions": [
                {"content": str(item), "source_turn_id": turn_id, "status": "open"}
                for item in list(model_output.get("open_questions_delta") or [])
                if str(item).strip()
            ],
            "rejected_directions": [],
            "chapter_projections": chapter_projection,
            "next_focus": next_focus,
        }

    @staticmethod
    def _state_item(
        *,
        item_id: str,
        content: str,
        source_turn_id: str | None = None,
        target_section: str = "",
        status: str = "active",
    ) -> dict:
        return {
            "item_id": item_id,
            "content": content,
            "source_turn_id": source_turn_id,
            "target_section": target_section,
            "status": status,
        }

    def _item_list(
        self,
        value: object,
        *,
        turn_id: str | None = None,
        target_spec_node: dict | None = None,
        prefix: str = "DS-I",
        default_status: str = "active",
    ) -> list[dict]:
        if not isinstance(value, list):
            return []
        items: list[dict] = []
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("summary") or item.get("text") or "").strip()
                if not content:
                    continue
                items.append(
                    {
                        "item_id": str(item.get("item_id") or f"{prefix}-{index:03d}"),
                        "content": content,
                        "source_turn_id": item.get("source_turn_id") or turn_id,
                        "target_section": str(
                            item.get("target_section")
                            or (target_spec_node or {}).get("target_section")
                            or ""
                        ),
                        "status": str(item.get("status") or default_status),
                    }
                )
                continue
            content = str(item).strip()
            if content:
                items.append(
                    self._state_item(
                        item_id=f"{prefix}-{index:03d}",
                        content=content,
                        source_turn_id=turn_id,
                        target_section=str((target_spec_node or {}).get("target_section") or ""),
                        status=default_status,
                    )
                )
        return items

    @staticmethod
    def _append_unique_items(current: list[dict], additions: list[dict], *, prefix: str = "DS-I") -> list[dict]:
        result = list(current)
        seen = {str(item.get("content") or "") for item in result if isinstance(item, dict)}
        for item in additions:
            content = str(item.get("content") or "")
            if not content or content in seen:
                continue
            result.append(dict(item))
            seen.add(content)
        return DecisionStateService._uniquify_item_ids(result, prefix=prefix)

    @staticmethod
    def _uniquify_item_ids(items: list[dict], *, prefix: str) -> list[dict]:
        result: list[dict] = []
        used: set[str] = set()
        next_index = 1
        for item in items:
            normalized = dict(item)
            item_id = str(normalized.get("item_id") or "").strip()
            if not item_id or item_id in used:
                item_id = DecisionStateService._next_item_id(prefix=prefix, used=used, start_index=next_index)
            used.add(item_id)
            normalized["item_id"] = item_id
            result.append(normalized)
            next_index = DecisionStateService._next_index_from_id(item_id, default=next_index) + 1
        return result

    @staticmethod
    def _next_item_id(*, prefix: str, used: set[str], start_index: int = 1) -> str:
        index = max(1, start_index)
        while True:
            candidate = f"{prefix}-{index:03d}"
            if candidate not in used:
                return candidate
            index += 1

    @staticmethod
    def _next_index_from_id(item_id: str, *, default: int) -> int:
        try:
            return int(str(item_id).rsplit("-", 1)[-1])
        except ValueError:
            return default

    @staticmethod
    def _prefix_for_section(section_id: str) -> str:
        return {
            "confirmed_facts": "DS-F",
            "confirmed_decisions": "DS-D",
            "tentative_assumptions": "DS-A",
            "open_questions": "DS-Q",
            "rejected_directions": "DS-R",
            "chapter_projections": "DS-P",
        }.get(section_id, "DS-I")

    @staticmethod
    def _question_lifecycle_ref_list(value: object, *, default_status: str) -> list[dict]:
        if not isinstance(value, list):
            return []
        refs: list[dict] = []
        for item in value:
            if isinstance(item, dict):
                item_id = str(item.get("item_id") or "").strip()
                content = str(item.get("content") or "").strip()
                if not item_id and not content:
                    continue
                refs.append(
                    {
                        "item_id": item_id,
                        "content": content,
                        "status": str(item.get("status") or default_status),
                        "reason": str(item.get("reason") or item.get("resolution_reason") or ""),
                    }
                )
                continue
            content = str(item).strip()
            if content:
                refs.append({"item_id": "", "content": content, "status": default_status, "reason": ""})
        return refs

    @staticmethod
    def _apply_question_lifecycle(state: dict, *, lifecycle_refs: dict[str, list[dict]]) -> dict[str, int]:
        counts = {"closed": 0, "deferred": 0, "superseded": 0}
        questions = list(state.get("open_questions") or [])
        for target_status, refs in lifecycle_refs.items():
            for ref in refs:
                matched = DecisionStateService._find_question_ref_match(questions, ref)
                if matched is None:
                    continue
                matched["status"] = str(ref.get("status") or target_status)
                reason = str(ref.get("reason") or "").strip()
                if reason:
                    matched["resolution_reason"] = reason
                counts[target_status] += 1
        state["open_questions"] = questions
        return counts

    @staticmethod
    def _defer_current_open_questions(state: dict, *, reason: str) -> dict[str, int]:
        counts = {"closed": 0, "deferred": 0, "superseded": 0}
        questions = list(state.get("open_questions") or [])
        for question in questions:
            if str(question.get("status") or "open").strip() != "open":
                continue
            question["status"] = "deferred"
            if reason.strip():
                question["resolution_reason"] = reason.strip()
            counts["deferred"] += 1
        state["open_questions"] = questions
        return counts

    @staticmethod
    def _find_question_ref_match(questions: list[dict], ref: dict) -> dict | None:
        item_id = str(ref.get("item_id") or "").strip()
        if item_id:
            for question in questions:
                if str(question.get("item_id") or "").strip() == item_id:
                    return question
        content = str(ref.get("content") or "").strip()
        if content:
            for question in questions:
                if str(question.get("content") or "").strip() == content:
                    return question
        return None

    @staticmethod
    def _counts(state: dict) -> dict[str, int]:
        return {
            key: len(list(state.get(key, [])))
            for key in [
                "confirmed_facts",
                "confirmed_decisions",
                "tentative_assumptions",
                "open_questions",
                "rejected_directions",
                "chapter_projections",
            ]
        }
