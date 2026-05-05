import { api } from "./api";
import type {
  RequirementAnalysisLabConfig,
  RequirementAnalysisOrchestratorEnvelope,
  RequirementAnalysisProviderEnvelope,
  RequirementAnalysisSession,
  RequirementAnalysisSessionCreateInput,
  RequirementAnalysisTurnEnvelope,
} from "./api";

export function getRequirementAnalysisLabConfig() {
  return api.get<RequirementAnalysisLabConfig>("/requirement-analysis/lab-config");
}

export function getRequirementAnalysisOrchestrators() {
  return api.get<RequirementAnalysisOrchestratorEnvelope>("/requirement-analysis/orchestrators");
}

export function getRequirementAnalysisProviders() {
  return api.get<RequirementAnalysisProviderEnvelope>("/requirement-analysis/providers");
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
