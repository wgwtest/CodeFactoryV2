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
        P4: "工具仓库",
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
      P4: { route_id: "stage-p4", label: "工具仓库", path: "/xx-p4", description: "P4 稳定模块入口", entry_available: true },
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
      { tone: "knowledge", label: "主链通畅", detail: "五阶段主链保持可观察流动" },
      { tone: "tooling", label: "评审压力 72%", detail: "P3 评审压力作为底部状态信号展示" },
      { tone: "analysis", label: "模拟源驱动", detail: "当前页面由 P6 mock projection 驱动" },
      { tone: "delivery", label: "最近刷新 18 秒前", detail: "门户投影新鲜度提示" },
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
  const capturedAt = isDeliveryGap ? "2026-04-21T10:27:00+08:00" : "2026-04-21T10:05:00+08:00";
  const makeMetric = (key: string, label: string, value: number, unit: string, basis: string) => ({
    key,
    label,
    value,
    unit,
    basis,
  });
  const makeLive = (
    key: string,
    label: string,
    value: number,
    unit: string,
    window: string,
    direction: "input" | "output" | "process",
  ) => ({
    key,
    label,
    value,
    unit,
    window,
    direction,
  });
  const makeUser = (user_ref: string, display_label: string, role_label: string) => ({
    user_ref,
    display_label,
    role_label,
    activity_state: "active",
    connected_at: capturedAt,
  });
  const makeQueue = (stageId: string, label: string, items: string[]) => ({
    queue_id: `${stageId.toLowerCase()}-display-queue`,
    label,
    items: items.map((itemLabel, order_index) => ({
      item_id: `${stageId.toLowerCase()}-queue-${order_index + 1}`,
      label: itemLabel,
      state: order_index === 0 ? "active" : "waiting",
      order_index,
    })),
    active_index: 0,
    advance_rule: "active_done_then_shift_left",
  });
  const makePorts = (
    stageId: string,
    inputTarget: string,
    inputLabel: string,
    inputRate: string,
    outputTarget: string,
    outputLabel: string,
    outputRate: string,
    terminal = false,
  ) => [
    {
      port_id: `${stageId.toLowerCase()}_input`,
      side: "left",
      direction: "input",
      label: inputLabel,
      connected_target: inputTarget,
      current_rate: inputRate,
      terminal: false,
    },
    {
      port_id: `${stageId.toLowerCase()}_output`,
      side: "right",
      direction: "output",
      label: outputLabel,
      connected_target: outputTarget,
      current_rate: outputRate,
      terminal,
    },
  ];
  type TestFlowPort = ReturnType<typeof makePorts>[number];
  const makeStageCard = (
    stageId: string,
    headline: string,
    summaryLine: string,
    overall: ReturnType<typeof makeMetric>[],
    live: ReturnType<typeof makeLive>[],
    ports: TestFlowPort[],
    users: ReturnType<typeof makeUser>[],
    queue: ReturnType<typeof makeQueue>,
    health: { label: string; tone: "ready" | "warning" | "blocked"; detail: string },
    degraded_hint: string | null = null,
  ) => ({
    contract_version: "P6DisplayExportContract.v2",
    stage_id: stageId,
    headline_value: headline,
    summary_line: summaryLine,
    metric_items: overall.slice(0, 2).map((metric) => ({
      metric_key: metric.key,
      metric_label: metric.label,
      metric_value: `${metric.value}${metric.unit}`,
    })),
    system_overall_metric_items: overall,
    live_counter_items: live,
    flow_port_items: ports,
    connected_user_items: users,
    queue_projection: queue,
    display_binding: {
      prototype_refs: [
        "DOC/CODEX_DOC/08_原型与附图/2026-04-29-192233-CodeFactoryV2-P6四子系统总体状态卡详情原型-v14/",
      ],
      regions: {
        top_participants: "connected_users",
        middle_overall: "system_overall_metrics",
        lower_realtime: "live_counters",
        left_input_port: "flow_ports[input]",
        right_output_port: "flow_ports[output]",
        bottom_queue: "queue_projection",
      },
    },
    source_trace: overall.map((metric) => ({
      field: `system_overall_metrics.${metric.key}`,
      source_doc: `DOC/CODEX_DOC/02_设计说明/${stageId}_${stageId}/`,
      source_object: metric.label,
      calculation_basis: metric.basis,
      freshness_policy: "mock-fresh",
      display_reason: "绑定详情卡中段总体状态",
    })),
    entry_badge: { label: `${stageId} 入口可用`, tone: "ready" },
    health_badge: health,
    timestamp_label: isDeliveryGap ? "缺口于 04-21 10:27" : isReviewPressure ? "压力于 04-21 10:16" : "刷新于 04-21 10:05",
    degraded_hint,
  });

  const nodes = [
    {
      node_id: "p1",
      node_kind: "module",
      title: "业务知识库",
      stage_id: "P1",
      route: "/graph",
      projection_mode: "auto",
      summary: "知识供给稳定对外发布。",
      primary_status: "knowledge_asset_running",
      freshness: "fresh",
      description: "负责沉淀领域知识并向后续阶段提供稳定知识供给。",
      stage_card: makeStageCard(
        "P1",
        "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人",
        "正在入库 8 条/小时，供给 P2 5 条/小时。",
        [
          makeMetric("knowledge_repository_count", "知识库", 12, "个", "累计资产"),
          makeMetric("published_knowledge_count", "已发布知识", 12480, "条", "累计产出"),
          makeMetric("domain_directory_count", "领域", 36, "个", "累计目录"),
          makeMetric("contributor_count", "贡献者", 58, "人", "累计贡献"),
        ],
        [
          makeLive("active_knowledge_intake_rate", "正在入库", 8, "条/小时", "1h", "input"),
          makeLive("active_p2_supply_rate", "供给 P2", 5, "条/小时", "1h", "output"),
        ],
        [
          {
            port_id: "p1_p2_output",
            side: "right",
            direction: "output",
            label: "发布态知识",
            connected_target: "P2",
            current_rate: "5 条/小时",
            terminal: false,
          },
        ],
        [
          makeUser("role:knowledge-librarian", "库", "知识库管理员"),
          makeUser("role:domain-specialist", "专", "领域专家"),
          makeUser("role:knowledge-reviewer", "审", "知识审核"),
          makeUser("role:collector", "采", "知识采集"),
        ],
        makeQueue("P1", "知识挂载队列", ["税务规则", "空域约束", "表单库", "资产库", "术语表"]),
        { label: "健康", tone: "ready", detail: "最新知识发布已完成。" },
      ),
    },
    {
      node_id: "p2",
      node_kind: "module",
      title: "需求分析系统",
      stage_id: "P2",
      route: "/requirements",
      projection_mode: "auto",
      summary: "需求建模累计资产稳定增长。",
      primary_status: "requirement_modeling_running",
      freshness: "fresh",
      description: "把业务语言建模为结构化需求规格与需求对象。",
      stage_card: makeStageCard(
        "P2",
        "支持软件 24 个，需求规格 86 份，业务对象 430 个",
        "知识接入 5 条/小时，规格输出 4 份/小时。",
        [
          makeMetric("supported_software_count", "支持软件", 24, "个", "累计承载"),
          makeMetric("requirement_spec_count", "需求规格", 86, "份", "累计产出"),
          makeMetric("business_object_count", "业务对象", 430, "个", "累计建模"),
        ],
        [
          makeLive("active_knowledge_receive_rate", "知识接入", 5, "条/小时", "1h", "input"),
          makeLive("active_spec_output_rate", "规格输出", 4, "份/小时", "1h", "output"),
        ],
        makePorts("P2", "P1", "发布态知识", "5 条/小时", "P3", "需求规格", "4 份/小时"),
        [
          makeUser("role:industry-user", "业", "行业用户"),
          makeUser("role:product-owner", "产", "产品负责人"),
          makeUser("role:analyst", "分", "需求分析"),
          makeUser("role:domain-owner", "域", "领域负责人"),
          makeUser("role:requirement-reviewer", "审", "需求评审"),
          makeUser("role:project-manager", "项", "项目管理"),
        ],
        makeQueue("P2", "需求建模队列", ["访谈记录", "领域对象", "模型草案"]),
        { label: "健康", tone: "ready", detail: "需求建模链路稳定。" },
      ),
    },
    {
      node_id: "p3",
      node_kind: "module",
      title: "软件设计系统",
      stage_id: "P3",
      route: "/modeling",
      projection_mode: "auto",
      summary: isReviewPressure ? "总体设计承载正常，但评审压力升高。" : "设计资产累计产出正常。",
      primary_status: isReviewPressure ? "review_pressure" : "software_design_running",
      freshness: "fresh",
      description: "承接需求规格并输出软件设计说明与设计结构表达。",
      stage_card: makeStageCard(
        "P3",
        "支持软件 36 个，设计基线 112 份，工单包 268 包",
        isReviewPressure ? "规格接入 4 份/小时，评审压力上升。" : "规格接入 4 份/小时，工单输出 5 包/小时，设计基线同步 3 份/小时。",
        [
          makeMetric("supported_software_count", "支持软件", 36, "个", "累计承载"),
          makeMetric("design_baseline_count", "设计基线", 112, "份", "累计设计资产"),
          makeMetric("work_order_package_count", "工单包", 268, "包", "累计产出"),
        ],
        [
          makeLive("active_requirement_input_rate", "规格接入", 4, "份/小时", "1h", "input"),
          makeLive("active_workorder_output_rate", "工单输出", 5, "包/小时", "1h", "output"),
          makeLive("active_design_baseline_sync_rate", "基线同步", 3, "份/小时", "1h", "output"),
        ],
        [
          ...makePorts("P3", "P2", "需求规格", "4 份/小时", "P4", "模块工单包", "5 包/小时"),
          {
            port_id: "p3_p5_baseline_output",
            side: "right",
            direction: "output",
            label: "设计基线",
            connected_target: "P5",
            current_rate: "3 份/小时",
            terminal: false,
          },
        ],
        [
          makeUser("role:architect", "架", "架构设计"),
          makeUser("role:designer", "设", "软件设计"),
          makeUser("role:reviewer", "审", "设计评审"),
          makeUser("role:modeler", "模", "模型维护"),
          makeUser("role:project-owner", "项", "项目负责人"),
        ],
        makeQueue("P3", "设计生成队列", ["规范输入", "分析草图", "草案", "评审", "冻结"]),
        isReviewPressure
          ? { label: "注意", tone: "warning", detail: "设计评审压力升高。" }
          : { label: "健康", tone: "ready", detail: "设计输出节奏正常。" },
      ),
    },
    {
      node_id: "p4",
      node_kind: "module",
      title: "工具仓库",
      stage_id: "P4",
      route: "/xx-p4",
      projection_mode: "auto",
      summary: isDeliveryGap ? "总体工具资产可用，供给命中存在缺口。" : "工具资产和供给结果稳定增长。",
      primary_status: isDeliveryGap ? "tool_supply_warning" : "tool_supply_running",
      freshness: "fresh",
      description: "沉淀工具供给与能力匹配规则。",
      stage_card: makeStageCard(
        "P4",
        "工具定义 286 个，领域目录 42 个，供给结果 620 项",
        isDeliveryGap ? "正在匹配 7 项/小时，部分能力需回补。" : "正在匹配 7 项/小时，工具供给 4 项/小时。",
        [
          makeMetric("tool_definition_count", "工具定义", 286, "个", "累计工具资产"),
          makeMetric("domain_catalog_count", "领域目录", 42, "个", "累计目录"),
          makeMetric("tool_supply_result_count", "供给结果", 620, "项", "累计产出"),
        ],
        [
          makeLive("active_matching_rate", "正在匹配", 7, "项/小时", "1h", "process"),
          makeLive("active_supply_output_rate", "工具供给", 4, "项/小时", "1h", "output"),
        ],
        makePorts("P4", "P3", "模块工单包", "5 包/小时", "P5", "工具供给", "4 项/小时"),
        [
          makeUser("role:tool-engineer", "工", "工具工程"),
          makeUser("role:researcher", "研", "工具研究"),
          makeUser("role:tool-reviewer", "审", "工具评审"),
          makeUser("role:maintainer", "维", "工具维护"),
        ],
        makeQueue("P4", "工具供给队列", ["查询", "生成", "验证"]),
        isDeliveryGap
          ? { label: "注意", tone: "warning", detail: "供给链存在待补位需求。" }
          : { label: "健康", tone: "ready", detail: "工具匹配链路稳定。" },
      ),
    },
    {
      node_id: "p5",
      node_kind: "module",
      title: "软件构建系统",
      stage_id: "P5",
      route: "/build",
      projection_mode: "auto",
      summary: isDeliveryGap ? "总体构建资产存在交付缺口。" : "构建与交付目录累计产出正常。",
      primary_status: isDeliveryGap ? "delivery_gap_blocked" : "software_build_running",
      freshness: "fresh",
      description: "整合设计、工具与交付链路，产出构建结果与缺口反馈。",
      stage_card: makeStageCard(
        "P5",
        "支持软件 24 个，交付版本 86 个，构建尝试 412 次",
        isDeliveryGap ? "目录输出受阻，需人工确认缺口与回补路径。" : "正在装配 4 项，目录输出 2 个/日。",
        [
          makeMetric("supported_software_count", "支持软件", 24, "个", "累计承载"),
          makeMetric("delivery_version_count", "交付版本", 86, "个", "累计产出"),
          makeMetric("build_attempt_count", "构建尝试", 412, "次", "累计运行事实"),
        ],
        [
          makeLive("active_assembly_count", "正在装配", 4, "项", "now", "process"),
          makeLive("delivery_catalog_output_rate", "目录输出", 2, "个/日", "1d", "output"),
        ],
        [
          ...makePorts("P5", "P4", "工具供给", "4 项/小时", "交付目录", "交付目录", "2 个/日", true),
          {
            port_id: "p3_baseline_input",
            side: "left",
            direction: "input",
            label: "设计基线",
            connected_target: "P3",
            current_rate: "3 份/小时",
            terminal: false,
          },
        ],
        [
          makeUser("role:builder", "构", "构建人员"),
          makeUser("role:tester", "测", "测试人员"),
          makeUser("role:release", "发", "发布人员"),
          makeUser("role:version-manager", "版", "版本管理"),
        ],
        makeQueue("P5", "构建交付队列", ["装配", "测试", "打包", "发布"]),
        isDeliveryGap
          ? { label: "阻塞", tone: "blocked", detail: "关键交付缺口未闭合。" }
          : { label: "健康", tone: "ready", detail: "构建主链可执行。" },
        isDeliveryGap ? "需人工确认缺口与回补路径。" : null,
      ),
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
          flow_id: "p1-p2",
          from_node_id: "p1",
          to_node_id: "p2",
          semantic_type: "knowledge_supply",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
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
          label: "需求规格",
        },
        {
          flow_id: "p3-p4",
          from_node_id: "p3",
          to_node_id: "p4",
          semantic_type: "work_order_package",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "design",
          render_style: "dashed",
          label: "模块工单包",
        },
        {
          flow_id: "p3-p5",
          from_node_id: "p3",
          to_node_id: "p5",
          semantic_type: "design_baseline_to_build",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "design",
          render_style: "dashed",
          label: "设计基线",
        },
        {
          flow_id: "p4-p5",
          from_node_id: "p4",
          to_node_id: "p5",
          semantic_type: "tool_supply",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "tooling",
          render_style: "solid",
          label: "工具供给",
        },
        {
          flow_id: "p5-delivery",
          from_node_id: "p5",
          to_node_id: "delivery-catalog",
          semantic_type: "delivery_catalog_output",
          direction: "forward",
          from_pin: "right",
          to_pin: "left",
          render_tone: "delivery",
          render_style: "solid",
          label: "交付目录",
        },
      ],
      artifact_list: [],
      portal_summary: {
        headline: "P6 首屏观察门户",
        source_label: "模拟源",
        scenario_label: scenarioLabel,
        module_count: 5,
        user_count: 23,
        artifact_count: 0,
        flow_count: 6,
        focus_hint: isDeliveryGap ? "建议优先关注 P5" : isReviewPressure ? "建议优先关注 P3" : "建议优先关注 P2",
        alert_message: isDeliveryGap
          ? "交付链出现缺口，建议优先处理 P5 并回看 P4 供给命中。"
          : isReviewPressure
            ? "评审与供给跟进出现压力，建议优先关注 P3 到 P4。"
            : "当前模拟源显示主链通畅，可直接观察整体投影。",
      },
      knowledge_context: {
        current_knowledge_base_name: "知识库 12 个，已发布知识 12480 条，领域 36 个，贡献者 58 人",
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

export function buildPortalDataViewEnvelope(options?: { history?: boolean; selectedStageId?: string }) {
  const portalEnvelope = buildPortalProjectionEnvelope("baseline");
  const selectedStageId = options?.selectedStageId ?? "P3";
  const stageNodes = portalEnvelope.projection.node_list.filter((item) => item.node_kind === "module" && item.stage_card);
  const makeFlowPoint = (
    flow_id: string,
    from_stage_id: string,
    to_stage_id: string,
    semantic_type: string,
    payload_label: string,
    value: number,
    unit: string,
  ) => ({
    flow_id,
    from_stage_id,
    to_stage_id,
    semantic_type,
    payload_label,
    value,
    unit,
    rate_label: `${value} ${unit}`,
    captured_at: "2026-04-30T15:20:00+08:00",
  });
  const points = options?.history
    ? {
        "p1-p2": [makeFlowPoint("p1-p2", "P1", "P2", "knowledge_supply", "发布态知识", 5, "条/小时")],
        "p2-p3": [makeFlowPoint("p2-p3", "P2", "P3", "requirement_to_design", "需求规格", 4, "份/小时")],
        "p3-p4": [makeFlowPoint("p3-p4", "P3", "P4", "work_order_package", "模块工单包", 5, "包/小时")],
        "p3-p5": [makeFlowPoint("p3-p5", "P3", "P5", "design_baseline_to_build", "设计基线", 3, "份/小时")],
        "p4-p5": [makeFlowPoint("p4-p5", "P4", "P5", "tool_supply", "工具供给", 4, "项/小时")],
        "p5-delivery": [
          makeFlowPoint("p5-delivery", "P5", "交付目录", "delivery_catalog_output", "交付目录", 2, "个/日"),
        ],
      }
    : {};

  const flowSeries = [
    ["p1-p2", "P1 -> P2", "P1", "P2", "knowledge_supply", "发布态知识", "knowledge"],
    ["p2-p3", "P2 -> P3", "P2", "P3", "requirement_to_design", "需求规格", "analysis"],
    ["p3-p4", "P3 -> P4", "P3", "P4", "work_order_package", "模块工单包", "design"],
    ["p3-p5", "P3 -> P5", "P3", "P5", "design_baseline_to_build", "设计基线", "design"],
    ["p4-p5", "P4 -> P5", "P4", "P5", "tool_supply", "工具供给", "tooling"],
    ["p5-delivery", "P5 -> 交付目录", "P5", "交付目录", "delivery_catalog_output", "交付目录", "delivery"],
  ].map(([flow_id, label, from_stage_id, to_stage_id, semantic_type, payload_label, render_tone]) => ({
    flow_id,
    label,
    from_stage_id,
    to_stage_id,
    semantic_type,
    payload_label,
    render_tone,
    points: points[flow_id as keyof typeof points] ?? [],
  }));

  const selectedNode = stageNodes.find((item) => item.stage_id === selectedStageId) ?? stageNodes[2];
  const selectedCard = selectedNode.stage_card;

  return {
    source_mode: "mock",
    scenario: portalEnvelope.scenario,
    view: {
      scenario_summary: {
        scenario_id: "baseline",
        label: "基线通畅",
        source_label: "模拟源",
        stage_count: 5,
        flow_count: 6,
        connected_user_count: 23,
        queue_item_count: 20,
        history_sample_count: options?.history ? 1 : 0,
        captured_at: "2026-04-30T15:20:00+08:00",
      },
      stage_rows: stageNodes.map((item) => ({
        stage_id: item.stage_id,
        stage_name: item.title,
        primary_status: item.primary_status,
        health_level: item.stage_card?.health_badge.tone === "blocked" ? "blocked" : "healthy",
        overall_status: item.stage_card?.headline_value,
        realtime_input:
          item.stage_card?.live_counter_items
            ?.filter((counter) => counter.direction === "input")
            .map((counter) => `${counter.label} ${counter.value}${counter.unit}`)
            .join("；") || item.stage_card?.summary_line,
        processing_status:
          item.stage_card?.live_counter_items
            ?.filter((counter) => counter.direction === "process")
            .map((counter) => `${counter.label} ${counter.value}${counter.unit}`)
            .join("；") || item.stage_card?.health_badge.detail,
        output_flow:
          item.stage_card?.flow_port_items
            ?.filter((port) => port.direction === "output")
            .map((port) => `${port.label} -> ${port.connected_target} ${port.current_rate}`)
            .join("；") ?? "",
        connected_user_count: item.stage_card?.connected_user_items?.length ?? 0,
        queue_item_count: item.stage_card?.queue_projection?.items.length ?? 0,
        updated_at: "2026-04-30T15:20:00+08:00",
      })),
      flow_series: flowSeries,
      selected_stage_detail: {
        stage_id: selectedNode.stage_id,
        stage_name: selectedNode.title,
        summary: selectedNode.summary,
        overall_metrics: selectedCard?.system_overall_metric_items ?? [],
        live_counters: selectedCard?.live_counter_items ?? [],
        flow_ports: selectedCard?.flow_port_items ?? [],
        connected_users: selectedCard?.connected_user_items ?? [],
        queue_projection: selectedCard?.queue_projection,
        source_trace: selectedCard?.source_trace ?? [],
        display_contract: {
          contract_version: "P6DisplayExportContract.v2",
          stage_overview: {
            stage_id: selectedNode.stage_id ?? "P3",
            stage_name: selectedNode.title,
            stage_display_name: selectedNode.title,
            primary_status: selectedNode.primary_status ?? "unknown",
            summary: selectedCard?.headline_value ?? "",
            updated_at: "2026-04-30T15:20:00+08:00",
            freshness: "fresh",
          },
          entry_projection: {
            entry_route: selectedNode.route ?? "/portal",
            entry_available: true,
            entry_reason: `${selectedNode.title} 入口可用`,
          },
          system_overall_metrics: selectedCard?.system_overall_metric_items ?? [],
          live_counters: selectedCard?.live_counter_items ?? [],
          flow_ports: selectedCard?.flow_port_items ?? [],
          connected_users: selectedCard?.connected_user_items ?? [],
          queue_projection: selectedCard?.queue_projection,
          display_binding: selectedCard?.display_binding,
          health_projection: {
            health_level: "healthy",
            health_message: selectedCard?.health_badge.detail ?? "",
            health_source: "test",
            captured_at: "2026-04-30T15:20:00+08:00",
          },
          source_trace: selectedCard?.source_trace ?? [],
          stage_specific: {},
        },
        recent_flow_points: options?.history ? flowSeries.flatMap((series) => series.points).slice(0, 3) : [],
      },
      history_sample_count: options?.history ? 1 : 0,
    },
  };
}
