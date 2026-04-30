import { api } from "./api";
import type {
  RequirementAuthoringDocumentCreateInput,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringDocumentSummary,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateWriteInput,
} from "./api";

export function getRequirementAuthoringTemplates() {
  return api.get<RequirementAuthoringTemplate[]>("/requirement-authoring/templates");
}

export function createRequirementAuthoringTemplate(payload: RequirementAuthoringTemplateWriteInput) {
  return api.post<RequirementAuthoringTemplate>("/requirement-authoring/templates", payload);
}

export function updateRequirementAuthoringTemplate(templateId: string, payload: RequirementAuthoringTemplateWriteInput) {
  return api.put<RequirementAuthoringTemplate>(`/requirement-authoring/templates/${templateId}`, payload);
}

export function activateRequirementAuthoringTemplate(templateId: string) {
  return api.post<RequirementAuthoringTemplate>(`/requirement-authoring/templates/${templateId}/activate`);
}

export function getRequirementAuthoringDocuments() {
  return api.get<RequirementAuthoringDocumentSummary[]>("/requirement-authoring/documents");
}

export function createRequirementAuthoringDocument(payload: RequirementAuthoringDocumentCreateInput) {
  return api.post<RequirementAuthoringDocumentDetail>("/requirement-authoring/documents", payload);
}

export function getRequirementAuthoringDocument(documentId: string) {
  return api.get<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}`);
}

export function appendRequirementAuthoringMessage(documentId: string, content: string) {
  return api.post<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}/messages`, { content });
}

export function patchRequirementAuthoringFormFields(documentId: string, fields: Record<string, string>) {
  return api.patch<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}/form-fields`, {
    fields,
  });
}

export function patchRequirementAuthoringClause(documentId: string, clauseId: string, content: string) {
  return api.patch<RequirementAuthoringDocumentDetail>(
    `/requirement-authoring/documents/${documentId}/clauses/${clauseId}`,
    { content },
  );
}

export function runRequirementAuthoringCheck(documentId: string) {
  return api.post<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}/check`);
}

export function freezeRequirementAuthoringDocument(documentId: string) {
  return api.post<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}/freeze`);
}
