import { api } from "./api";
import type {
  BrainstormOrchestratorEnvelope,
  BrainstormProviderEnvelope,
  BrainstormSession,
  BrainstormSessionCreateInput,
  BrainstormTurnEnvelope,
} from "./api";

export function getBrainstormOrchestrators() {
  return api.get<BrainstormOrchestratorEnvelope>("/brainstorm/orchestrators");
}

export function getBrainstormProviders() {
  return api.get<BrainstormProviderEnvelope>("/brainstorm/providers");
}

export function createBrainstormSession(payload: BrainstormSessionCreateInput) {
  return api.post<BrainstormSession>("/brainstorm/sessions", payload);
}

export function getBrainstormSession(sessionId: string) {
  return api.get<BrainstormSession>(`/brainstorm/sessions/${sessionId}`);
}

export function createBrainstormTurn(sessionId: string, userInput: string) {
  return api.post<BrainstormTurnEnvelope>(`/brainstorm/sessions/${sessionId}/turns`, {
    user_input: userInput,
  });
}
