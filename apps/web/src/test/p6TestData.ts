export function buildScenarioCatalog() {
  return {
    source_mode: "mock",
    default_scenario_id: "baseline",
    items: [
      {
        scenario_id: "baseline",
        label: "基线通畅",
        description: "主链通畅，五阶段入口可用。",
        source_mode: "mock",
        recommended_focus_stage: "P2",
      },
      {
        scenario_id: "review-pressure",
        label: "评审压力",
        description: "P3 评审积压，P4 跟进承压。",
        source_mode: "mock",
        recommended_focus_stage: "P3",
      },
      {
        scenario_id: "delivery-gap",
        label: "交付缺口",
        description: "P5 出现交付缺口，P4 与 P5 告警升高。",
        source_mode: "mock",
        recommended_focus_stage: "P5",
      },
    ],
  };
}

export function buildDisplayBaseline() {
  return {
    version: "p6.3-v1",
    token_set: {
      token_set_id: "p6-platform-token-set",
      color_tokens: {
        surface_canvas: "#07111f",
        surface_panel: "#0f1b2d",
        surface_panel_alt: "#16263c",
        border_strong: "#2d4b73",
        text_primary: "#f8fbff",
        text_secondary: "#b9c8da",
        state_ready: "#34d399",
        state_warning: "#fbbf24",
        state_blocked: "#f87171",
        state_neutral: "#94a3b8",
      },
      spacing_tokens: {
        node_gap: "16px",
        panel_gap: "20px",
        panel_padding: "20px",
      },
      radius_tokens: {
        card: "24px",
        chip: "999px",
        panel: "28px",
      },
      shadow_tokens: {
        card: "0 24px 60px rgba(5, 10, 20, 0.35)",
        panel: "0 18px 44px rgba(5, 10, 20, 0.28)",
      },
      typography_tokens: {
        title: "'IBM Plex Sans', 'Segoe UI', sans-serif",
        body: "'Noto Sans SC', 'Segoe UI', sans-serif",
        mono: "'IBM Plex Mono', monospace",
      },
      version: "p6.3-v1",
    },
    stage_naming_baseline: {
      baseline_id: "p6-stage-naming",
      stage_name_map: {
        P1: "业务知识库",
        P2: "需求分析系统",
        P3: "软件设计系统",
        P4: "工具仓库 / 工具中台",
        P5: "软件构建系统",
      },
      forbidden_aliases: ["首页", "总控台", "驾驶舱"],
      notes: ["平台页面统一使用 P1 到 P6 正式阶段命名。"],
      version: "p6.3-v1",
    },
    status_copy_baseline: {
      baseline_id: "p6-status-copy",
      platform_status_map: {
        pending: "待开始",
        active: "进行中",
        completed: "已完成",
        review: "待人工验收",
        blocked: "阻塞中",
        unavailable: "数据暂不可用",
      },
      state_color_map: {
        pending: "#94a3b8",
        active: "#60a5fa",
        completed: "#34d399",
        review: "#fbbf24",
        blocked: "#f87171",
        unavailable: "#64748b",
      },
      feedback_copy_map: {
        empty: "无数据",
        degraded: "数据暂不可用",
        stale: "快照已过期",
        focus: "切换聚焦阶段以查看比对差异。",
      },
      version: "p6.3-v1",
    },
    shared_display_primitives: [],
    node_visual_baseline: {
      baseline_id: "p6-node-visual-baseline",
      system_stage_card_rules: {
        shape: "rectangular-card",
        required_fields: ["stage_identification", "primary_status", "summary", "core_metrics", "footer_status"],
      },
      participant_user_node_rules: {
        shape: "capsule",
      },
      artifact_node_rules: {
        shape: "small-card",
      },
      status_annotation_node_rules: {
        shape: "annotation-chip",
      },
      state_transition_rules: {
        blocked: ["状态色强化", "提示文案"],
      },
      size_tiers: {
        system_stage_card: { width: 340, height: 208 },
        participant_user_node: { width: 220, height: 150 },
      },
    },
    upgrade_rules: [
      {
        rule_id: "upgrade-platform-page",
        applies_to_scope: "platform_page",
        required_primitives: ["primitive-overview-strip", "primitive-stage-card", "primitive-alert-panel"],
        allowed_exceptions: ["实验态预览区"],
        validation_points: ["必须继承 token", "必须使用统一状态文案"],
        priority: 1,
      },
    ],
    exception_rules: [],
  };
}

export function buildPlatformRoutes() {
  return {
    portal_route: {
      route_id: "portal",
      label: "P6 首屏观察门户",
      path: "/portal",
      description: "门户蓝图、节点关系与入口导览。",
      entry_available: true,
    },
    observation_route: {
      route_id: "observation",
      label: "P6 串行观察页",
      path: "/observation",
      description: "顺序观察、对比与告警摘要。",
      entry_available: true,
    },
    stage_routes: {
      P1: { route_id: "stage-p1", label: "业务知识库", path: "/graph", description: "P1 稳定模块入口", entry_available: true },
      P2: { route_id: "stage-p2", label: "需求分析系统", path: "/requirements", description: "P2 稳定模块入口", entry_available: true },
      P3: { route_id: "stage-p3", label: "软件设计系统", path: "/modeling", description: "P3 稳定模块入口", entry_available: true },
      P4: { route_id: "stage-p4", label: "工具仓库 / 工具中台", path: "/xx-p4", description: "P4 稳定模块入口", entry_available: true },
      P5: { route_id: "stage-p5", label: "软件构建系统", path: "/build", description: "P5 稳定模块入口", entry_available: true },
    },
  };
}

export function buildPlatformLegend() {
  return {
    summary_copy: "门户只负责导览与跳转，不承载业务编辑。双击节点即可进入对应模块。",
    interaction_facts: [
      "单击高亮 / 双击进入 / 滚轮缩放 / 背景平移",
      "节点拖拽仅在自动布局区内生效，超界后自动回收",
    ],
    element_language_copy: "矩形状态卡 = 系统节点，轻量胶囊 = 参与用户，小胶囊 = 数据产物",
    signal_items: [
      { tone: "knowledge", label: "知识供给", detail: "P1 到 P2 的知识输入" },
      { tone: "analysis", label: "需求分析", detail: "需求进入与规格说明" },
      { tone: "design", label: "设计转化", detail: "设计输出到构建与说明" },
      { tone: "tooling", label: "工具匹配", detail: "工具供给与匹配链" },
      { tone: "delivery", label: "构建执行", detail: "交付执行与缺口反馈" },
    ],
    roadmap_items: [
      { item_id: "p6-r1", label: "统一登录接入", status: "后置" },
      { item_id: "p6-r2", label: "权限与角色控制", status: "后置" },
      { item_id: "p6-ops", label: "入口与导航治理", status: "逐步纳入" },
    ],
  };
}

export function buildWorkbenchBootstrap() {
  return {
    version: "p6.4-v1",
    templates: [
      {
        template_id: "template-module-status",
        template_name: "系统状态卡",
        template_kind: "module_card",
        slot_schema: ["header", "headline", "summary", "metrics", "footer"],
        supported_field_map: {
          stage: "stage_id",
          status: "primary_status",
          summary: "summary_line",
          metrics: "metric_items",
          footer: "health_badge",
        },
        supported_states: ["healthy", "warning", "blocked", "unknown"],
        style_profile_ref: "node-visual-baseline.system_stage_card_rules",
      },
      {
        template_id: "template-module-compact",
        template_name: "压缩状态卡",
        template_kind: "module_card",
        slot_schema: ["header", "summary", "footer"],
        supported_field_map: {
          stage: "stage_id",
          summary: "summary_line",
          badge: "health_badge",
        },
        supported_states: ["healthy", "warning", "blocked", "unknown"],
        style_profile_ref: "node-visual-baseline.system_stage_card_rules",
      },
      {
        template_id: "template-module-overview",
        template_name: "概览卡",
        template_kind: "module_card",
        slot_schema: ["header", "summary", "description", "footer"],
        supported_field_map: {
          stage: "stage_id",
          summary: "summary_line",
          description: "summary",
          footer: "health_badge",
        },
        supported_states: ["healthy", "warning", "blocked", "unknown"],
        style_profile_ref: "node-visual-baseline.system_stage_card_rules",
      },
      {
        template_id: "template-user-capsule",
        template_name: "参与用户胶囊",
        template_kind: "participant_card",
        slot_schema: ["role", "context", "interaction_hints"],
        supported_field_map: {
          role: "role_label",
          context: "context_label",
          interaction_hints: "interaction_hints",
        },
        supported_states: ["manual"],
        style_profile_ref: "node-visual-baseline.participant_user_node_rules",
      },
      {
        template_id: "template-user-card",
        template_name: "参与用户信息卡",
        template_kind: "participant_card",
        slot_schema: ["role", "context", "interaction_hints", "availability"],
        supported_field_map: {
          role: "role_label",
          context: "context_label",
          interaction_hints: "interaction_hints",
          availability: "availability_hint",
        },
        supported_states: ["manual"],
        style_profile_ref: "node-visual-baseline.participant_user_node_rules",
      },
    ],
    bindings: [
      {
        binding_id: "binding-portal-full",
        source_projection_kind: "PortalProjection",
        source_stage_scope: "all-stages",
        field_map: {
          headline: "stage_card.headline_value",
          summary: "stage_card.summary_line",
          metrics: "stage_card.metric_items",
          health: "stage_card.health_badge",
        },
        transform_rules: ["metrics -> top 2", "freshness -> badge copy"],
        fallback_rules: ["empty metrics -> hide metrics region"],
      },
      {
        binding_id: "binding-portal-summary",
        source_projection_kind: "PortalProjection",
        source_stage_scope: "all-stages",
        field_map: {
          headline: "stage_card.headline_value",
          summary: "stage_card.summary_line",
          health: "stage_card.health_badge",
        },
        transform_rules: ["metrics -> top 1"],
        fallback_rules: ["missing summary -> use stage summary"],
      },
      {
        binding_id: "binding-observation-alert",
        source_projection_kind: "ObservationProjection",
        source_stage_scope: "focus-stage",
        field_map: {
          headline: "headline_value",
          summary: "summary_line",
          health: "health_badge",
          timestamp: "timestamp_label",
        },
        transform_rules: ["blocked stage -> emphasize alert copy"],
        fallback_rules: ["missing stage card -> show unavailable badge"],
      },
    ],
    layouts: [
      {
        layout_id: "layout-single",
        layout_name: "单卡预览",
        region_schema: ["primary"],
        ordering_rules: ["keep current target first"],
        size_rules: ["primary fills preview canvas"],
        responsive_rules: ["mobile stacks summary under preview"],
      },
      {
        layout_id: "layout-compare",
        layout_name: "双卡对比",
        region_schema: ["baseline", "candidate"],
        ordering_rules: ["baseline left", "candidate right"],
        size_rules: ["two equal cards"],
        responsive_rules: ["mobile collapses to vertical compare"],
      },
    ],
    presets: [
      {
        preset_id: "preset-portal-baseline",
        preset_name: "门户标准观察卡",
        applicable_scenarios: ["baseline", "review-pressure", "delivery-gap"],
        template_refs: ["template-module-status"],
        binding_refs: ["binding-portal-full"],
        layout_refs: ["layout-single"],
        status: "active",
      },
      {
        preset_id: "preset-observation-alert",
        preset_name: "观察告警对比卡",
        applicable_scenarios: ["review-pressure", "delivery-gap"],
        template_refs: ["template-module-compact"],
        binding_refs: ["binding-observation-alert"],
        layout_refs: ["layout-compare"],
        status: "candidate",
      },
    ],
    experiments: [
      {
        experiment_id: "exp-portal-baseline",
        goal: "验证门户系统状态卡是否可以在不改写阶段事实的前提下保持统一展示。",
        projection_scope: "PortalProjection",
        template_refs: ["template-module-status"],
        binding_refs: ["binding-portal-full"],
        layout_refs: ["layout-single"],
        preset_refs: ["preset-portal-baseline"],
        result_summary: "系统状态卡适合门户首屏，能够稳定承载阶段识别、摘要和健康状态。",
        issues: ["参与用户节点需要维持更低视觉权重，避免与系统节点争主位。"],
        promotion_recommendation: "candidate",
        target_stage_ids: ["P3", "P4", "P5"],
        evidence_refs: ["portal:baseline", "baseline:node-visual-baseline"],
        created_at: "2026-04-21T02:18:00+08:00",
      },
    ],
    promotion_candidates: [
      {
        promotion_candidate_id: "candidate-portal-baseline",
        source_experiment_id: "exp-portal-baseline",
        candidate_kind: "template_preset",
        target_stage_ids: ["P3", "P4", "P5"],
        adoption_reason: "门户系统状态卡已经具备可复用的模板、绑定和布局组合。",
        evidence_refs: ["portal:baseline", "baseline:node-visual-baseline"],
        status: "ready_for_stage_adoption",
      },
    ],
  };
}

export function buildPortalProjectionEnvelope(scenarioId: string) {
  const isDeliveryGap = scenarioId === "delivery-gap";
  const isReviewPressure = scenarioId === "review-pressure";
  const scenarioLabel = isDeliveryGap ? "交付缺口" : isReviewPressure ? "评审压力" : "基线通畅";

  const nodes = [
    {
      node_id: "user",
      node_kind: "user",
      title: "行业用户",
      projection_mode: "manual",
      summary: "以业务语言提出目标并进入平台主链。",
      description: "门户中的参与角色节点。",
      participant_payload: {
        role_label: "参与角色",
        title: "行业用户",
        context_label: `模拟源 · ${scenarioLabel}`,
        interaction_hints: ["提出目标", "确认对象", "进入需求"],
        availability_hint: "持续接入",
      },
    },
    {
      node_id: "p1",
      node_kind: "module",
      title: "业务知识库",
      stage_id: "P1",
      route: "/graph",
      projection_mode: "auto",
      summary: "知识供给稳定对外发布。",
      primary_status: "knowledge_published",
      freshness: "fresh",
      description: "负责沉淀领域知识并向后续阶段提供稳定知识供给。",
      stage_card: {
        stage_id: "P1",
        headline_value: "NAS 战术知识库 v3",
        summary_line: "当前知识库已进入对外供给态。",
        metric_items: [
          { metric_key: "published_knowledge_count", metric_label: "已发布知识", metric_value: "132" },
          { metric_key: "source_document_count", metric_label: "来源文档", metric_value: "28" },
        ],
        entry_badge: { label: "图谱入口可用", tone: "ready" },
        health_badge: { label: "健康", tone: "ready", detail: "最新知识发布已完成。" },
        timestamp_label: "发布于 04-21 09:15",
        degraded_hint: null,
      },
    },
    {
      node_id: "p2",
      node_kind: "module",
      title: "需求分析系统",
      stage_id: "P2",
      route: "/requirements",
      projection_mode: "auto",
      summary: "需求批次建模进度稳定。",
      primary_status: "requirements_modeling",
      freshness: "fresh",
      description: "把业务语言建模为结构化需求规格与需求对象。",
      stage_card: {
        stage_id: "P2",
        headline_value: "无人协同批次 A",
        summary_line: "规格草案已进入稳定整理阶段。",
        metric_items: [
          { metric_key: "active_requirement_count", metric_label: "活跃需求", metric_value: "7" },
          { metric_key: "modeled_requirement_count", metric_label: "已建模", metric_value: "5" },
        ],
        entry_badge: { label: "需求入口可用", tone: "ready" },
        health_badge: { label: "健康", tone: "ready", detail: "需求建模批次运行平稳。" },
        timestamp_label: "分析于 04-21 09:28",
        degraded_hint: null,
      },
    },
    {
      node_id: "p3",
      node_kind: "module",
      title: "软件设计系统",
      stage_id: "P3",
      route: "/modeling",
      projection_mode: "auto",
      summary: isReviewPressure ? "设计评审积压，冻结单等待批阅。" : "设计单冻结后进入评审流。",
      primary_status: isReviewPressure ? "review_backlog" : "design_review_active",
      freshness: "fresh",
      description: "承接需求规格并输出软件设计说明与设计结构表达。",
      stage_card: {
        stage_id: "P3",
        headline_value: isReviewPressure ? "设计单 SO-240421-05" : "设计单 SO-240421-02",
        summary_line: isReviewPressure ? "冻结设计单进入评审积压队列。" : "当前设计单已冻结并进入评审。",
        metric_items: [
          { metric_key: "active_design_order_count", metric_label: "活跃设计单", metric_value: isReviewPressure ? "4" : "3" },
          { metric_key: "review_pending_count", metric_label: "待评审", metric_value: isReviewPressure ? "6" : "1" },
        ],
        entry_badge: { label: "软设入口可用", tone: "ready" },
        health_badge: {
          label: isReviewPressure ? "注意" : "健康",
          tone: isReviewPressure ? "warning" : "ready",
          detail: isReviewPressure ? "设计评审积压增加。" : "设计评审节奏正常。",
        },
        timestamp_label: isReviewPressure ? "积压于 04-21 10:16" : "评审于 04-21 09:42",
        degraded_hint: null,
      },
    },
    {
      node_id: "p4",
      node_kind: "module",
      title: "工具仓库 / 工具中台",
      stage_id: "P4",
      route: "/xx-p4",
      projection_mode: "auto",
      summary: isDeliveryGap ? "供给命中率下降，部分工具需求待补齐。" : "供给快照与工具匹配结果可用。",
      primary_status: isDeliveryGap ? "supply_gap_warning" : "tool_snapshot_ready",
      freshness: "fresh",
      description: "沉淀工具供给与能力匹配规则。",
      stage_card: {
        stage_id: "P4",
        headline_value: isDeliveryGap ? "供给快照 SUP-240421-C" : "供给快照 SUP-240421-A",
        summary_line: isDeliveryGap ? "供给命中不足，需回补能力项。" : "工具匹配结果已推送给构建链。",
        metric_items: [
          { metric_key: "active_supply_snapshot_count", metric_label: "供给快照", metric_value: isDeliveryGap ? "3" : "4" },
          { metric_key: "tool_demand_open_count", metric_label: "开放需求单", metric_value: isDeliveryGap ? "7" : "2" },
        ],
        entry_badge: { label: "工具仓入口可用", tone: "ready" },
        health_badge: {
          label: isDeliveryGap ? "注意" : "健康",
          tone: isDeliveryGap ? "warning" : "ready",
          detail: isDeliveryGap ? "供给链存在待补位需求。" : "供给快照与工具匹配链路稳定。",
        },
        timestamp_label: isDeliveryGap ? "告警于 04-21 10:24" : "巡检于 04-21 09:56",
        degraded_hint: null,
      },
    },
    {
      node_id: "p5",
      node_kind: "module",
      title: "软件构建系统",
      stage_id: "P5",
      route: "/build",
      projection_mode: "auto",
      summary: isDeliveryGap ? "交付主单执行受阻，缺口待人工确认。" : "构建主单已具备执行条件。",
      primary_status: isDeliveryGap ? "delivery_gap_blocked" : "delivery_ready",
      freshness: "fresh",
      description: "整合设计、工具与交付链路，产出构建结果与缺口反馈。",
      stage_card: {
        stage_id: "P5",
        headline_value: isDeliveryGap ? "交付主单 DO-240421-04" : "交付主单 DO-240421-01",
        summary_line: isDeliveryGap ? "最近一次尝试暴露关键交付缺口。" : "最新交付主单已具备执行窗口。",
        metric_items: [
          { metric_key: "active_delivery_order_count", metric_label: "活跃交付单", metric_value: "2" },
          { metric_key: "review_pending_attempt_count", metric_label: "待批阅尝试", metric_value: isDeliveryGap ? "3" : "0" },
        ],
        entry_badge: { label: "构建入口可用", tone: "ready" },
        health_badge: {
          label: isDeliveryGap ? "阻塞" : "健康",
          tone: isDeliveryGap ? "blocked" : "ready",
          detail: isDeliveryGap ? "关键交付缺口未闭合。" : "构建主链可执行。",
        },
        timestamp_label: isDeliveryGap ? "缺口于 04-21 10:27" : "交付于 04-21 10:05",
        degraded_hint: isDeliveryGap ? "需人工确认缺口与回补路径。" : null,
      },
    },
  ];

  return {
    source_mode: "mock",
    scenario: {
      scenario_id: scenarioId,
      label: scenarioLabel,
      description: isDeliveryGap ? "P5 出现交付缺口，P4 与 P5 告警升高。" : "主链通畅，五阶段入口可用。",
      source_mode: "mock",
      recommended_focus_stage: isDeliveryGap ? "P5" : isReviewPressure ? "P3" : "P2",
    },
    projection: {
      node_list: nodes,
      flow_list: [
        {
          flow_id: "user-p2",
          from_node_id: "user",
          to_node_id: "p2",
          semantic_type: "participant_input",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "analysis",
          render_style: "solid",
          label: "需求进入",
        },
        {
          flow_id: "p1-p2",
          from_node_id: "p1",
          to_node_id: "p2",
          semantic_type: "knowledge_supply",
          direction: "forward",
          from_pin: "top",
          to_pin: "bottom",
          render_tone: "knowledge",
          render_style: "dashed",
          label: "知识供给",
        },
        {
          flow_id: "p2-p3",
          from_node_id: "p2",
          to_node_id: "p3",
          semantic_type: "requirement_to_design",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "analysis",
          render_style: "solid",
          label: "规格说明",
        },
        {
          flow_id: "p3-p4",
          from_node_id: "p3",
          to_node_id: "p4",
          semantic_type: "tool_match",
          direction: "forward",
          from_pin: "bottom",
          to_pin: "top",
          render_tone: "tooling",
          render_style: "dashed",
          label: "工具匹配",
        },
        {
          flow_id: "p4-p5",
          from_node_id: "p4",
          to_node_id: "p5",
          semantic_type: "delivery_execution",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "delivery",
          render_style: "solid",
          label: "构建执行",
        },
        {
          flow_id: "p3-p5",
          from_node_id: "p3",
          to_node_id: "p5",
          semantic_type: "design_projection",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "design",
          render_style: "solid",
          label: "设计落地",
        },
      ],
      artifact_list: [
        {
          artifact_id: "spec",
          artifact_kind: "requirement_spec",
          title: "需求规格说明",
          summary: "从需求建模投影出的结构化规格。",
          linked_node_ids: ["p2", "p3"],
          source_mode: "mock",
          render_tone: "analysis",
          projection_mode: "auto",
        },
        {
          artifact_id: "design",
          artifact_kind: "software_design_spec",
          title: "软件设计说明",
          summary: "从规格说明转化出的设计表达。",
          linked_node_ids: ["p3", "p5"],
          source_mode: "mock",
          render_tone: "design",
          projection_mode: "auto",
        },
        {
          artifact_id: "tooling",
          artifact_kind: "tooling_projection",
          title: "工具化描述 / 调用编排",
          summary: "驱动工具中台与构建执行的调用对象。",
          linked_node_ids: ["p3", "p4", "p5"],
          source_mode: "mock",
          render_tone: "tooling",
          projection_mode: "auto",
        },
      ],
      portal_summary: {
        headline: "P6 首屏观察门户",
        source_label: "模拟源",
        scenario_label: scenarioLabel,
        module_count: 5,
        user_count: 1,
        artifact_count: 3,
        flow_count: 6,
        focus_hint: isDeliveryGap ? "建议优先关注 P5" : isReviewPressure ? "建议优先关注 P3" : "建议优先关注 P2",
        alert_message: isDeliveryGap
          ? "交付链出现缺口，建议优先处理 P5 并回看 P4 供给命中。"
          : isReviewPressure
            ? "评审与供给跟进出现压力，建议优先关注 P3 到 P4。"
            : "当前模拟源显示主链通畅，可直接观察整体投影。",
      },
      knowledge_context: {
        current_knowledge_base_name: "NAS 战术知识库 v3",
        archive_label: "平台模拟知识库",
        context_hint: `模拟源 · ${scenarioLabel}`,
      },
      freshness: "fresh",
      degraded_reason: isDeliveryGap ? "需人工确认缺口与回补路径。" : null,
    },
  };
}

export function buildObservationProjectionEnvelope(scenarioId: string) {
  const portalEnvelope = buildPortalProjectionEnvelope(scenarioId);
  const isDeliveryGap = scenarioId === "delivery-gap";
  const isReviewPressure = scenarioId === "review-pressure";
  const stageCards = portalEnvelope.projection.node_list
    .filter(
      (
        item,
      ): item is (typeof portalEnvelope.projection.node_list)[number] & {
        node_kind: "module";
        stage_id: string;
        stage_card: NonNullable<(typeof item)["stage_card"]>;
      } => item.node_kind === "module" && typeof item.stage_id === "string" && item.stage_card !== null,
    )
    .map((item) => ({
      stage_id: item.stage_id,
      stage_name: item.title,
      headline_value: item.stage_card.headline_value,
      summary_line: item.stage_card.summary_line,
      primary_status: item.primary_status ?? "unknown",
      freshness: item.freshness ?? "unknown",
      entry_badge: item.stage_card.entry_badge,
      health_badge: item.stage_card.health_badge,
      timestamp_label: item.stage_card.timestamp_label,
      degraded_hint: item.stage_card.degraded_hint,
    }));

  return {
    source_mode: "mock",
    scenario: portalEnvelope.scenario,
    projection: {
      stage_cards: stageCards,
      comparison_items: [
        { comparison_id: "entry-available", label: "可用入口", value: "5/5", tone: "ready" },
        {
          comparison_id: "warning-stage-count",
          label: "注意阶段",
          value: isDeliveryGap ? "1" : isReviewPressure ? "2" : "0",
          tone: isDeliveryGap || isReviewPressure ? "warning" : "neutral",
        },
        {
          comparison_id: "blocked-stage-count",
          label: "阻塞阶段",
          value: isDeliveryGap ? "1" : "0",
          tone: isDeliveryGap ? "blocked" : "neutral",
        },
      ],
      alert_summary: {
        total: isDeliveryGap ? 2 : isReviewPressure ? 2 : 0,
        warning_stage_ids: isReviewPressure ? ["P3", "P4"] : isDeliveryGap ? ["P4"] : [],
        blocked_stage_ids: isDeliveryGap ? ["P5"] : [],
        message: isDeliveryGap
          ? "交付链出现缺口，建议优先处理 P5 并回看 P4 供给命中。"
          : isReviewPressure
            ? "评审与供给跟进出现压力，建议优先关注 P3 到 P4。"
            : "当前模拟源显示主链通畅，可直接观察整体投影。",
      },
      route_actions: stageCards.map((card) => ({
        stage_id: card.stage_id,
        label: `进入 ${card.stage_name}`,
        route: card.stage_id === "P1"
          ? "/graph"
          : card.stage_id === "P2"
            ? "/requirements"
            : card.stage_id === "P3"
              ? "/modeling"
              : card.stage_id === "P4"
                ? "/xx-p4"
                : "/build",
        route_available: true,
      })),
      focus_stage_id: isDeliveryGap ? "P5" : isReviewPressure ? "P3" : "P2",
      freshness: "fresh",
      degraded_reason: isDeliveryGap ? "需人工确认缺口与回补路径。" : null,
    },
  };
}
