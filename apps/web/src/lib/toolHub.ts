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
  ItemProgressView,
  MockDemandScenarioId,
  ToolDefinition,
  ToolDefinitionWriteInput,
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

export function getToolHubOverview() {
  return api.get<ToolHubReadEnvelope<ToolHubOverview>>("/tool-hub/overview");
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
