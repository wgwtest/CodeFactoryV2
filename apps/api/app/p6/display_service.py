from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from itertools import count

from app.p6.models import (
    DisplayExperimentCreateRequest,
    DisplayExperimentList,
    DisplayExperimentRecord,
    DisplayPromotionCandidate,
    DisplayPromotionCandidateList,
    DisplayWidgetBinding,
    DisplayWidgetLayout,
    DisplayWidgetPreset,
    DisplayWidgetTemplate,
    DisplayWorkbenchBootstrap,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_TEMPLATES = [
    DisplayWidgetTemplate(
        template_id="template-module-status",
        template_name="系统状态卡",
        template_kind="module_card",
        slot_schema=["header", "headline", "summary", "metrics", "footer"],
        supported_field_map={
            "stage": "stage_id",
            "status": "primary_status",
            "summary": "summary_line",
            "metrics": "metric_items",
            "footer": "health_badge",
        },
        supported_states=["healthy", "warning", "blocked", "unknown"],
        style_profile_ref="node-visual-baseline.system_stage_card_rules",
    ),
    DisplayWidgetTemplate(
        template_id="template-module-compact",
        template_name="压缩状态卡",
        template_kind="module_card",
        slot_schema=["header", "summary", "footer"],
        supported_field_map={
            "stage": "stage_id",
            "summary": "summary_line",
            "badge": "health_badge",
        },
        supported_states=["healthy", "warning", "blocked", "unknown"],
        style_profile_ref="node-visual-baseline.system_stage_card_rules",
    ),
    DisplayWidgetTemplate(
        template_id="template-module-overview",
        template_name="概览卡",
        template_kind="module_card",
        slot_schema=["header", "summary", "description", "footer"],
        supported_field_map={
            "stage": "stage_id",
            "summary": "summary_line",
            "description": "summary",
            "footer": "health_badge",
        },
        supported_states=["healthy", "warning", "blocked", "unknown"],
        style_profile_ref="node-visual-baseline.system_stage_card_rules",
    ),
    DisplayWidgetTemplate(
        template_id="template-user-capsule",
        template_name="参与用户胶囊",
        template_kind="participant_card",
        slot_schema=["role", "context", "interaction_hints"],
        supported_field_map={
            "role": "role_label",
            "context": "context_label",
            "interaction_hints": "interaction_hints",
        },
        supported_states=["manual"],
        style_profile_ref="node-visual-baseline.participant_user_node_rules",
    ),
    DisplayWidgetTemplate(
        template_id="template-user-card",
        template_name="参与用户信息卡",
        template_kind="participant_card",
        slot_schema=["role", "context", "interaction_hints", "availability"],
        supported_field_map={
            "role": "role_label",
            "context": "context_label",
            "interaction_hints": "interaction_hints",
            "availability": "availability_hint",
        },
        supported_states=["manual"],
        style_profile_ref="node-visual-baseline.participant_user_node_rules",
    ),
]

_BINDINGS = [
    DisplayWidgetBinding(
        binding_id="binding-portal-full",
        source_projection_kind="PortalProjection",
        source_stage_scope="all-stages",
        field_map={
            "headline": "stage_card.headline_value",
            "summary": "stage_card.summary_line",
            "metrics": "stage_card.metric_items",
            "health": "stage_card.health_badge",
        },
        transform_rules=["metrics -> top 2", "freshness -> badge copy"],
        fallback_rules=["empty metrics -> hide metrics region", "missing degraded hint -> omit degraded slot"],
    ),
    DisplayWidgetBinding(
        binding_id="binding-portal-summary",
        source_projection_kind="PortalProjection",
        source_stage_scope="all-stages",
        field_map={
            "headline": "stage_card.headline_value",
            "summary": "stage_card.summary_line",
            "health": "stage_card.health_badge",
        },
        transform_rules=["metrics -> top 1"],
        fallback_rules=["missing summary -> use stage summary"],
    ),
    DisplayWidgetBinding(
        binding_id="binding-observation-alert",
        source_projection_kind="ObservationProjection",
        source_stage_scope="focus-stage",
        field_map={
            "headline": "headline_value",
            "summary": "summary_line",
            "health": "health_badge",
            "timestamp": "timestamp_label",
        },
        transform_rules=["blocked stage -> emphasize alert copy", "focus stage -> keep first card"],
        fallback_rules=["missing stage card -> show unavailable badge"],
    ),
]

_LAYOUTS = [
    DisplayWidgetLayout(
        layout_id="layout-single",
        layout_name="单卡预览",
        region_schema=["primary"],
        ordering_rules=["keep current target first"],
        size_rules=["primary fills preview canvas"],
        responsive_rules=["mobile stacks summary under preview"],
    ),
    DisplayWidgetLayout(
        layout_id="layout-compare",
        layout_name="双卡对比",
        region_schema=["baseline", "candidate"],
        ordering_rules=["baseline left", "candidate right"],
        size_rules=["two equal cards"],
        responsive_rules=["mobile collapses to vertical compare"],
    ),
]

_PRESETS = [
    DisplayWidgetPreset(
        preset_id="preset-portal-baseline",
        preset_name="门户标准观察卡",
        applicable_scenarios=["baseline", "review-pressure", "delivery-gap"],
        template_refs=["template-module-status"],
        binding_refs=["binding-portal-full"],
        layout_refs=["layout-single"],
        status="active",
    ),
    DisplayWidgetPreset(
        preset_id="preset-observation-alert",
        preset_name="观察告警对比卡",
        applicable_scenarios=["review-pressure", "delivery-gap"],
        template_refs=["template-module-compact"],
        binding_refs=["binding-observation-alert"],
        layout_refs=["layout-compare"],
        status="candidate",
    ),
]

_EXPERIMENTS = [
    DisplayExperimentRecord(
        experiment_id="exp-portal-baseline",
        goal="验证门户系统状态卡是否可以在不改写阶段事实的前提下保持统一展示。",
        projection_scope="PortalProjection",
        template_refs=["template-module-status"],
        binding_refs=["binding-portal-full"],
        layout_refs=["layout-single"],
        preset_refs=["preset-portal-baseline"],
        result_summary="系统状态卡适合门户首屏，能够稳定承载阶段识别、摘要和健康状态。",
        issues=["参与用户节点需要维持更低视觉权重，避免与系统节点争主位。"],
        promotion_recommendation="candidate",
        target_stage_ids=["P3", "P4", "P5"],
        evidence_refs=["portal:baseline", "baseline:node-visual-baseline"],
        created_at="2026-04-21T02:18:00+08:00",
    )
]

_PROMOTION_CANDIDATES = [
    DisplayPromotionCandidate(
        promotion_candidate_id="candidate-portal-baseline",
        source_experiment_id="exp-portal-baseline",
        candidate_kind="template_preset",
        target_stage_ids=["P3", "P4", "P5"],
        adoption_reason="门户系统状态卡已经具备可复用的模板、绑定和布局组合。",
        evidence_refs=["portal:baseline", "baseline:node-visual-baseline"],
        status="ready_for_stage_adoption",
    )
]

_EXPERIMENT_COUNTER = count(2)
_CANDIDATE_COUNTER = count(2)


class PlatformDisplayService:
    def get_workbench(self) -> DisplayWorkbenchBootstrap:
        return DisplayWorkbenchBootstrap(
            version="p6.4-v1",
            templates=deepcopy(_TEMPLATES),
            bindings=deepcopy(_BINDINGS),
            layouts=deepcopy(_LAYOUTS),
            presets=deepcopy(_PRESETS),
            experiments=deepcopy(_EXPERIMENTS),
            promotion_candidates=deepcopy(_PROMOTION_CANDIDATES),
        )

    def list_experiments(self) -> DisplayExperimentList:
        return DisplayExperimentList(items=deepcopy(_EXPERIMENTS))

    def list_promotion_candidates(self) -> DisplayPromotionCandidateList:
        return DisplayPromotionCandidateList(items=deepcopy(_PROMOTION_CANDIDATES))

    def create_experiment(self, request: DisplayExperimentCreateRequest) -> DisplayExperimentRecord:
        experiment = DisplayExperimentRecord(
            experiment_id=f"exp-{next(_EXPERIMENT_COUNTER):04d}",
            goal=request.goal,
            projection_scope=request.projection_scope,
            template_refs=list(request.template_refs),
            binding_refs=list(request.binding_refs),
            layout_refs=list(request.layout_refs),
            preset_refs=list(request.preset_refs),
            result_summary=request.result_summary,
            issues=list(request.issues),
            promotion_recommendation=request.promotion_recommendation,
            target_stage_ids=list(request.target_stage_ids),
            evidence_refs=list(request.evidence_refs),
            created_at=_utc_now(),
        )
        _EXPERIMENTS.append(experiment)

        if request.promotion_recommendation == "candidate":
            _PROMOTION_CANDIDATES.append(
                DisplayPromotionCandidate(
                    promotion_candidate_id=f"candidate-{next(_CANDIDATE_COUNTER):04d}",
                    source_experiment_id=experiment.experiment_id,
                    candidate_kind="template_preset",
                    target_stage_ids=list(request.target_stage_ids),
                    adoption_reason=request.result_summary,
                    evidence_refs=list(request.evidence_refs),
                    status="ready_for_stage_adoption",
                )
            )

        return deepcopy(experiment)
