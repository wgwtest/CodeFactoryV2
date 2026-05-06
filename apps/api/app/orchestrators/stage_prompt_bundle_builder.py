from __future__ import annotations

import json
from typing import Any

from app.orchestrators.package_loader import LoadedOrchestratorPackage
from app.orchestrators.stage_prompt_resolver import StagePrompt


class StagePromptBundleBuilder:
    def build(
        self,
        *,
        loaded: LoadedOrchestratorPackage,
        stage: dict,
        prompt: StagePrompt,
        context: dict[str, Any],
        output_schema: dict[str, Any],
        adoption_policy: dict[str, Any],
        extra_prompt_bundle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stage_id = str(stage.get("stage_id") or "stage-001")
        context_json = json.dumps(context, ensure_ascii=False)
        schema_json = json.dumps(output_schema, ensure_ascii=False)
        adoption_policy_json = json.dumps(adoption_policy, ensure_ascii=False)
        stage_task_definition = dict(context.get("stage_task_definition") or {})
        quality_constraints = dict(context.get("stage_quality_constraints") or {})
        chapter_configuration_context = dict(context.get("chapter_configuration_context") or {})
        template_shape_assessment = dict(context.get("template_shape_assessment") or {})
        target_anchor_plan = list(context.get("target_anchor_plan") or [])
        stage_task_definition_json = json.dumps(stage_task_definition, ensure_ascii=False)
        quality_constraints_json = json.dumps(quality_constraints, ensure_ascii=False)
        chapter_configuration_context_json = json.dumps(chapter_configuration_context, ensure_ascii=False)
        template_shape_assessment_json = json.dumps(template_shape_assessment, ensure_ascii=False)
        target_anchor_plan_json = json.dumps(target_anchor_plan, ensure_ascii=False)
        assembled_prompt = (
            f"{prompt.base_contract_text.strip()}\n\n"
            f"{loaded.policy_text.strip()}\n\n"
            f"{prompt.stage_prompt_text.strip()}\n\n"
            f"阶段 ID：{stage_id}\n"
            f"阶段 Prompt ID：{prompt.prompt_id}\n"
            f"阶段上下文 JSON：{context_json}\n"
            f"章节配置上下文 ChapterConfigurationContext JSON：{chapter_configuration_context_json}\n"
            f"阶段任务定义 JSON：{stage_task_definition_json}\n"
            f"阶段质量约束 JSON：{quality_constraints_json}\n"
            f"模板形态评估 TemplateShapeAssessment JSON：{template_shape_assessment_json}\n"
            f"目标锚点规划 TargetAnchorPlan JSON：{target_anchor_plan_json}\n"
            f"阶段采用策略 JSON：{adoption_policy_json}\n"
            f"必须返回且只返回符合此结构的 JSON：{schema_json}"
        )
        bundle = {
            "orchestrator_id": loaded.package.orchestrator_id,
            "mode": loaded.package.mode,
            "stage_id": stage_id,
            "stage_kind": str(stage.get("stage_kind") or ""),
            "prompt_id": prompt.prompt_id,
            "context_json": context_json,
            "schema_json": schema_json,
            "adoption_policy_json": adoption_policy_json,
            "stage_task_definition_json": stage_task_definition_json,
            "quality_constraints_json": quality_constraints_json,
            "chapter_configuration_context_json": chapter_configuration_context_json,
            "template_shape_assessment_json": template_shape_assessment_json,
            "target_anchor_plan_json": target_anchor_plan_json,
            "assembled_prompt": assembled_prompt,
            "base_contract_text": prompt.base_contract_text,
            "policy_text": loaded.policy_text,
            "prompt_text": prompt.stage_prompt_text,
            "stage_prompt_text": prompt.stage_prompt_text,
        }
        if extra_prompt_bundle:
            bundle.update(extra_prompt_bundle)
        return bundle
