from __future__ import annotations

import importlib.util
import json
import sys
from typing import Any

from app.orchestrators.contract_validator import OrchestratorContractValidator
from app.orchestrators.package_loader import OrchestratorPackageLoader


class OrchestratorRunnerHost:
    def __init__(
        self,
        *,
        loader: OrchestratorPackageLoader | None = None,
        validator: OrchestratorContractValidator | None = None,
    ) -> None:
        self.loader = loader or OrchestratorPackageLoader()
        self.validator = validator or OrchestratorContractValidator()

    def build_provider_prompt_bundle(
        self,
        orchestrator_id: str,
        *,
        context: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict:
        loaded = self.loader.load(orchestrator_id)
        context_json = json.dumps(context, ensure_ascii=False)
        schema_json = json.dumps(output_schema, ensure_ascii=False)
        assembled_prompt = (
            f"{loaded.orchestrator_text}\n\n"
            f"{loaded.policy_text}\n\n"
            f"{loaded.prompt_text}\n\n"
            "请基于以下会话上下文，生成一轮 Requirement Analysis Turn 输出。\n"
            "这只是需求规格说明写作 Lab，不是通用知识图谱。输出必须服务于需求规格章节成文。\n"
            "用户输入是本轮 Turn 的起点，不是对系统预设问题的必答项。\n"
            "previous_interaction 是上轮系统留题，可能是开放问题、选择题、建议方向或空。\n"
            "你必须先判断用户本轮输入的真实意图，再执行规格补充、回看状态，最后设计 next_interaction。\n"
            "不要把用户输入强行解释为对某个 active 节点的回答。\n"
            "document_patch 可以指向一个或多个最合理的需求规格章节，章节必须能从 spec_tree 或用户输入解释出来。\n"
            "next_suggestion 将被服务端转换为 next_interaction；它只是下一轮留题，可以被用户忽略、反驳或改题。\n"
            "post_update_review 必须解释本轮补充后是否足够、还缺什么，不能刚收到回答就机械进入下一题。\n"
            "quick_options 只有在确实需要轻量决策时才出现，不要每轮都强行生成。\n"
            "confirmed_facts_delta 只放本轮用户已经明确确认的事实，不要重复历史事实。\n"
            "open_questions_delta 只放下一步仍需要确认的问题，不要重复历史 open_questions。\n"
            "document_patch 只为本轮新增确认事实生成建议。\n"
            f"会话上下文 JSON：{context_json}\n"
            f"必须返回且只返回符合此结构的 JSON：{schema_json}"
        )
        return {
            "orchestrator_id": loaded.package.orchestrator_id,
            "mode": loaded.package.mode,
            "context_json": context_json,
            "schema_json": schema_json,
            "assembled_prompt": assembled_prompt,
            "policy_text": loaded.policy_text,
            "prompt_text": loaded.prompt_text,
        }

    def normalize_output(
        self,
        payload: dict[str, Any],
        *,
        provider_id: str,
        model: str,
        write_policy: str,
        raw_response: dict[str, Any] | None = None,
    ) -> dict:
        return self.validator.normalize_turn_output(
            payload,
            provider_id=provider_id,
            model=model,
            write_policy=write_policy,
            raw_response=raw_response,
        )

    def execute_local_runner(self, orchestrator_id: str, *, context: dict[str, Any]) -> dict:
        loaded = self.loader.load(orchestrator_id)
        if loaded.package.mode != "local_runner":
            raise ValueError("orchestrator is not a local runner")
        if not loaded.entry_path:
            raise RuntimeError("local runner orchestrator missing entry path")

        module = self._load_runner_module(orchestrator_id, loaded.entry_path)
        run_turn = getattr(module, "run_turn", None)
        if not callable(run_turn):
            raise RuntimeError(f"local runner {loaded.entry_path} must expose run_turn(context)")

        output = run_turn(context)
        if not isinstance(output, dict):
            raise RuntimeError(f"local runner {loaded.entry_path} must return a dict")

        raw_response = dict(output.get("raw_model_response") or {})
        output["raw_model_response"] = {
            **raw_response,
            "orchestrator_id": loaded.package.orchestrator_id,
            "mode": loaded.package.mode,
            "mock": raw_response.get("mock", True),
            "runner_invoked": True,
            "runner_entry": loaded.entry_path,
        }
        return output

    @staticmethod
    def _load_runner_module(orchestrator_id: str, entry_path: str):
        module_name = f"_codefactory_orchestrator_{orchestrator_id.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load local runner: {entry_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
