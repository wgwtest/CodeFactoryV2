import { describe, expect, test } from "vitest";

import type {
  EvolutionInspectionConfig,
  ToolDefinition,
  ToolDemandItem,
  ToolDemandSheet,
  ToolHubOverview,
} from "../lib/api";
import { buildP4ObjectViewsProjection } from "../lib/toolHub";

function buildTool(tool_id: string, name: string, updated_at: string): ToolDefinition {
  return {
    tool_id,
    name,
    slug: tool_id,
    status: "active",
    summary: `${name} 摘要`,
    problem_statement: `${name} 问题定义`,
    primary_domain_id: "workflow_approval",
    tool_form_id: "frontend_component",
    runtime_platform_ids: ["agent_runtime"],
    tags: ["domain:workflow_approval", "form:frontend_component"],
    lifecycle_stage_ids: ["solution_design"],
    input_types: ["manual_text"],
    output_types: ["structured_json"],
    supported_sources: ["manual_input"],
    usage_notes: "",
    keywords: [name],
    verification: {
      status: "verified",
      last_verified_result: "ok",
      sample_case_ids: [],
    },
    created_at: updated_at,
    updated_at,
  };
}

function buildDemandItem(): ToolDemandItem {
  return {
    item_id: "item-1",
    sheet_id: "sheet-1",
    source_node_id: "node-1",
    ancestry: ["系统", "工单", "工具"],
    business_domain_id: "workflow_approval",
    component_name: "审批规则校验器",
    component_code: "COMP-1",
    problem_statement: "生成审批规则校验器",
    required_input_types: ["manual_text"],
    expected_output_types: ["structured_json"],
    preferred_tool_forms: ["frontend_component"],
    preferred_runtime_platforms: ["agent_runtime"],
    lifecycle_stage_ids: ["solution_design"],
    keywords: ["审批"],
    acceptance_notes: "可直接交付",
    recommendation_type: "existing_tool",
    recommendation_summary: "建议直接交付现有工具：审批规则校验器",
    recommended_tool_id: "tool-1",
    recommended_tool_name: "审批规则校验器",
    review_status: "approved_delivery",
    importance_score: 5,
    urgency_score: 4,
    rationality_verdict: "合理",
    review_comment: "直接交付",
    reviewed_by: "tester",
    reviewed_at: "2026-05-13T10:00:00Z",
    processing_status: "ready_for_fetch",
    analysis_result: "分析结果",
    check_result: "校验结果",
    match_result: "匹配结果",
    supply_result: {
      result_type: "existing_tool",
      item_id: "item-1",
      tool_ref: "tool-1",
      fetch_interface: {
        tool_id: "tool-1",
        tool_name: "审批规则校验器",
        tool_version: "v1",
        tool_form_id: "frontend_component",
        packaging_type: "descriptor_only",
        integration_mode: "manual",
        dependency_policy: "external",
        runtime_dependencies: [],
        runtime_platform_ids: ["agent_runtime"],
        fetch_mode: "descriptor",
        entrypoint_type: "http",
        entrypoint_locator: "/api/tool-hub/tools/tool-1/fetch",
        contract_version: "p4.fetch.v1",
        updated_at: "2026-05-13T10:00:00Z",
      },
      progress_query_interface: null,
      estimated_ready_at: null,
      suggested_poll_after_seconds: null,
      available_at: "2026-05-13T10:00:00Z",
      last_message: "已交付",
    },
    submitted_at: "2026-05-13T09:00:00Z",
    updated_at: "2026-05-13T10:00:00Z",
  };
}

function buildDemandSheet(): ToolDemandSheet {
  return {
    sheet_id: "sheet-1",
    sheet_name: "审批工单",
    lifecycle_status: "accepted",
    review_status: "reviewed",
    delivery_status: "delivered",
    processing_status: "ready",
    source: {
      phase: "p3_simulator",
      producer: "tester",
      business_case: "workflow_approval",
      scenario_id: "scenario-1",
      scenario_name: "审批场景",
    },
    requested_by: "P3",
    business_case: "workflow_approval",
    root_node: {
      node_id: "root",
      node_type: "system",
      node_name: "系统",
      node_code: "ROOT",
      business_domain_id: "workflow_approval",
      children: [],
    },
    item_ids: ["item-1"],
    item_count: 1,
    pending_review_count: 0,
    approved_delivery_count: 1,
    approved_manufacture_count: 0,
    rejected_item_count: 0,
    matched_existing_count: 1,
    manufacturing_count: 0,
    ready_for_fetch_count: 1,
    failed_count: 0,
    lifecycle_events: [],
    items: [buildDemandItem()],
    submitted_at: "2026-05-13T09:00:00Z",
    updated_at: "2026-05-13T10:00:00Z",
  };
}

test("buildP4ObjectViewsProjection derives object tabs and selected tool context", () => {
  const tools = [buildTool("tool-1", "审批规则校验器", "2026-05-13T10:00:00Z")];
  const demandSheets = [buildDemandSheet()];
  const overview = {
    metrics: {
      tool_count: 1,
      verified_tool_count: 1,
      active_tool_count: 1,
      draft_tool_count: 0,
      archived_tool_count: 0,
      match_run_count: 0,
      evolution_run_count: 0,
      active_chain_count: 1,
      overlap_candidate_count: 0,
      pending_suggestion_count: 0,
      recent_success_rate: 100,
    },
    run_monitor: {
      active_match_run_count: 0,
      active_evolution_run_count: 0,
      latest_match_run: null,
      latest_evolution_run: null,
      failing_run_count: 0,
      stale_run_count: 0,
    },
    coverage_matrix: {
      title: "业务域 × 工具形态",
      x_axis_label: "工具形态",
      y_axis_label: "业务能力域",
      columns: [{ id: "frontend_component", label: "前端元组件", description: "" }],
      rows: [{ row_id: "workflow_approval", row_label: "审批流转", cells: [{ column_id: "frontend_component", value: 1 }] }],
    },
    risk_summary: [],
    pending_suggestions: [],
    recent_match_runs: [],
    recent_evolution_runs: [],
    catalogs: {
      domains: [{ id: "workflow_approval", label: "审批流转", description: "" }],
      lifecycle_stages: [{ id: "solution_design", label: "方案设计", description: "" }],
      tool_forms: [{ id: "frontend_component", label: "前端元组件", description: "" }],
      runtime_platforms: [{ id: "agent_runtime", label: "Agent 运行时", description: "" }],
      input_types: [{ id: "manual_text", label: "手工文本", description: "" }],
      output_types: [{ id: "structured_json", label: "结构化 JSON", description: "" }],
      supported_sources: [{ id: "manual_input", label: "人工输入", description: "" }],
      verification_statuses: [{ id: "verified", label: "已验证", description: "" }],
      tag_namespaces: [{ id: "domain", label: "业务域", description: "" }],
    },
  } satisfies ToolHubOverview;

  const evolutionConfig = {
    config_id: "default",
    enabled: true,
    schedule_mode: "manual_and_scheduled",
    interval_minutes: 60,
    include_draft_tools: true,
    focus_rule_ids: ["missing_description", "taxonomy_issue", "overlap_risk", "coverage_gap"],
    overlap_threshold: 3,
    max_run_history: 50,
    auto_apply_rule_ids: ["missing_description", "taxonomy_issue"],
    updated_by: "tester",
    updated_at: "2026-05-13T10:00:00Z",
  } satisfies EvolutionInspectionConfig;

  const projection = buildP4ObjectViewsProjection({
    overview,
    tools,
    demandSheets,
    manufacturePlans: [],
    evolutionConfig,
    evolutionRuns: [],
    evolutionTasks: [],
  });

  expect(projection.object_tabs.map((item) => item.key)).toEqual([
    "pool",
    "processing",
    "build",
    "usage",
    "registry",
    "graph",
    "asset",
    "config",
    "lineage",
  ]);
  expect(projection.tool_build.selected_tool?.name).toBe("审批规则校验器");
  expect(projection.workorder_pool.active_sheet?.sheet_name).toBe("审批工单");
  expect(projection.coverage_knowledge_graph.matrix.title).toBe("业务域 × 工具形态");
});
