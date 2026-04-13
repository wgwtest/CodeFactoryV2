import { api } from "./api";
import type {
  ApplicationRequirementDraftCreateInput,
  ApplicationRequirementDraftEnvelope,
  ApplicationRequirementDraftExport,
  ApplicationRequirementDraftUpdateInput,
} from "./api";

export function createRequirementDraft(payload: ApplicationRequirementDraftCreateInput) {
  return api.post<ApplicationRequirementDraftEnvelope>("/modeling/requirement-drafts", payload);
}

export function getRequirementDraft(draftId: string) {
  return api.get<ApplicationRequirementDraftEnvelope>(`/modeling/requirement-drafts/${draftId}`);
}

export function updateRequirementDraft(draftId: string, payload: ApplicationRequirementDraftUpdateInput) {
  return api.put<ApplicationRequirementDraftEnvelope>(`/modeling/requirement-drafts/${draftId}`, payload);
}

export function completeRequirementDraft(draftId: string) {
  return api.post<ApplicationRequirementDraftEnvelope>(`/modeling/requirement-drafts/${draftId}/complete`);
}

export function exportRequirementDraft(draftId: string) {
  return api.get<ApplicationRequirementDraftExport>(`/modeling/requirement-drafts/${draftId}/export`);
}
