import { api } from "./api";
import type {
  EvolutionRun,
  EvolutionRunEnvelope,
  ItemProgressView,
  ToolDefinition,
  ToolDefinitionWriteInput,
  ToolDemandItem,
  ToolDemandSheet,
  ToolDemandSheetCreateRequestInput,
  ToolDemandSheetEnvelope,
  ToolFetchManifest,
  ToolHubOverview,
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

export function createToolMatchRun(payload: ToolMatchRequestInput) {
  return api.post<ToolMatchRun>("/tool-hub/match-runs", payload);
}

export function getEvolutionRuns() {
  return api.get<ToolHubReadEnvelope<EvolutionRunEnvelope>>("/tool-hub/evolution-runs");
}

export function createEvolutionRun() {
  return api.post<EvolutionRun>("/tool-hub/evolution-runs");
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

export function getDemandSheet(sheetId: string) {
  return api.get<ToolDemandSheet>(`/tool-hub/demand-sheets/${sheetId}`);
}

export function getDemandItem(itemId: string) {
  return api.get<ToolDemandItem>(`/tool-hub/demand-items/${itemId}`);
}

export function getDemandItemProgress(itemId: string) {
  return api.get<ItemProgressView>(`/tool-hub/demand-items/${itemId}/progress`);
}

export function getToolFetchManifest(toolId: string) {
  return api.get<ToolFetchManifest>(`/tool-hub/tools/${toolId}/fetch`);
}
