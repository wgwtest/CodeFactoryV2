from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.brainstorm.deepseek_client import DeepSeekBrainstormClient
from app.brainstorm.models import BrainstormSessionCreate, BrainstormTurnCreate
from app.brainstorm.orchestrators import OrchestratorPackage, get_orchestrator_registry
from app.config import settings
from app.db.models.requirements import BrainstormSession, RequirementAuthoringTemplate
from app.requirement_authoring.models import default_template_payload

PROVIDER_DEFINITIONS = [
    {"provider_id": "mock", "name": "Mock Provider"},
    {"provider_id": "deepseek", "name": "DeepSeek"},
    {"provider_id": "openai", "name": "OpenAI"},
]

CLAUSE_QUESTIONS = {
    "REQ-1.1": "这个需求规格要描述的软件/系统是什么？请先给出名称、背景领域和编写目的。",
    "REQ-2.1": "软件定位是什么？请说明它面向哪个领域、解决什么问题，以及第一阶段不做什么。",
    "REQ-3.1": "谁使用这个系统？请说明主要用户角色、职责和是否存在协作者或管理员。",
    "REQ-3.2": "核心业务流程是什么？请按用户从开始到得到结果的主线描述。",
    "REQ-3.3": "异常与补偿怎么处理？请说明失败、缺数据、冲突或人工复核时的处理方式。",
    "REQ-4.1": "性能与可靠性有什么要求？请说明响应、批处理、稳定性、安全或部署约束。",
    "REQ-5.1": "验收准则是什么？请说明怎样判断这份需求对应的软件已经可接受。",
}


class BrainstormService:
    def __init__(self, session) -> None:
        self.session = session

    def list_orchestrators(self) -> dict:
        registry = get_orchestrator_registry()
        return {
            "items": [package.to_api() for package in registry.list_packages()],
            "stable_contract": self._stable_contract(),
            "output_protocol": [
                "previous_interaction",
                "input_relation",
                "spec_execution",
                "post_update_review",
                "closure_decision",
                "next_interaction",
                "decision_trace",
            ],
        }

    def list_providers(self) -> dict:
        return {"items": [self._provider(provider["provider_id"]) for provider in PROVIDER_DEFINITIONS]}

    def create_session(self, payload: BrainstormSessionCreate) -> dict:
        orchestrator_id = self._normalize_orchestrator_id(payload.orchestrator_id)
        orchestrator = self._orchestrator(orchestrator_id)
        if payload.provider_id not in {item["provider_id"] for item in PROVIDER_DEFINITIONS}:
            raise ValueError("unsupported provider")
        if payload.provider_id == "deepseek" and not settings.brainstorm_deepseek_api_key:
            raise ValueError("DeepSeek provider is not configured")

        now = self._now()
        model = self._resolve_model(payload.provider_id, payload.model)
        spec_tree = self._new_spec_tree(payload.template_id)
        active_spec_node_id = self._first_open_spec_node_id(spec_tree)
        state = {
            "messages": [
                {
                    "id": "msg-0001",
                    "role": "assistant",
                    "content": (
                        f"我会按{payload.template_id}需求规格模板维护完成度树。"
                        "你可以直接描述、提问、反驳或补充；我会说明本轮更新了哪些规格内容。"
                    ),
                    "created_at": now,
                }
            ],
            "turns": [],
            "confirmed_facts": [],
            "open_questions": [self._suggestion_content_for_node(self._find_spec_node(spec_tree, active_spec_node_id or ""))],
            "document_patch": [],
            "questions": [
                {
                    "question_id": "Q-001",
                    "content": self._suggestion_content_for_node(self._find_spec_node(spec_tree, active_spec_node_id or "")),
                    "status": "open",
                    "target_section": self._find_spec_node(spec_tree, active_spec_node_id or "").get("target_section")
                    if self._find_spec_node(spec_tree, active_spec_node_id or "")
                    else "未绑定模板章节",
                    "source_turn_id": None,
                    "resolution_fact_ids": [],
                }
            ],
            "facts": [],
            "patches": [],
            "spec_tree": spec_tree,
            "active_spec_node_id": active_spec_node_id,
            "turn_path": [],
            "next_interaction": None,
            "last_quick_options": [],
            "annotations": ["Lab 只生成 document_patch 建议，不直接写入正式需求规格草稿。"],
            "risks": [],
            "provider_logs": [],
        }
        session = BrainstormSession(
            topic=payload.topic.strip() or "未命名 Brainstorming 课题",
            orchestrator_id=orchestrator.orchestrator_id,
            provider_id=payload.provider_id,
            model=model,
            template_id=payload.template_id,
            knowledge_package_id=payload.knowledge_package_id,
            write_policy=payload.write_policy,
            status="created",
            payload=state,
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return self._serialize_session(session)

    def get_session(self, session_id: str) -> dict | None:
        session = self.session.get(BrainstormSession, session_id)
        if session is None:
            return None
        return self._serialize_session(session)

    def add_turn(self, session_id: str, payload: BrainstormTurnCreate) -> dict | None:
        session = self.session.get(BrainstormSession, session_id)
        if session is None:
            return None

        state = dict(session.payload or {})
        turns = list(state.get("turns", []))
        turn_id = f"turn-{len(turns) + 1:04d}"
        user_input = payload.user_input.strip()
        last_quick_options = self._normalize_quick_options(state.get("last_quick_options"))
        normalized = self._normalize_input(user_input, quick_options=last_quick_options)
        now = self._now()
        facts = list(state.get("facts", []))
        questions = list(state.get("questions", []))
        patches = list(state.get("patches", []))
        spec_tree = list(state.get("spec_tree") or self._new_spec_tree(session.template_id))
        active_spec_node_id = str(state.get("active_spec_node_id") or self._first_open_spec_node_id(spec_tree) or "")
        orchestrator = self._orchestrator(session.orchestrator_id)
        model_output = self._run_orchestrator(
            orchestrator=orchestrator,
            session=session,
            user_input=user_input,
            normalized=normalized,
        )
        previous_interaction = self._previous_interaction(
            state.get("next_interaction"),
            last_quick_options=last_quick_options,
        )
        input_relation = self._classify_input_relation(
            previous_interaction,
            normalized,
            last_quick_options=last_quick_options,
        )
        model_output = self._normalize_turn_model_output(model_output, session=session)
        projection_spec_node_id = self._select_projection_spec_node_id(spec_tree, model_output, active_spec_node_id)
        projection_spec_node = self._active_spec_node_context(spec_tree, projection_spec_node_id)
        model_output = self._ensure_patch_target_section(
            model_output=model_output,
            current_spec_node=projection_spec_node,
            session=session,
        )
        next_open_before_update = self._first_open_spec_node_id(spec_tree)
        decision_trace_seed = self._decision_trace_seed(
            projection_spec_node=projection_spec_node,
            normalized=normalized,
            next_open_before_update=next_open_before_update,
            orchestrator=orchestrator,
        )
        structured_update = self._build_structured_summary_update(
            model_output=model_output,
            normalized=normalized,
            questions=questions,
            facts=facts,
            patches=patches,
            target_spec_node=projection_spec_node,
            turn_id=turn_id,
            session=session,
        )
        spec_update = self._update_spec_tree(
            spec_tree=spec_tree,
            active_node_id=projection_spec_node_id,
            answer_summary=structured_update["answer_summary"],
            turn_id=turn_id,
        )
        next_spec_node = self._active_spec_node_context(spec_update["spec_tree"], spec_update["active_spec_node_id"])
        model_output = self._align_model_output_to_next_node(
            model_output=model_output,
            next_spec_node=next_spec_node,
            current_spec_node=projection_spec_node,
            session=session,
        )
        structured_update["questions"] = self._ensure_next_open_question(
            questions=structured_update["questions"],
            next_question=model_output["next_question"],
            next_spec_node=next_spec_node,
            turn_id=turn_id,
        )
        affected_spec_nodes = self._affected_spec_nodes(
            spec_tree=spec_update["spec_tree"],
            node_ids=spec_update["closed_node_ids"] or [projection_spec_node_id],
        )
        state_changes = self._state_changes(
            previous_questions=questions,
            updated_questions=structured_update["questions"],
            closed_spec_node_ids=spec_update["closed_node_ids"],
            next_active_spec_node_id=spec_update["active_spec_node_id"],
        )
        spec_execution = self._spec_execution(
            model_output=model_output,
            affected_spec_nodes=affected_spec_nodes,
            state_changes=state_changes,
        )
        post_update_review = self._post_update_review(
            previous_interaction=previous_interaction,
            next_spec_node=next_spec_node,
            closed_spec_node_ids=spec_update["closed_node_ids"],
        )
        closure_decision = self._closure_decision(
            spec_execution=spec_execution,
            post_update_review=post_update_review,
            closed_spec_node_ids=spec_update["closed_node_ids"],
        )
        next_interaction = self._next_interaction(
            next_spec_node=next_spec_node,
            model_output=model_output,
            turn_index=len(turns) + 1,
        )
        decision_trace = self._decision_trace(
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
            "service_steps": self._service_steps(),
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
        state["confirmed_facts"] = self._append_unique(
            list(state.get("confirmed_facts", [])), model_output["confirmed_facts_delta"]
        )
        state["open_questions"] = self._append_unique(
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
        state["annotations"] = self._append_unique(list(state.get("annotations", [])), model_output["annotations"])
        state["risks"] = self._append_unique(list(state.get("risks", [])), model_output["risks"])
        state["provider_logs"] = [
            *list(state.get("provider_logs", [])),
            {
                "call_id": f"brainstorm-provider-call-{len(turns):04d}",
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
        self.session.commit()
        self.session.refresh(session)
        return {"session": self._serialize_session(session), "turn": turn}

    def _serialize_session(self, session: BrainstormSession) -> dict:
        state = dict(session.payload or {})
        return {
            "session_id": session.id,
            "topic": session.topic,
            "status": session.status,
            "orchestrator": self._orchestrator(session.orchestrator_id).to_api(),
            "provider_id": session.provider_id,
            "model": session.model,
            "template_id": session.template_id,
            "knowledge_package_id": session.knowledge_package_id,
            "write_policy": session.write_policy,
            "stable_contract": self._stable_contract(),
            "messages": list(state.get("messages", [])),
            "turns": list(state.get("turns", [])),
            "confirmed_facts": list(state.get("confirmed_facts", [])),
            "open_questions": list(state.get("open_questions", [])),
            "document_patch": list(state.get("document_patch", [])),
            "questions": list(state.get("questions", [])),
            "facts": list(state.get("facts", [])),
            "patches": list(state.get("patches", [])),
            "spec_tree": list(state.get("spec_tree") or self._new_spec_tree(session.template_id)),
            "active_spec_node_id": state.get("active_spec_node_id") or self._first_open_spec_node_id(list(state.get("spec_tree") or [])),
            "turn_path": list(state.get("turn_path", [])),
            "next_interaction": state.get("next_interaction"),
            "annotations": list(state.get("annotations", [])),
            "risks": list(state.get("risks", [])),
            "provider_logs": list(state.get("provider_logs", [])),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def _normalize_orchestrator_id(self, orchestrator_id: str) -> str:
        normalized = orchestrator_id.strip()
        legacy_map = {
            "brainstorming": "xg-brainstorming-orchestrator",
            "rule_based_review": "xg-strong-rule-orchestrator",
        }
        return legacy_map.get(normalized, normalized)

    def _orchestrator(self, orchestrator_id: str) -> OrchestratorPackage:
        return get_orchestrator_registry().require(self._normalize_orchestrator_id(orchestrator_id))

    def _provider(self, provider_id: str) -> dict:
        for provider in PROVIDER_DEFINITIONS:
            if provider["provider_id"] == provider_id:
                status = "active" if provider_id == "mock" else "not_configured"
                if provider_id == "deepseek" and settings.brainstorm_deepseek_api_key:
                    status = "active"
                return {**provider, "status": status}
        raise ValueError("unsupported provider")

    def _resolve_model(self, provider_id: str, model: str) -> str:
        if provider_id == "deepseek" and (not model or model == "mock-brainstorm-v1" or model == "provider-default"):
            return settings.brainstorm_deepseek_model
        return model or "mock-brainstorm-v1"

    def _run_orchestrator(
        self,
        *,
        orchestrator: OrchestratorPackage,
        session: BrainstormSession,
        user_input: str,
        normalized: dict,
    ) -> dict:
        if orchestrator.mode == "local_runner" and orchestrator.orchestrator_id == "xg-strong-rule-orchestrator":
            return self._strong_rule_model_output(session, user_input, normalized, orchestrator=orchestrator)
        return self._run_provider(session, user_input, normalized, orchestrator=orchestrator)

    def _run_provider(
        self,
        session: BrainstormSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        if session.provider_id == "deepseek":
            if not settings.brainstorm_deepseek_api_key:
                raise ValueError("DeepSeek provider is not configured")
            client = DeepSeekBrainstormClient(
                api_key=settings.brainstorm_deepseek_api_key,
                base_url=settings.brainstorm_deepseek_base_url,
                model=session.model or settings.brainstorm_deepseek_model,
            )
            return client.run_turn(session=session, user_input=user_input, normalized=normalized)
        return self._mock_model_output(session, user_input, normalized, orchestrator=orchestrator)

    def _normalize_input(self, user_input: str, *, quick_options: list[dict] | None = None) -> dict:
        stripped = user_input.strip()
        option = stripped[:1].upper() if stripped else ""
        if option in {"A", "B", "C"}:
            option_text = stripped[1:].lstrip("，,、.。:： ").strip()
            matched_quick_option = self._find_quick_option(quick_options or [], option)
            return {
                "input_type": "quick_option_answer",
                "matched_option": option,
                "matched_option_label": matched_quick_option.get("label") if matched_quick_option else None,
                "semantic": option_text
                or str(matched_quick_option.get("label") if matched_quick_option else "")
                or self._option_semantic(option),
            }
        if stripped in {"继续", "可以", "下一步"}:
            return {
                "input_type": "short_command",
                "matched_option": None,
                "matched_option_label": None,
                "semantic": "用户要求继续推进。",
            }
        return {"input_type": "free_text", "matched_option": None, "matched_option_label": None, "semantic": stripped}

    def _normalize_quick_options(self, value: object) -> list[dict]:
        if not isinstance(value, list):
            return []
        normalized: list[dict] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip().upper()
            label = str(item.get("label") or "").strip()
            if key and label:
                normalized.append({**item, "key": key, "label": label})
        return normalized

    def _find_quick_option(self, options: list[dict], key: str) -> dict | None:
        normalized_key = key.strip().upper()
        for option in options:
            if str(option.get("key") or "").strip().upper() == normalized_key:
                return option
        return None

    def _option_semantic(self, option: str) -> str:
        return {
            "A": "系统初步定位为计算分析工具。",
            "B": "系统初步定位为协同规划平台。",
            "C": "系统同时包含计算分析与协同规划。",
        }[option]

    def _mock_model_output(
        self,
        session: BrainstormSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        semantic = normalized["semantic"]
        state = dict(session.payload or {})
        active_node = self._find_spec_node(
            list(state.get("spec_tree") or self._new_spec_tree(session.template_id)),
            str(state.get("active_spec_node_id") or ""),
        )
        active_section = active_node.get("target_section") if active_node else "未绑定模板章节"
        clause_id = self._clause_id_from_node(active_node)
        fact = self._fact_for_active_node(clause_id, semantic)
        patch_content = self._patch_for_active_node(clause_id, semantic)
        next_question = str(active_node.get("question") if active_node else "请继续补充需求规格说明。")
        quick_options = self._quick_options_for_node(active_node)

        return {
            "organizer_interpretation": {
                "summary": f"用户输入可转化为 {active_section} 的需求规格材料。",
                "intent": "supplement_requirement",
                "confidence": "medium",
            },
            "assistant_message": f"基于你的输入，本轮更新了：{active_section}。",
            "next_suggestion": {
                "kind": "topic",
                "content": "",
                "reason": "",
                "related_spec_node_ids": [],
            },
            "next_question": next_question,
            "quick_options": quick_options,
            "confirmed_facts_delta": [fact],
            "open_questions_delta": [next_question],
            "document_patch": [
                {
                    "section": active_section,
                    "operation": "append_or_update",
                    "content": patch_content,
                    "write_policy": session.write_policy,
                }
            ],
            "annotations": ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
            "risks": [],
            "confidence": "medium",
            "raw_model_response": {
                "provider_id": session.provider_id,
                "model": session.model,
                "mock": True,
                "orchestrator_id": orchestrator.orchestrator_id,
                "mode": orchestrator.mode,
                "user_input": user_input,
            },
        }

    def _strong_rule_model_output(
        self,
        session: BrainstormSession,
        user_input: str,
        normalized: dict,
        *,
        orchestrator: OrchestratorPackage,
    ) -> dict:
        base = self._mock_model_output(session, user_input, normalized, orchestrator=orchestrator)
        current_section = base["document_patch"][0]["section"] if base["document_patch"] else "未绑定模板章节"
        return {
            **base,
            "organizer_interpretation": {
                "summary": f"强规则组织器将用户输入投影到 {current_section}，并按固定审计顺序处理。",
                "intent": "supplement_requirement",
                "confidence": "high",
            },
            "assistant_message": f"强规则组织器已按固定闭环更新：{current_section}。",
            "annotations": [
                *list(base.get("annotations", [])),
                "强规则组织器按固定状态机执行：输入关系 -> 规格补充 -> 回看 -> 闭环 -> 下一轮设计。",
            ],
            "raw_model_response": {
                **dict(base.get("raw_model_response") or {}),
                "orchestrator_id": orchestrator.orchestrator_id,
                "mode": orchestrator.mode,
                "mock": True,
            },
        }

    def _build_structured_summary_update(
        self,
        *,
        model_output: dict,
        normalized: dict,
        questions: list[dict],
        facts: list[dict],
        patches: list[dict],
        target_spec_node: dict,
        turn_id: str,
        session: BrainstormSession,
    ) -> dict:
        current_target_section = model_output["document_patch"][0].get("section") if model_output["document_patch"] else None
        source_question = self._resolve_answering_question(
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
            facts.append(
                {
                    "fact_id": fact_id,
                    "content": fact_content,
                    "source_turn_id": turn_id,
                    "source_question_ids": [source_question_id] if source_question_id else [],
                    "target_section": current_target_section or (source_question.get("target_section") if source_question else None),
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
                "resolution_fact_ids": self._append_unique(
                    list(questions[source_index].get("resolution_fact_ids", [])), new_fact_ids
                ),
            }

        for open_question in model_output["open_questions_delta"]:
            target_section = self._infer_target_section_from_model_output(model_output, open_question)
            if any(question.get("content") == open_question for question in questions):
                continue
            if source_question and self._is_same_question_content(open_question, str(source_question.get("content") or "")):
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
            patches.append(
                {
                    "patch_id": patch_id,
                    "target_section": patch.get("section") or "未绑定模板章节",
                    "operation": patch.get("operation") or "append_or_update",
                    "content": patch.get("content") or "",
                    "write_policy": patch.get("write_policy") or session.write_policy,
                    "status": "proposed",
                    "source_fact_ids": new_fact_ids,
                    "source_question_ids": [source_question_id] if source_question_id else [],
                }
            )

        answer_summary = model_output["confirmed_facts_delta"][0] if model_output["confirmed_facts_delta"] else normalized["semantic"]
        return {
            "questions": questions,
            "facts": facts,
            "patches": patches,
            "answer_summary": answer_summary,
            "source_question_id": source_question_id,
        }

    def _new_spec_tree(self, template_id: str = "81433号") -> list[dict]:
        template_payload = self._resolve_template_payload(template_id)
        template_code = self._template_code_from_id(template_id)
        root = {
            "node_id": "SPEC-ROOT",
            "title": f"需求规格说明完成度树（{template_code}号）",
            "target_section": f"{template_code}号 需求规格说明",
            "node_type": "template",
            "question": "按需求规格模板补齐可写入正文的目标节点。",
            "status": "open",
            "answer_summary": "",
            "completion_reason": "",
            "children": [],
        }
        for section in template_payload.get("sections", []):
            section_id = str(section.get("section_id") or "").strip()
            section_title = str(section.get("title") or section_id).strip()
            section_node = {
                "node_id": f"SPEC-SEC-{section_id}",
                "title": section_title,
                "target_section": section_title,
                "node_type": "section",
                "question": f"补齐{section_title}下的需求规格信息。",
                "status": "open",
                "answer_summary": "",
                "completion_reason": "",
                "children": [],
            }
            for clause in section.get("clauses", []):
                clause_id = str(clause.get("clause_id") or "").strip()
                clause_title = str(clause.get("title") or clause_id).strip()
                if not clause_id:
                    continue
                section_node["children"].append(
                    {
                        "node_id": f"SPEC-{clause_id}",
                        "title": f"{clause_id} {clause_title}",
                        "target_section": f"{section_title} / {clause_title}",
                        "node_type": "clause",
                        "question": CLAUSE_QUESTIONS.get(clause_id, f"请补齐{clause_title}。"),
                        "status": "open",
                        "answer_summary": "",
                        "completion_reason": "",
                        "children": [],
                    }
                )
            root["children"].append(section_node)
        self._refresh_parent_statuses([root])
        return [root]

    def _resolve_template_payload(self, template_id: str) -> dict:
        template = self.session.get(RequirementAuthoringTemplate, template_id)
        if template is not None:
            return dict(template.payload or default_template_payload(template.template_code))
        template_code = self._template_code_from_id(template_id)
        return default_template_payload(template_code)

    def _template_code_from_id(self, template_id: str) -> str:
        digits = "".join(char for char in template_id if char.isdigit())
        if digits.startswith("82259"):
            return "82259"
        return "81433"

    def _active_spec_node_context(self, spec_tree: list[dict], node_id: str | None) -> dict:
        node = self._find_spec_node(spec_tree, node_id or "") if node_id else None
        if node is None:
            return {
                "node_id": None,
                "title": "已完成",
                "target_section": "整体复核",
                "node_type": "completion",
                "question": "当前需求规格完成度树暂无待确认节点。",
                "path": [],
                "status": "closed",
            }
        return {
            "node_id": node.get("node_id"),
            "title": node.get("title"),
            "target_section": node.get("target_section"),
            "node_type": node.get("node_type") or "clause",
            "question": node.get("question") or node.get("title"),
            "path": self._spec_node_path(spec_tree, str(node.get("node_id"))),
            "status": node.get("status"),
        }

    def _spec_node_path(self, nodes: list[dict], node_id: str, current: list[str] | None = None) -> list[str]:
        current = current or []
        for node in nodes:
            next_path = [*current, str(node.get("title") or node.get("node_id"))]
            if node.get("node_id") == node_id:
                return next_path
            child_path = self._spec_node_path(list(node.get("children", [])), node_id, next_path)
            if child_path:
                return child_path
        return []

    def _decision_trace_seed(
        self,
        *,
        projection_spec_node: dict,
        normalized: dict,
        next_open_before_update: str | None,
        orchestrator: OrchestratorPackage,
    ) -> list[str]:
        orchestrator_label = (
            "强规则组织器"
            if orchestrator.orchestrator_id == "xg-strong-rule-orchestrator"
            else orchestrator.name
        )
        return [
            f"当前组织器：{orchestrator_label}（{orchestrator.orchestrator_id} / {orchestrator.mode}）。",
            "用户输入是本轮 Turn 起点。",
            f"本轮投影节点为 {projection_spec_node.get('node_id')} / {projection_spec_node.get('title')}。",
            f"投影目标章节为 {projection_spec_node.get('target_section')}。",
            f"本轮输入类型为 {normalized.get('input_type')}，语义摘要为：{normalized.get('semantic')}。",
            f"处理前第一个 open 叶子节点为 {next_open_before_update or '无'}。",
            "组织器规则：先回应用户本轮输入，再把结果投影到需求规格完成度树。",
        ]

    def _previous_interaction(self, value: object, *, last_quick_options: list[dict]) -> dict:
        if not isinstance(value, dict):
            return {
                "interaction_id": None,
                "type": "none",
                "prompt": "无，用户自由发起。",
                "options": [],
                "target_spec_node_ids": [],
                "reason": "首轮或上轮没有系统留题。",
            }
        return {
            "interaction_id": value.get("interaction_id"),
            "type": str(value.get("type") or "suggestion"),
            "prompt": str(value.get("prompt") or ""),
            "options": self._normalize_quick_options(value.get("options") or last_quick_options),
            "target_spec_node_ids": [
                str(item) for item in value.get("target_spec_node_ids", []) if str(item).strip()
            ]
            if isinstance(value.get("target_spec_node_ids"), list)
            else [],
            "reason": str(value.get("reason") or ""),
        }

    def _state_changes(
        self,
        *,
        previous_questions: list[dict],
        updated_questions: list[dict],
        closed_spec_node_ids: list[str],
        next_active_spec_node_id: str | None,
    ) -> dict:
        previous_by_id = {question.get("question_id"): question for question in previous_questions}
        closed_question_ids = [
            str(question.get("question_id"))
            for question in updated_questions
            if question.get("status") == "confirmed"
            and previous_by_id.get(question.get("question_id"), {}).get("status") != "confirmed"
        ]
        created_question_ids = [
            str(question.get("question_id"))
            for question in updated_questions
            if question.get("question_id") not in previous_by_id
        ]
        return {
            "closed_question_ids": closed_question_ids,
            "created_question_ids": created_question_ids,
            "closed_spec_node_ids": closed_spec_node_ids,
            "next_active_spec_node_id": next_active_spec_node_id,
        }

    def _spec_execution(self, *, model_output: dict, affected_spec_nodes: list[dict], state_changes: dict) -> dict:
        return {
            "interpretation": model_output["organizer_interpretation"],
            "assistant_message": model_output["assistant_message"],
            "confirmed_facts": model_output["confirmed_facts_delta"],
            "affected_spec_nodes": affected_spec_nodes,
            "document_patch": model_output["document_patch"],
            "state_changes": state_changes,
            "annotations": model_output["annotations"],
            "risks": model_output["risks"],
        }

    def _post_update_review(
        self,
        *,
        previous_interaction: dict,
        next_spec_node: dict,
        closed_spec_node_ids: list[str],
    ) -> dict:
        previous_resolved = bool(closed_spec_node_ids) or previous_interaction.get("type") == "none"
        current_sufficient = bool(closed_spec_node_ids)
        remaining_gaps = []
        if next_spec_node.get("node_id"):
            remaining_gaps.append(str(next_spec_node.get("question") or next_spec_node.get("title")))
        summary = (
            f"本轮已形成可写入材料，相关节点可关闭；下一处缺口是 {next_spec_node.get('target_section')}。"
            if next_spec_node.get("node_id")
            else "本轮已形成可写入材料，完成度树暂无待确认节点，可进入整体复核。"
        )
        return {
            "summary": summary,
            "previous_interaction_resolved": previous_resolved,
            "current_spec_node_sufficient": current_sufficient,
            "needs_followup_on_same_topic": not current_sufficient,
            "remaining_gaps": remaining_gaps,
        }

    def _closure_decision(
        self,
        *,
        spec_execution: dict,
        post_update_review: dict,
        closed_spec_node_ids: list[str],
    ) -> dict:
        status = "closed" if closed_spec_node_ids else "needs_followup"
        next_action = "propose_next_interaction" if not post_update_review["needs_followup_on_same_topic"] else "continue_same_topic"
        return {
            "status": status,
            "reason": (
                "本轮输入已被吸收，并形成需求规格正文建议；无需继续追问同一题。"
                if status == "closed"
                else "本轮已有回应，但尚未形成足够的需求规格正文建议，需要继续追问同一题。"
            ),
            "next_action": next_action,
        }

    def _next_interaction(self, *, next_spec_node: dict, model_output: dict, turn_index: int) -> dict:
        if not next_spec_node.get("node_id"):
            return {
                "interaction_id": f"interaction-{turn_index:04d}",
                "type": "free_continue",
                "prompt": "当前完成度树暂无待确认节点，可以进入整体复核。",
                "options": [],
                "target_spec_node_ids": [],
                "reason": "需求规格完成度树暂无 open 叶子节点。",
            }
        options = self._normalize_quick_options(model_output.get("quick_options"))
        interaction_type = "choice_question" if options else "open_question"
        next_suggestion = model_output.get("next_suggestion")
        suggestion_prompt = (
            str(next_suggestion.get("content") or "").strip() if isinstance(next_suggestion, dict) else ""
        )
        return {
            "interaction_id": f"interaction-{turn_index:04d}",
            "type": interaction_type,
            "prompt": suggestion_prompt
            or str(model_output.get("next_question") or next_spec_node.get("question") or next_spec_node.get("title")),
            "options": options,
            "target_spec_node_ids": [str(next_spec_node["node_id"])],
            "reason": str(
                next_suggestion.get("reason")
                if isinstance(next_suggestion, dict)
                else ""
            )
            or f"补充后回看发现 {next_spec_node.get('target_section')} 仍缺少可写入材料。",
        }

    def _align_model_output_to_next_node(
        self,
        *,
        model_output: dict,
        next_spec_node: dict,
        current_spec_node: dict,
        session: BrainstormSession,
    ) -> dict:
        if not next_spec_node.get("node_id"):
            next_question = "当前完成度树已无待确认节点。需要整体复核哪些章节仍显薄弱？"
            quick_options: list[dict] = []
        else:
            next_question = str(next_spec_node.get("question") or next_spec_node.get("title"))
            if model_output.get("raw_model_response", {}).get("mock") or not model_output.get("quick_options"):
                quick_options = self._quick_options_for_node(next_spec_node)
            else:
                quick_options = model_output["quick_options"]
        updated_sections = current_spec_node.get("target_section") or "需求规格说明"
        next_content = (
            f"建议下一步确认：{next_question}"
            if next_spec_node.get("node_id")
            else "当前完成度树暂无待确认节点，可以进入整体复核。"
        )
        orchestrator_id = str(model_output.get("raw_model_response", {}).get("orchestrator_id") or "")
        if orchestrator_id == "xg-strong-rule-orchestrator":
            assistant_message = f"强规则组织器已按固定闭环更新：{updated_sections}。{next_content}"
        else:
            assistant_message = f"基于你的输入，本轮更新了：{updated_sections}。{next_content}"
        existing_suggestion = model_output.get("next_suggestion")
        existing_suggestion_id = (
            existing_suggestion.get("suggestion_id") if isinstance(existing_suggestion, dict) else ""
        )
        existing_content = (
            str(existing_suggestion.get("content") or "").strip() if isinstance(existing_suggestion, dict) else ""
        )
        existing_reason = (
            str(existing_suggestion.get("reason") or "").strip() if isinstance(existing_suggestion, dict) else ""
        )
        existing_related = (
            list(existing_suggestion.get("related_spec_node_ids") or [])
            if isinstance(existing_suggestion, dict) and isinstance(existing_suggestion.get("related_spec_node_ids"), list)
            else []
        )
        next_suggestion = {
            "suggestion_id": "",
            "kind": "topic",
            "content": existing_content or next_content,
            "reason": (
                existing_reason
                or f"{updated_sections} 已有可写入材料，完成度树建议继续补齐 {next_spec_node.get('target_section')}。"
                if next_spec_node.get("node_id")
                else "需求规格完成度树暂无 open 叶子节点。"
            ),
            "related_spec_node_ids": existing_related or ([next_spec_node["node_id"]] if next_spec_node.get("node_id") else []),
        }
        return {
            **model_output,
            "assistant_message": assistant_message,
            "next_suggestion": {
                **next_suggestion,
                "suggestion_id": str(existing_suggestion_id or ""),
            },
            "next_question": next_question,
            "quick_options": quick_options,
            "open_questions_delta": [next_question] if next_spec_node.get("node_id") else [],
            "document_patch": [
                {
                    **patch,
                    "write_policy": patch.get("write_policy") or session.write_policy,
                }
                for patch in model_output["document_patch"]
            ],
        }

    def _ensure_patch_target_section(self, *, model_output: dict, current_spec_node: dict, session: BrainstormSession) -> dict:
        current_section = str(current_spec_node.get("target_section") or "未绑定模板章节")
        patches = []
        for patch in model_output.get("document_patch", []):
            section = str(patch.get("section") or "").strip() or current_section
            patches.append(
                {
                    **patch,
                    "section": section,
                    "write_policy": patch.get("write_policy") or session.write_policy,
                }
            )
        if not patches and model_output.get("confirmed_facts_delta"):
            patches.append(
                {
                    "section": current_section,
                    "operation": "append_or_update",
                    "content": str(model_output["confirmed_facts_delta"][0]),
                    "write_policy": session.write_policy,
                }
            )
        return {**model_output, "document_patch": patches}

    def _clause_id_from_node(self, node: dict | None) -> str:
        if not node:
            return ""
        node_id = str(node.get("node_id") or "")
        return node_id.removeprefix("SPEC-")

    def _fact_for_active_node(self, clause_id: str, semantic: str) -> str:
        if clause_id == "REQ-1.1":
            return f"编写目的初步确认：{semantic}"
        if clause_id == "REQ-2.1":
            return f"软件定位初步确认：{semantic}"
        if clause_id == "REQ-3.1":
            return f"用户与角色初步确认：{semantic}"
        if clause_id == "REQ-3.2":
            return f"核心业务流程初步确认：{semantic}"
        if clause_id == "REQ-3.3":
            return f"异常与补偿初步确认：{semantic}"
        if clause_id == "REQ-4.1":
            return f"性能与可靠性初步确认：{semantic}"
        if clause_id == "REQ-5.1":
            return f"验收准则初步确认：{semantic}"
        return f"需求规格信息初步确认：{semantic}"

    def _patch_for_active_node(self, clause_id: str, semantic: str) -> str:
        if clause_id == "REQ-1.1":
            return f"本文档用于定义{semantic}相关的软件需求边界、功能行为和验收准则。"
        if clause_id == "REQ-2.1":
            return f"软件定位为：{semantic}"
        if clause_id == "REQ-3.1":
            return f"本软件的主要使用对象和职责包括：{semantic}"
        if clause_id == "REQ-3.2":
            return f"核心业务流程为：{semantic}"
        if clause_id == "REQ-3.3":
            return f"异常与补偿要求为：{semantic}"
        if clause_id == "REQ-4.1":
            return f"性能与可靠性要求为：{semantic}"
        if clause_id == "REQ-5.1":
            return f"验收准则为：{semantic}"
        return semantic

    def _quick_options_for_node(self, node: dict | None) -> list[dict]:
        clause_id = self._clause_id_from_node(node)
        options_by_clause = {
            "REQ-1.1": [
                ("A", "先定义软件名称和目标", True),
                ("B", "先说明业务背景", False),
                ("C", "先限定不做什么", False),
            ],
            "REQ-2.1": [
                ("A", "计算分析工具", True),
                ("B", "协同规划平台", False),
                ("C", "二者兼有但先做分析", False),
            ],
            "REQ-3.1": [
                ("A", "领域专家直接使用", True),
                ("B", "管理员配置后专家使用", False),
                ("C", "多角色协同使用", False),
            ],
            "REQ-3.2": [
                ("A", "导入数据后计算分析", True),
                ("B", "配置任务后批量处理", False),
                ("C", "人工确认后生成报告", False),
            ],
            "REQ-3.3": [
                ("A", "缺数据时阻断并提示", True),
                ("B", "异常时进入人工复核", False),
                ("C", "允许保存为待处理", False),
            ],
            "REQ-4.1": [
                ("A", "优先保证可靠性", True),
                ("B", "优先保证响应速度", False),
                ("C", "先按单机部署约束", False),
            ],
            "REQ-5.1": [
                ("A", "按功能闭环验收", True),
                ("B", "按专家评审验收", False),
                ("C", "按演示样例验收", False),
            ],
        }
        return [
            {"key": key, "label": label, "recommended": recommended}
            for key, label, recommended in options_by_clause.get(clause_id, [])
        ]

    def _update_spec_tree(self, *, spec_tree: list[dict], active_node_id: str, answer_summary: str, turn_id: str) -> dict:
        closed_node_ids: list[str] = []
        node = self._find_spec_node(spec_tree, active_node_id)
        if node is not None:
            node["status"] = "closed"
            node["answer_summary"] = answer_summary
            node["completion_reason"] = f"{turn_id} 用户已确认"
            closed_node_ids.append(active_node_id)
        self._refresh_parent_statuses(spec_tree)
        return {
            "spec_tree": spec_tree,
            "active_spec_node_id": self._first_open_spec_node_id(spec_tree),
            "closed_node_ids": closed_node_ids,
        }

    def _find_spec_node(self, nodes: list[dict], node_id: str) -> dict | None:
        for node in nodes:
            if node.get("node_id") == node_id:
                return node
            child = self._find_spec_node(list(node.get("children", [])), node_id)
            if child is not None:
                return child
        return None

    def _first_open_spec_node_id(self, nodes: list[dict]) -> str | None:
        for node in nodes:
            children = list(node.get("children", []))
            if children:
                child_id = self._first_open_spec_node_id(children)
                if child_id:
                    return child_id
                continue
            if node.get("status") == "open":
                return str(node.get("node_id"))
        return None

    def _refresh_parent_statuses(self, nodes: list[dict]) -> None:
        for node in nodes:
            children = list(node.get("children", []))
            if not children:
                continue
            self._refresh_parent_statuses(children)
            child_statuses = {child.get("status") for child in children}
            if child_statuses == {"closed"}:
                node["status"] = "closed"
            elif "closed" in child_statuses or "partial" in child_statuses:
                node["status"] = "partial"
            else:
                node["status"] = "open"

    def _resolve_answering_question(
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
            if target_spec_node.get("node_id"):
                question = {
                    "question_id": f"Q-{len(questions) + 1:03d}",
                    "content": self._suggestion_content_for_node(target_spec_node),
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

    def _infer_target_section(self, content: str) -> str:
        if "输入" in content or "数据来源" in content:
            return "2.1 输入数据"
        if "输出" in content or "结果形式" in content:
            return "2.2 输出结果"
        if "用户" in content or "角色" in content or "协同" in content or "编辑" in content:
            return "1.2 用户角色"
        if "功能" in content:
            return "3. 功能需求"
        if "目标" in content or "定位" in content or "系统更偏向" in content:
            return "1.1 系统目标"
        return "未归类澄清项"

    def _infer_target_section_from_model_output(self, model_output: dict, open_question: str) -> str:
        if model_output.get("document_patch"):
            section = str(model_output["document_patch"][0].get("section") or "").strip()
            if section:
                return section
        return self._infer_target_section(open_question)

    def _select_projection_spec_node_id(self, spec_tree: list[dict], model_output: dict, fallback_node_id: str) -> str:
        patch_sections = [
            str(patch.get("section") or "").strip()
            for patch in model_output.get("document_patch", [])
            if isinstance(patch, dict)
        ]
        for section in patch_sections:
            matched = self._find_spec_node_by_target_section(spec_tree, section)
            if matched and matched.get("node_id"):
                return str(matched["node_id"])
        return fallback_node_id

    def _find_spec_node_by_target_section(self, nodes: list[dict], target_section: str) -> dict | None:
        for node in nodes:
            if node.get("target_section") == target_section:
                return node
            child = self._find_spec_node_by_target_section(list(node.get("children", [])), target_section)
            if child is not None:
                return child
        return None

    def _ensure_next_open_question(
        self,
        *,
        questions: list[dict],
        next_question: str,
        next_spec_node: dict,
        turn_id: str,
    ) -> list[dict]:
        if not next_question or not next_spec_node.get("node_id"):
            return questions
        for question in questions:
            if question.get("status") == "open" and question.get("target_section") == next_spec_node.get("target_section"):
                return questions
        for question in questions:
            if question.get("content") == next_question and question.get("status") == "open":
                question["target_section"] = next_spec_node.get("target_section")
                return questions
        questions.append(
            {
                "question_id": f"Q-{len(questions) + 1:03d}",
                "content": next_question,
                "status": "open",
                "target_section": next_spec_node.get("target_section"),
                "source_turn_id": turn_id,
                "resolution_fact_ids": [],
            }
        )
        return questions

    @staticmethod
    def _is_same_question_content(candidate: str, existing: str) -> bool:
        normalized_candidate = candidate.replace("可以补齐：", "").strip()
        normalized_existing = existing.replace("可以补齐：", "").strip()
        return bool(normalized_candidate) and (
            normalized_candidate == normalized_existing
            or normalized_candidate in normalized_existing
            or normalized_existing in normalized_candidate
        )

    def _service_steps(self) -> list[dict]:
        return [
            {"step": 1, "title": "接收用户输入", "status": "completed"},
            {"step": 2, "title": "读取会话状态", "status": "completed"},
            {"step": 3, "title": "读取模板与知识包", "status": "completed"},
            {"step": 4, "title": "组装组织器上下文", "status": "completed"},
            {"step": 5, "title": "调用组织器 / Provider", "status": "completed"},
            {"step": 6, "title": "解析结构化输出", "status": "completed"},
            {"step": 7, "title": "校验并落状态", "status": "completed"},
        ]

    def _stable_contract(self) -> dict:
        return {
            "formal_document": True,
            "template_object": True,
            "knowledge_binding": True,
            "draft_persistence": True,
            "check_and_freeze": True,
            "p2_to_p3_output": True,
        }

    def _append_unique(self, current: list[str], additions: list[str]) -> list[str]:
        result = list(current)
        for item in additions:
            if item not in result:
                result.append(item)
        return result

    def _normalize_turn_model_output(self, model_output: dict, *, session: BrainstormSession) -> dict:
        next_suggestion = model_output.get("next_suggestion")
        if not isinstance(next_suggestion, dict):
            next_question = str(model_output.get("next_question") or "")
            next_suggestion = {
                "kind": "topic",
                "content": next_question or "下一轮可以继续补齐需求规格说明。",
                "reason": "Provider 未返回 next_suggestion，服务端按旧字段兼容生成。",
                "related_spec_node_ids": [],
            }
        normalized = {
            **model_output,
            "organizer_interpretation": self._normalize_organizer_interpretation(model_output.get("organizer_interpretation")),
            "next_suggestion": {
                "suggestion_id": str(next_suggestion.get("suggestion_id") or ""),
                "kind": str(next_suggestion.get("kind") or "topic"),
                "content": str(next_suggestion.get("content") or ""),
                "reason": str(next_suggestion.get("reason") or ""),
                "related_spec_node_ids": [
                    str(item) for item in next_suggestion.get("related_spec_node_ids", []) if str(item).strip()
                ]
                if isinstance(next_suggestion.get("related_spec_node_ids"), list)
                else [],
            },
            "quick_options": list(model_output.get("quick_options", [])),
            "confirmed_facts_delta": list(model_output.get("confirmed_facts_delta", [])),
            "open_questions_delta": list(model_output.get("open_questions_delta", [])),
            "document_patch": list(model_output.get("document_patch", [])),
            "annotations": list(model_output.get("annotations", [])),
            "risks": list(model_output.get("risks", [])),
            "confidence": str(model_output.get("confidence") or "medium"),
            "raw_model_response": dict(model_output.get("raw_model_response") or {"provider_id": session.provider_id, "mock": True}),
        }
        return normalized

    def _normalize_organizer_interpretation(self, value: object) -> dict:
        if isinstance(value, dict):
            return {
                "summary": str(value.get("summary") or "系统已理解本轮用户输入。"),
                "intent": str(value.get("intent") or "supplement_requirement"),
                "confidence": str(value.get("confidence") or "medium"),
            }
        return {
            "summary": "系统已理解本轮用户输入。",
            "intent": "supplement_requirement",
            "confidence": "medium",
        }

    def _classify_input_relation(
        self,
        previous_interaction: object,
        normalized: dict,
        *,
        last_quick_options: list[dict],
    ) -> dict:
        if normalized.get("input_type") == "quick_option_answer":
            matched_option = str(normalized.get("matched_option") or "").strip().upper()
            previous_option = self._find_quick_option(last_quick_options, matched_option)
            if previous_option:
                return {
                    "relation": "selected_option",
                    "reason": f"用户选择了上轮选项 {matched_option}：{previous_option.get('label')}。",
                }
        if not isinstance(previous_interaction, dict) or previous_interaction.get("type") == "none":
            return {"relation": "none", "reason": "本轮之前没有上轮系统留题。"}
        semantic = str(normalized.get("semantic") or "")
        prompt = str(previous_interaction.get("prompt") or "")
        if any(token in semantic for token in ["不是", "先不", "不对", "别", "反对"]):
            return {"relation": "challenge", "reason": "用户输入包含否定或纠正意图，优先按反驳/修正处理。"}
        if any(token in semantic for token in ["先", "按", "确认", "可以", "继续"]):
            return {"relation": "answered", "reason": "用户输入承接了上轮系统留题并给出确认或推进指令。"}
        if "软件定位" in prompt or "定位" in prompt:
            if any(token in semantic for token in ["工具", "平台", "领域", "第一阶段", "系统"]):
                return {"relation": "answered", "reason": "用户输入回答了上轮系统留题中的软件定位信息。"}
        if "用户" in prompt or "角色" in prompt:
            if any(token in semantic for token in ["用户", "专家", "管理员", "角色", "使用"]):
                return {"relation": "answered", "reason": "用户输入回答了上轮系统留题中的用户或角色信息。"}
        return {"relation": "partially_answered", "reason": "用户输入部分承接上轮系统留题，但仍需要结合需求规格继续分析。"}

    def _affected_spec_nodes(self, *, spec_tree: list[dict], node_ids: list[str]) -> list[dict]:
        affected: list[dict] = []
        for node_id in node_ids:
            node = self._find_spec_node(spec_tree, node_id)
            affected.append(
                {
                    "node_id": node_id or None,
                    "title": node.get("title") if node else node_id,
                    "target_section": node.get("target_section") if node else "未绑定模板章节",
                    "effect": "update",
                    "reason": "用户本轮输入形成了该章节的可写入材料。",
                }
            )
        return affected

    def _decision_trace(
        self,
        *,
        previous_interaction: dict,
        input_relation: dict,
        spec_execution: dict,
        post_update_review: dict,
        closure_decision: dict,
        next_interaction: dict,
        seed: list[str],
    ) -> list[str]:
        trace = list(seed)
        trace.append(f"读取上轮系统留题：{previous_interaction.get('type')} / {previous_interaction.get('prompt')}")
        trace.append(f"输入关系判定为 {input_relation.get('relation')}：{input_relation.get('reason')}")
        affected_labels = "、".join(
            str(node.get("target_section") or node.get("node_id"))
            for node in spec_execution.get("affected_spec_nodes", [])
        )
        trace.append(f"先执行规格补充：{affected_labels or '无'}。")
        trace.append(f"补充后回看：{post_update_review.get('summary')}")
        trace.append(
            f"本轮处理闭环：{closure_decision.get('status')}，下一步策略 {closure_decision.get('next_action')}。"
        )
        trace.append(f"下一轮交互设计：{next_interaction.get('type')} / {next_interaction.get('prompt')}")
        return trace

    def _suggestion_content_for_node(self, node: dict | None) -> str:
        if node is None:
            return "请直接描述你希望形成的需求规格说明内容。"
        return f"可以补齐：{node.get('question') or node.get('title')}"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
