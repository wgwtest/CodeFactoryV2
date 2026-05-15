import { api } from "./api";
import type {
  RequirementAnalysisLabConfig,
  RequirementAnalysisOrchestratorEnvelope,
  RequirementAnalysisProviderEnvelope,
  RequirementAnalysisSession,
  RequirementAnalysisSessionCreateInput,
  RequirementAnalysisTemplateDetail,
  RequirementAnalysisTemplateEnvelope,
  RequirementAnalysisTurnEnvelope,
  RequirementSpecWorkItem,
  RequirementSpecWorkItemConfigureInput,
  RequirementSpecWorkItemCreateInput,
  RequirementSpecWorkItemEnvelope,
  RequirementSpecWorkItemSaveAsInput,
  RequirementSpecWorkItemSaveSessionArtifactsInput,
} from "./api";

export function getRequirementAnalysisLabConfig() {
  return api.get<RequirementAnalysisLabConfig>("/requirement-analysis/lab-config");
}

export function getRequirementAnalysisOrchestrators() {
  return api.get<RequirementAnalysisOrchestratorEnvelope>("/requirement-analysis/orchestrators");
}

export function reloadRequirementAnalysisOrchestrators() {
  return api.post<RequirementAnalysisOrchestratorEnvelope>("/requirement-analysis/orchestrators/reload");
}

export function getRequirementAnalysisProviders() {
  return api.get<RequirementAnalysisProviderEnvelope>("/requirement-analysis/providers");
}

export function getRequirementAnalysisTemplates() {
  return api.get<RequirementAnalysisTemplateEnvelope>("/requirement-analysis/templates");
}

export function getRequirementAnalysisTemplateBases() {
  return api.get<RequirementAnalysisTemplateEnvelope>("/requirement-analysis/template-bases");
}

export function getRequirementSpecWorkItems() {
  return api.get<RequirementSpecWorkItemEnvelope>("/requirement-analysis/spec-items");
}

export function createRequirementSpecWorkItem(payload: RequirementSpecWorkItemCreateInput) {
  return api.post<RequirementSpecWorkItem>("/requirement-analysis/spec-items", payload);
}

export function configureRequirementSpecWorkItem(specItemId: string, payload: RequirementSpecWorkItemConfigureInput) {
  return api.post<RequirementSpecWorkItem>(`/requirement-analysis/spec-items/${specItemId}/configure`, payload);
}

export function publishRequirementSpecWorkItem(specItemId: string) {
  return api.post<RequirementSpecWorkItem>(`/requirement-analysis/spec-items/${specItemId}/publish`);
}

export function deleteRequirementSpecWorkItem(specItemId: string) {
  return api.delete<{ deleted: boolean; spec_item_id: string }>(`/requirement-analysis/spec-items/${specItemId}`);
}

export function saveRequirementSpecWorkItemSessionArtifacts(specItemId: string, payload?: RequirementSpecWorkItemSaveSessionArtifactsInput) {
  return api.post<RequirementSpecWorkItem>(`/requirement-analysis/spec-items/${specItemId}/save-session-artifacts`, payload ?? {});
}

export function saveRequirementSpecWorkItemSessionArtifactsAs(specItemId: string, payload: RequirementSpecWorkItemSaveAsInput) {
  return api.post<RequirementSpecWorkItem>(`/requirement-analysis/spec-items/${specItemId}/save-session-artifacts-as`, payload);
}

export function getRequirementAnalysisTemplate(templateId: string) {
  return api.get<RequirementAnalysisTemplateDetail>(`/requirement-analysis/templates/${templateId}`);
}

export function createRequirementAnalysisTemplate(baseTemplateId: string, name: string, description: string) {
  return api.post<RequirementAnalysisTemplateDetail>("/requirement-analysis/templates", {
    base_template_id: baseTemplateId,
    name,
    description,
  });
}

export function saveRequirementAnalysisTemplate(templateId: string, content: string, name?: string, description?: string) {
  return api.put<RequirementAnalysisTemplateDetail>(`/requirement-analysis/templates/${templateId}`, {
    content,
    name,
    description,
  });
}

export function deleteRequirementAnalysisTemplate(templateId: string) {
  return api.delete<{ deleted: boolean; template_id: string }>(`/requirement-analysis/templates/${templateId}`);
}

export function saveRequirementAnalysisTemplateAsBase(templateId: string) {
  return api.post<RequirementAnalysisTemplateDetail>(`/requirement-analysis/templates/${templateId}/save-as-base`);
}

export function createRequirementAnalysisSession(payload: RequirementAnalysisSessionCreateInput) {
  return api.post<RequirementAnalysisSession>("/requirement-analysis/sessions", payload);
}

export function getRequirementAnalysisSession(sessionId: string) {
  return api.get<RequirementAnalysisSession>(`/requirement-analysis/sessions/${sessionId}`);
}

export function createRequirementAnalysisTurn(sessionId: string, userInput: string) {
  return api.post<RequirementAnalysisTurnEnvelope>(`/requirement-analysis/sessions/${sessionId}/turns`, {
    user_input: userInput,
  });
}
