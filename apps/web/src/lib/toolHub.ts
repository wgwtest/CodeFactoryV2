import { api } from "./api";
import type {
  EvolutionConfigUpdateInput,
  EvolutionFinding,
  EvolutionFindingDecisionInput,
  EvolutionInspectionConfig,
  EvolutionRun,
  EvolutionRunCreateInput,
  EvolutionRunEnvelope,
  EvolutionTask,
  EvolutionTaskEnvelope,
  EvolutionTaskRollbackInput,
  FrontendComponentBuildRequestInput,
  ItemProgressView,
  MockDemandScenarioId,
  P4ObjectWorkbenchProjection,
  ToolBuildRun,
  ToolDefinition,
  ToolDefinitionWriteInput,
  ToolDeliveryManifest,
  ToolDemandItem,
  ToolDemandReviewDecisionInput,
  ToolDemandSheetActionInput,
  ToolDemandSheet,
  ToolDemandSheetCreateRequestInput,
  ToolDemandSheetEnvelope,
  ToolDemandTestingClearResult,
  ToolFetchManifest,
  ToolHubOverview,
  ToolManufacturePlanEnvelope,
  ToolRegistryDeleteResult,
  ToolRegistryTestingClearResult,
  ToolHubReadEnvelope,
  ToolListEnvelope,
  ToolMatchRequestInput,
  ToolMatchRun,
} from "./api";

export type P4ObjectViewsProjectionInput = {
  overview: ToolHubOverview;
  tools: ToolDefinition[];
  demandSheets: ToolDemandSheet[];
  activeSheet?: ToolDemandSheet | null;
  selectedItemId?: string | null;
  selectedToolId?: string | null;
  manufacturePlans: ToolManufacturePlanEnvelope["items"];
  evolutionConfig: EvolutionInspectionConfig | null;
  evolutionRuns: EvolutionRun[];
  evolutionTasks: EvolutionTask[];
};

export type P4ObjectViewsProjection = Omit<P4ObjectWorkbenchProjection, "snapshot_id" | "meta">;

export function buildP4ObjectViewsProjection(input: P4ObjectViewsProjectionInput): P4ObjectViewsProjection {
  const activeSheet = input.activeSheet ?? input.demandSheets[0] ?? null;
  const activeItem =
    activeSheet?.items?.find((item) => item.item_id === input.selectedItemId) ?? activeSheet?.items?.[0] ?? null;
  const selectedTool =
    input.tools.find((tool) => tool.tool_id === input.selectedToolId) ??
    input.tools.find((tool) => tool.tool_id === activeItem?.recommended_tool_id) ??
    input.tools[0] ??
    null;
  const manufacturePlan = activeItem
    ? input.manufacturePlans.find((plan) => plan.item_id === activeItem.item_id) ?? null
    : null;
  const activeItems =
    activeSheet?.items?.filter((item) => item.supply_result?.result_type === "existing_tool" || item.supply_result?.result_type === "manufactured_tool") ??
    [];
  const hotTools = [...input.tools].sort((left, right) => right.updated_at.localeCompare(left.updated_at)).slice(0, 3);
  const coldTools = input.tools.filter((tool) => tool.status !== "active").slice(0, 3);
  const hotDomains = input.overview.catalogs.domains.slice(0, 3);
  const coldDomains = input.overview.catalogs.domains.slice(-3);
  const usedByItems = activeSheet?.items?.filter((item) => item.recommended_tool_id === selectedTool?.tool_id || item.supply_result?.tool_ref === selectedTool?.tool_id) ?? [];

  return {
    object_tabs: [
      { key: "pool", title: "工单池与工单", caption: "工单池 / 当前工单 / 工具项" },
      { key: "processing", title: "工单处理", caption: "生命周期、进展与关闭口径" },
      { key: "build", title: "工具构建", caption: "匹配、生产与过程值" },
      { key: "usage", title: "取用驾驶舱", caption: "取用、热点与冷点" },
      { key: "registry", title: "工具资源列表", caption: "资源、版本与验证" },
      { key: "graph", title: "覆盖知识图谱", caption: "业务覆盖与时序关系" },
      { key: "asset", title: "成品工具属性", caption: "工程使用与演进关系" },
      { key: "config", title: "演进配置", caption: "巡检范围与触发规则" },
      { key: "lineage", title: "演进轨迹", caption: "主干、分支与回退点" },
    ],
    workorder_pool: {
      sheets: input.demandSheets,
      active_sheet: activeSheet,
    },
    workorder_processing: {
      active_sheet: activeSheet,
      active_item: activeItem,
    },
    tool_build: {
      selected_tool: selectedTool,
      active_item: activeItem,
      manufacture_plan: manufacturePlan,
    },
    usage_cockpit: {
      active_items: activeItems,
      hot_tools: hotTools,
      cold_tools: coldTools,
      hot_domains: hotDomains,
      cold_domains: coldDomains,
    },
    tool_resources: {
      tools: input.tools,
    },
    coverage_knowledge_graph: {
      matrix: input.overview.coverage_matrix,
    },
    delivered_tool_attribute: {
      selected_tool: selectedTool,
      used_by_items: usedByItems,
      evolution_task_count: input.evolutionTasks.length,
      rollback_available_count: input.evolutionTasks.filter((task) => task.rollback_available).length,
    },
    evolution_config: {
      config: input.evolutionConfig,
    },
    evolution_lineage: {
      runs: input.evolutionRuns,
      tasks: input.evolutionTasks,
    },
  };
}

export function getToolHubOverview() {
  return api.get<ToolHubReadEnvelope<ToolHubOverview>>("/tool-hub/overview");
}

export function getP4ObjectWorkbenchProjection(params?: {
  sheet_id?: string | null;
  item_id?: string | null;
  tool_id?: string | null;
}) {
  return api.get<ToolHubReadEnvelope<P4ObjectWorkbenchProjection>>("/tool-hub/operator/workbench/object-view", {
    params: Object.fromEntries(
      Object.entries(params ?? {}).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    ),
  });
}

export function getToolDefinitions() {
  return api.get<ToolHubReadEnvelope<ToolListEnvelope>>("/tool-hub/tools");
}

export function createToolDefinition(payload: ToolDefinitionWriteInput) {
  return api.post<ToolDefinition>("/tool-hub/tools", payload);
}

export function updateToolDefinition(toolId: string, payload: ToolDefinitionWriteInput) {
  return api.put<ToolDefinition>(`/tool-hub/tools/${toolId}`, payload);
}

export function deleteToolDefinition(toolId: string) {
  return api.delete<ToolRegistryDeleteResult>(`/tool-hub/tools/${toolId}`);
}

export function createToolMatchRun(payload: ToolMatchRequestInput) {
  return api.post<ToolMatchRun>("/tool-hub/match-runs", payload);
}

export function getEvolutionRuns() {
  return api.get<ToolHubReadEnvelope<EvolutionRunEnvelope>>("/tool-hub/evolution-runs");
}

export function createEvolutionRun() {
  return api.post<EvolutionRun>("/tool-hub/evolution-runs");
}

export function getEvolutionConfig() {
  return api.get<ToolHubReadEnvelope<EvolutionInspectionConfig>>("/tool-hub/evolution/config");
}

export function updateEvolutionConfig(payload: EvolutionConfigUpdateInput) {
  return api.patch<EvolutionInspectionConfig>("/tool-hub/evolution/config", payload);
}

export function getEvolutionRunsV2() {
  return api.get<ToolHubReadEnvelope<EvolutionRunEnvelope>>("/tool-hub/evolution/runs");
}

export function createEvolutionRunV2(payload: EvolutionRunCreateInput) {
  return api.post<EvolutionRun>("/tool-hub/evolution/runs", payload);
}

export function decideEvolutionFinding(findingId: string, payload: EvolutionFindingDecisionInput) {
  return api.post<EvolutionFinding>(`/tool-hub/evolution/findings/${findingId}/decision`, payload);
}

export function getEvolutionTasks() {
  return api.get<ToolHubReadEnvelope<EvolutionTaskEnvelope>>("/tool-hub/evolution/tasks");
}

export function getEvolutionTask(taskId: string) {
  return api.get<EvolutionTask>(`/tool-hub/evolution/tasks/${taskId}`);
}

export function rollbackEvolutionTask(taskId: string, payload: EvolutionTaskRollbackInput) {
  return api.post<EvolutionTask>(`/tool-hub/evolution/tasks/${taskId}/rollback`, payload);
}

export function createMockDemandSheet(scenarioId: MockDemandScenarioId) {
  return api.post<ToolDemandSheet>(`/tool-hub/mock-generators/demand-sheets/${scenarioId}`);
}

export function createMockBlueForceDemandSheet() {
  return api.post<ToolDemandSheet>("/tool-hub/mock-generators/blue-force-demand-sheets");
}

export function createDemandSheet(payload: ToolDemandSheetCreateRequestInput) {
  return api.post<ToolDemandSheet>("/tool-hub/demand-sheets", payload);
}

export function getDemandSheets() {
  return api.get<ToolDemandSheetEnvelope>("/tool-hub/demand-sheets");
}

export function getManufacturePlans() {
  return api.get<ToolManufacturePlanEnvelope>("/tool-hub/manufacture-plans");
}

export function getDemandSheet(sheetId: string) {
  return api.get<ToolDemandSheet>(`/tool-hub/demand-sheets/${sheetId}`);
}

export function withdrawDemandSheet(sheetId: string, payload: ToolDemandSheetActionInput) {
  return api.post<ToolDemandSheet>(`/tool-hub/demand-sheets/${sheetId}/withdraw`, payload);
}

export function rejectDemandSheet(sheetId: string, payload: ToolDemandSheetActionInput) {
  return api.post<ToolDemandSheet>(`/tool-hub/demand-sheets/${sheetId}/reject`, payload);
}

export function clearDemandSheetsForTesting() {
  return api.post<ToolDemandTestingClearResult>("/tool-hub/testing/clear-demand-sheets");
}

export function clearToolsForTesting() {
  return api.post<ToolRegistryTestingClearResult>("/tool-hub/testing/clear-tools");
}

export function getDemandItem(itemId: string) {
  return api.get<ToolDemandItem>(`/tool-hub/demand-items/${itemId}`);
}

export function reviewDemandItem(itemId: string, payload: ToolDemandReviewDecisionInput) {
  return api.post<ToolDemandItem>(`/tool-hub/demand-items/${itemId}/review`, payload);
}

export function getDemandItemProgress(itemId: string) {
  return api.get<ItemProgressView>(`/tool-hub/demand-items/${itemId}/progress`);
}

export function getToolFetchManifest(toolId: string) {
  return api.get<ToolFetchManifest>(`/tool-hub/tools/${toolId}/fetch`);
}

export function createFrontendComponentBuildRequest(payload: FrontendComponentBuildRequestInput) {
  return api.post<ToolBuildRun>("/tool-hub/build-requests/frontend-components", payload);
}

export function getBuildRun(buildRunId: string) {
  return api.get<ToolBuildRun>(`/tool-hub/build-runs/${buildRunId}`);
}

export function getToolDeliveryManifest(toolId: string) {
  return api.get<ToolDeliveryManifest>(`/tool-hub/tools/${toolId}/delivery-manifest`);
}
