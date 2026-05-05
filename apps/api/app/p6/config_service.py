from __future__ import annotations

from app.p6.mock_scenarios import STAGE_METADATA, STAGE_ORDER
from app.p6.models import (
    DesignTokenSet,
    NodeVisualBaseline,
    PlatformDisplayBaselinePackage,
    PlatformLegend,
    PlatformLegendRoadmapItem,
    PlatformLegendSignalItem,
    PlatformRouteItem,
    PlatformRoutes,
    SharedDisplayPrimitive,
    StageNamingBaseline,
    StatusCopyBaseline,
    UpgradeRule,
)


class PlatformConfigService:
    def get_display_baseline(self) -> PlatformDisplayBaselinePackage:
        return PlatformDisplayBaselinePackage(
            version="p6.3-v1",
            token_set=DesignTokenSet(
                token_set_id="p6-platform-token-set",
                color_tokens={
                    "surface_canvas": "#07111f",
                    "surface_panel": "#0f1b2d",
                    "surface_panel_alt": "#16263c",
                    "border_strong": "#2d4b73",
                    "text_primary": "#f8fbff",
                    "text_secondary": "#b9c8da",
                    "state_ready": "#34d399",
                    "state_warning": "#fbbf24",
                    "state_blocked": "#f87171",
                    "state_neutral": "#94a3b8",
                },
                spacing_tokens={
                    "node_gap": "16px",
                    "panel_gap": "20px",
                    "panel_padding": "20px",
                },
                radius_tokens={
                    "card": "24px",
                    "chip": "999px",
                    "panel": "28px",
                },
                shadow_tokens={
                    "card": "0 24px 60px rgba(5, 10, 20, 0.35)",
                    "panel": "0 18px 44px rgba(5, 10, 20, 0.28)",
                },
                typography_tokens={
                    "title": "'IBM Plex Sans', 'Segoe UI', sans-serif",
                    "body": "'Noto Sans SC', 'Segoe UI', sans-serif",
                    "mono": "'IBM Plex Mono', monospace",
                },
                version="p6.3-v1",
            ),
            stage_naming_baseline=StageNamingBaseline(
                baseline_id="p6-stage-naming",
                stage_name_map={stage_id: str(STAGE_METADATA[stage_id]["stage_name"]) for stage_id in STAGE_ORDER},
                forbidden_aliases=["首页", "总控台", "驾驶舱"],
                notes=[
                    "平台页面统一使用 P1 到 P6 正式阶段命名。",
                    "阶段内部业务昵称不得直接进入平台观察面。",
                ],
                version="p6.3-v1",
            ),
            status_copy_baseline=StatusCopyBaseline(
                baseline_id="p6-status-copy",
                platform_status_map={
                    "pending": "待开始",
                    "active": "进行中",
                    "completed": "已完成",
                    "review": "待人工验收",
                    "blocked": "阻塞中",
                    "unavailable": "数据暂不可用",
                },
                state_color_map={
                    "pending": "#94a3b8",
                    "active": "#60a5fa",
                    "completed": "#34d399",
                    "review": "#fbbf24",
                    "blocked": "#f87171",
                    "unavailable": "#64748b",
                },
                feedback_copy_map={
                    "empty": "无数据",
                    "degraded": "数据暂不可用",
                    "stale": "快照已过期",
                    "focus": "切换聚焦阶段以查看比对差异。",
                },
                version="p6.3-v1",
            ),
            shared_display_primitives=[
                SharedDisplayPrimitive(
                    primitive_id="primitive-overview-strip",
                    primitive_kind="overview_strip",
                    supported_states=["fresh", "stale", "unknown"],
                    layout_rules=["横向摘要条", "支持多指标并排展示"],
                    interaction_rules=["只读展示", "点击阶段摘要时允许切换聚焦"],
                    example_refs=["/observation#overview-strip"],
                ),
                SharedDisplayPrimitive(
                    primitive_id="primitive-stage-card",
                    primitive_kind="system_stage_card",
                    supported_states=["healthy", "warning", "blocked", "unknown"],
                    layout_rules=["矩形状态卡", "至少包含主状态与页脚状态"],
                    interaction_rules=["单击高亮", "双击跳转", "悬停联动关系"],
                    example_refs=["/portal#node-stage-card", "/observation#serial-stage-card"],
                ),
                SharedDisplayPrimitive(
                    primitive_id="primitive-user-node",
                    primitive_kind="participant_user_node",
                    supported_states=["manual"],
                    layout_rules=["轻量胶囊", "不展示系统指标栅格"],
                    interaction_rules=["悬停查看上下文", "不承担主链状态判断"],
                    example_refs=["/portal#participant-user-node"],
                ),
                SharedDisplayPrimitive(
                    primitive_id="primitive-alert-panel",
                    primitive_kind="alert_panel",
                    supported_states=["warning", "blocked", "degraded"],
                    layout_rules=["摘要优先", "与降级说明分区显示"],
                    interaction_rules=["支持切换聚焦阶段", "不触发业务写入"],
                    example_refs=["/observation#alert-panel"],
                ),
            ],
            node_visual_baseline=NodeVisualBaseline(
                baseline_id="p6-node-visual-baseline",
                system_stage_card_rules={
                    "shape": "rectangular-card",
                    "required_fields": [
                        "stage_identification",
                        "primary_status",
                        "summary",
                        "core_metrics",
                        "footer_status",
                    ],
                    "visual_priority": "primary",
                    "default_emphasis": "high",
                },
                participant_user_node_rules={
                    "shape": "capsule",
                    "required_fields": ["role", "context", "interaction_direction"],
                    "visual_priority": "secondary",
                    "default_emphasis": "low",
                },
                artifact_node_rules={
                    "shape": "small-card",
                    "required_fields": ["artifact_identity", "linked_relation"],
                    "visual_priority": "secondary",
                },
                status_annotation_node_rules={
                    "shape": "annotation-chip",
                    "required_fields": ["status_or_alert_copy"],
                    "visual_priority": "tertiary",
                },
                state_transition_rules={
                    "default": ["边框清晰", "层级稳定"],
                    "hover": ["轻度增强", "不改变骨架"],
                    "selected": ["强调边框", "关系联动"],
                    "degraded": ["状态标签", "辅助描边"],
                    "blocked": ["状态色强化", "提示文案"],
                },
                size_tiers={
                    "system_stage_card": {"width": 340, "height": 208},
                    "participant_user_node": {"width": 220, "height": 150},
                    "artifact_node": {"width": 180, "height": 84},
                },
            ),
            upgrade_rules=[
                UpgradeRule(
                    rule_id="upgrade-platform-page",
                    applies_to_scope="platform_page",
                    required_primitives=["primitive-overview-strip", "primitive-stage-card", "primitive-alert-panel"],
                    allowed_exceptions=["已登记阶段例外", "实验态预览区"],
                    validation_points=["必须继承 token", "必须使用统一状态文案", "必须区分无数据与数据暂不可用"],
                    priority=1,
                ),
                UpgradeRule(
                    rule_id="upgrade-stage-overview-page",
                    applies_to_scope="stage_overview_page",
                    required_primitives=["primitive-overview-strip", "primitive-stage-card"],
                    allowed_exceptions=["阶段特有业务布局"],
                    validation_points=["平台观察字段统一", "阶段例外显式登记"],
                    priority=2,
                ),
            ],
            exception_rules=[
                {
                    "stage_exception_id": "portal-user-node-lightweight",
                    "applies_to_stage": "P6",
                    "reason": "门户参与用户节点只承担上下文说明，不承担主链指标展示。",
                    "allowed_override": ["participant_user_node_rules.shape", "participant_user_node_rules.required_fields"],
                    "expiry_or_review_rule": "随 P6.3 版本评审复核",
                }
            ],
        )

    def get_routes(self) -> PlatformRoutes:
        stage_routes = {
            stage_id: PlatformRouteItem(
                route_id=f"stage-{stage_id.lower()}",
                label=str(STAGE_METADATA[stage_id]["stage_name"]),
                path=str(STAGE_METADATA[stage_id]["route"]),
                description=f"{stage_id} 稳定模块入口",
            )
            for stage_id in STAGE_ORDER
        }
        return PlatformRoutes(
            portal_route=PlatformRouteItem(
                route_id="portal",
                label="P6 首屏观察门户",
                path="/portal",
                description="门户蓝图、节点关系与入口导览。",
            ),
            observation_route=PlatformRouteItem(
                route_id="observation",
                label="P6 串行观察页",
                path="/observation",
                description="顺序观察、对比与告警摘要。",
            ),
            stage_routes=stage_routes,
        )

    def get_legend(self) -> PlatformLegend:
        return PlatformLegend(
            summary_copy="门户只负责导览与跳转，不承载业务编辑。双击节点即可进入对应模块。",
            interaction_facts=[
                "单击高亮 / 双击进入 / 滚轮缩放 / 背景平移",
                "节点拖拽仅在自动布局区内生效，超界后自动回收",
            ],
            element_language_copy="矩形状态卡 = 系统节点，轻量胶囊 = 参与用户，小胶囊 = 数据产物",
            signal_items=[
                PlatformLegendSignalItem(tone="knowledge", label="主链通畅", detail="五阶段主链保持可观察流动"),
                PlatformLegendSignalItem(tone="tooling", label="评审压力 72%", detail="P3 评审压力作为底部状态信号展示"),
                PlatformLegendSignalItem(tone="analysis", label="模拟源驱动", detail="当前页面由 P6 mock projection 驱动"),
                PlatformLegendSignalItem(tone="delivery", label="最近刷新 18 秒前", detail="门户投影新鲜度提示"),
            ],
            roadmap_items=[
                PlatformLegendRoadmapItem(item_id="p6-r1", label="统一登录接入", status="后置"),
                PlatformLegendRoadmapItem(item_id="p6-r2", label="权限与角色控制", status="后置"),
                PlatformLegendRoadmapItem(item_id="p6-ops", label="入口与导航治理", status="逐步纳入"),
            ],
        )
