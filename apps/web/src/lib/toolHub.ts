import { api } from "./api";
import type {
  EvolutionRun,
  EvolutionRunEnvelope,
  ToolDefinition,
  ToolDefinitionWriteInput,
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
