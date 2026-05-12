import importlib.util
from pathlib import Path


def _load_probe_module():
    script_path = Path("scripts/p2_orchestrator_multiturn_probe.py")
    spec = importlib.util.spec_from_file_location("p2_orchestrator_multiturn_probe", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dynamic_examiner_does_not_confirm_unverified_first_choice_domain() -> None:
    probe = _load_probe_module()
    last_session = {
        "next_interaction": {
            "prompt": "请为这个态势分析系统起一个软件名称，并说明它主要应用于哪个领域（例如军事、应急、地理信息等）？",
            "options": [
                {"key": "MILI", "label": "军事领域，如战场态势分析"},
                {"key": "EMER", "label": "应急领域，如灾害态势分析"},
                {"key": "GIS", "label": "地理信息领域，如通用空间分析"},
            ],
        },
        "messages": [],
    }

    decision = probe.choose_dynamic_examiner_input(
        turn_index=2,
        max_turns=8,
        last_session=last_session,
        used_domains=set(),
        recent_questions=[],
    )

    assert decision["released_domain"] == "software_positioning"
    assert "MILI" not in decision["user_input"]
    assert "军事领域，如战场态势分析" not in decision["user_input"]
    assert "不完全" in decision["user_input"]


def test_dynamic_examiner_prioritizes_scope_boundary_when_question_asks_no_go_scope() -> None:
    probe = _load_probe_module()
    decision = probe.choose_dynamic_examiner_input(
        turn_index=5,
        max_turns=20,
        last_session={
            "next_interaction": {
                "prompt": "系统明确不做哪些范围，哪些能力只做辅助分析？",
                "options": [],
            },
            "messages": [],
        },
        used_domains={"initial_intent", "user_roles", "workflow"},
        recent_questions=[],
    )

    assert decision["released_domain"] == "scope_boundary"
    assert "不做实时多源情报接入" in decision["user_input"]
    assert "自动决策推荐" in decision["user_input"]


def test_dynamic_examiner_prioritizes_scope_boundary_for_first_stage_inclusion_question() -> None:
    probe = _load_probe_module()
    decision = probe.choose_dynamic_examiner_input(
        turn_index=6,
        max_turns=20,
        last_session={
            "next_interaction": {
                "prompt": "这些角色和核心功能是否全部纳入第一阶段？还是部分角色或功能后续阶段再引入？",
                "options": [],
            },
            "messages": [],
        },
        used_domains={"initial_intent", "software_positioning", "user_roles", "workflow", "core_functions"},
        recent_questions=[],
    )

    assert decision["released_domain"] == "scope_boundary"
    assert "第一阶段" in decision["user_input"]
    assert "不做实时多源情报接入" in decision["user_input"]


def test_dynamic_examiner_answers_role_question_before_correction_for_decision_role_example() -> None:
    probe = _load_probe_module()
    decision = probe.choose_dynamic_examiner_input(
        turn_index=3,
        max_turns=20,
        last_session={
            "next_interaction": {
                "prompt": "系统的目标用户有哪些？他们分别承担什么角色？例如，是分析人员、指挥决策人员，还是其他角色？",
                "options": [],
            },
            "messages": [],
        },
        used_domains={"initial_intent", "workflow"},
        recent_questions=[],
    )

    assert decision["released_domain"] == "user_roles"
    assert decision["examiner_action"] == "answer_question"
    assert "科研分析人员" in decision["user_input"]


def test_brainstorm_next_interaction_prompt_forbids_unconfirmed_domain_options() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "不得把未确认的软件领域" in prompt
    assert "不要把示例领域" in prompt
    assert "不得在 next_question 或 quick_options 中列举“军事、应急、城市规划”" in prompt
    assert "quick_options" in prompt


def test_brainstorm_delivery_prompt_must_not_label_confirmed_facts_as_model_inference() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "必须区分已确认事实与暂定假设" in prompt
    assert "不得把已确认事实统称为模型推断" in prompt
    assert "只能把 `tentative_assumptions`" in prompt


def test_brainstorm_delivery_prompt_forbids_unconfirmed_domain_examples_in_user_message() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "交付模式下" in prompt
    assert "user_message" in prompt
    assert "待确认事项" in prompt
    assert "不得列举“军事、应急、城市规划”" in prompt


def test_brainstorm_next_interaction_prompt_separates_status_review_from_delivery() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "状态回看" in prompt
    assert "不等同于交付草案" in prompt
    assert "不得使用 deliverable 或 draft_delivery" in prompt


def test_brainstorm_decision_state_prompt_forbids_readding_historical_or_example_questions() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(
        encoding="utf-8"
    )

    assert "不得把历史 open_questions 原样重新输出到 open_questions" in prompt
    assert "不得新增模板示例或常见领域示例型问题" in prompt
    assert "具体应用领域待确认" in prompt
    assert "不要生成“如军事、应急、城市规划等”" in prompt


def test_brainstorm_decision_state_prompt_requires_closing_or_deferring_answered_historical_questions() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(
        encoding="utf-8"
    )

    assert "只输出本轮增量" in prompt
    assert "必须维护未闭合问题生命周期" in prompt
    assert "本轮用户已经回答了某个历史问题" in prompt
    assert "输出 `closed_question_refs`" in prompt
    assert "本轮明确暂不回答或应留到草案缺口" in prompt
    assert "输出 `deferred_question_refs`" in prompt
    assert "不得把用户已回答的问题再次作为 open_questions 输出" in prompt
    assert "不得为了追求问题完整性而累计同主题多个未闭合问题" in prompt


def test_brainstorm_next_interaction_prompt_requires_single_focused_question() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "下一轮主问题必须一问一事" in prompt
    assert "不得在一个 next_question 中同时追问" in prompt
    assert "最多只允许包含一个主问题" in prompt
    assert "如果存在多个缺口" in prompt
    assert "只选择当前最影响决策链推进的一个缺口" in prompt


def test_brainstorm_next_interaction_prompt_keeps_terms_after_core_decisions() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "术语与缩略语不是探索收束阶段的优先问题" in prompt
    assert "不得因为 1.3 术语与缩略语缺口而抢占" in prompt
    assert "优先追问用户角色、使用流程、范围边界、数据接口、非功能或验收口径" in prompt
    assert "即使当前活动节点是 1.3" in prompt
    assert "连续两轮" in prompt


def test_brainstorm_next_interaction_prompt_defers_name_and_background_after_one_ask() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "软件名称、背景领域和编写目的" in prompt
    assert "最多只能作为一次早期澄清问题" in prompt
    assert "用户连续补充角色、流程、边界、数据、非功能或验收事实时" in prompt
    assert "不得继续反复追问软件名称、背景领域和编写目的" in prompt
    assert "应把名称或背景领域暂记为待确认事项" in prompt


def test_brainstorm_next_interaction_prompt_forbids_name_background_as_main_question_after_core_facts() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "不得把软件名称、背景领域、编写目的或适用范围作为 next_question 的主问题" in prompt
    assert "只能在 user_message 或待确认事项中列为后续风险" in prompt
    assert "下一问必须转向尚未闭合的核心功能、数据接口、异常补偿、非功能约束或验收准则" in prompt


def test_brainstorm_next_interaction_prompt_defers_repeated_first_stage_inclusion_question() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
        encoding="utf-8"
    )

    assert "第一阶段角色覆盖范围" in prompt
    assert "核心功能是否全部纳入第一阶段" in prompt
    assert "不得连续两轮以上反复追问" in prompt
    assert "将其转为待确认事项" in prompt
    assert "继续推进数据、异常、非功能或验收" in prompt


def test_brainstorm_decision_prompt_treats_answered_scope_roles_and_flow_as_decisions() -> None:
    prompt = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
    )

    assert "用户在回答组织器问题时明确给出的软件定位、范围边界、角色分工、核心流程、数据接入模式、非功能约束或验收口径" in prompt
    assert "应进入 `confirmed_decisions`" in prompt
    assert "不能只放入 `confirmed_facts`" in prompt


def test_brainstorm_v1_strategy_questions_do_not_expose_internal_strategy_label() -> None:
    strategy = Path("orchestrators/xg/brainstorm-v1/spec_strategy.json").read_text(encoding="utf-8")

    assert "组织器策略问题" not in strategy
    assert "请先确认软件名称、背景领域和编写目的" in strategy


def test_brainstorm_draft_prompt_forbids_unconfirmed_domain_examples_in_draft() -> None:
    prompt = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
    )

    assert "禁止列举用户未确认的具体领域示例" in prompt
    assert "即使标注为暂定也不允许" in prompt
    assert "军事、应急、城市规划" in prompt


def test_brainstorm_draft_prompt_preserves_user_proposed_capabilities() -> None:
    prompt = Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(
        encoding="utf-8"
    )

    assert "用户首轮明确提出的功能能力" in prompt
    assert "不得写成“未在本轮确认”" in prompt
    assert "部署分析" in prompt


def test_brainstorm_convergence_prompt_uses_quality_gate_instead_of_short_summary() -> None:
    prompt = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
    )

    assert "仍应控制 provider JSON 尺寸" in prompt
    assert "不得把成稿压缩成短摘要" in prompt
    assert "接近一万字" in prompt
    assert "工程需求章节应成为主要篇幅来源" in prompt
    assert "document_patch 最多输出 6 条" not in prompt
    assert "每条 content 控制在 500 字以内" not in prompt


def test_brainstorm_convergence_prompt_uses_json_safe_incremental_draft_patches() -> None:
    prompt = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
    )

    assert "单条 document_patch.content 控制在 600 到 800 字" in prompt
    assert "document_patch 输出 4 到 6 条" in prompt
    assert "篇幅目标主要通过多轮过程累计正文达成" in prompt
    assert "不得为了追求一万字在同一次 provider JSON 中输出超长正文" in prompt
    assert "如果本轮无法一次达到篇幅目标" in prompt
    assert "本轮先完成结构完整、工程需求补厚和待确认事项归档" in prompt
    assert "不要输出会导致 JSON 截断的超长字符串" in prompt


def test_brainstorm_convergence_prompt_requires_draft_body_in_document_patch_not_user_message() -> None:
    prompt = (
        Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.system.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/decision_state_delta.user.md").read_text(encoding="utf-8")
        + "\n"
        + Path("orchestrators/xg/brainstorm-v1/prompts/next_interaction_planning.system.md").read_text(
            encoding="utf-8"
        )
    )

    assert "草案正文必须进入 document_patch.content" in prompt
    assert "不得把完整草案正文放入 user_message、next_question 或 assistant_message" in prompt
    assert "user_message 只输出交付摘要" in prompt
    assert "工程需求重点条款应优先加厚" in prompt


def test_dynamic_examiner_does_not_repeat_review_request_after_review_domain_used() -> None:
    probe = _load_probe_module()
    used_domains = {fact["domain"] for fact in probe.DYNAMIC_EXAMINER_FACTS}
    used_domains.add("review")

    decision = probe.choose_dynamic_examiner_input(
        turn_index=12,
        max_turns=20,
        last_session={
            "next_interaction": {
                "prompt": "目前哪些关键决策已经闭合，哪些还没有闭合？",
                "options": [],
            },
            "messages": [],
        },
        used_domains=used_domains,
        recent_questions=["目前哪些关键决策已经闭合，哪些还没有闭合？"],
    )

    assert decision["examiner_action"] != "review_request"
    assert decision["examiner_action"] == "convergence_request"


def test_dynamic_probe_stops_after_delivery_interaction() -> None:
    probe = _load_probe_module()

    assert probe.should_stop_dynamic_probe_after_turn(
        {
            "next_interaction": {
                "type": "draft_delivery",
                "prompt": "已停止追问，并基于已确认信息生成章节化草案。",
                "options": [],
            }
        }
    )
    assert probe.should_stop_dynamic_probe_after_turn(
        {
            "next_interaction": {
                "type": "deliverable",
                "prompt": "已基于当前所有已确认信息生成完整需求规格说明草案。",
                "options": [],
            }
        }
    )
    assert not probe.should_stop_dynamic_probe_after_turn(
        {
            "next_interaction": {
                "type": "open_question",
                "prompt": "接下来优先处理哪个未闭合项？",
                "options": [],
            }
        }
    )
