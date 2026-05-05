import { api } from "./api";
import type {
  RequirementAuthoringDocumentCreateInput,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringDocumentSummary,
  RequirementAuthoringKnowledgeBinding,
  RequirementAuthoringKnowledgeProviderEnvelope,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateWriteInput,
  RequirementAuthoringWorkbenchConfig,
} from "./api";

export function getRequirementAuthoringWorkbenchConfig() {
  return api.get<RequirementAuthoringWorkbenchConfig>("/requirement-authoring/workbench-config");
}

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

export function getRequirementAuthoringKnowledgeProviders() {
  return api.get<RequirementAuthoringKnowledgeProviderEnvelope>("/requirement-authoring/knowledge-providers");
}

export function bindRequirementAuthoringKnowledge(providerId: string, domainId: string) {
  return api.post<RequirementAuthoringKnowledgeBinding>("/requirement-authoring/knowledge-bindings", {
    provider_id: providerId,
    domain_id: domainId,
  });
}

export function createRequirementAuthoringDocument(payload: RequirementAuthoringDocumentCreateInput) {
  return api.post<RequirementAuthoringDocumentDetail>("/requirement-authoring/documents", payload);
}

export function getRequirementAuthoringDocument(documentId: string) {
  return api.get<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}`);
}

export function deleteRequirementAuthoringDocument(documentId: string) {
  return api.delete<{ deleted: boolean; document_id: string }>(`/requirement-authoring/documents/${documentId}`);
}

export function saveRequirementAuthoringDocument(
  documentId: string,
  payload: {
    title?: string | null;
    template_id?: string | null;
    archive_ids?: string[] | null;
    knowledge_binding?: RequirementAuthoringKnowledgeBinding | null;
  } = {},
) {
  return api.post<RequirementAuthoringDocumentDetail>(`/requirement-authoring/documents/${documentId}/save`, payload);
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
