import { api } from "./api";
import type { ArchiveDocumentFormalizeResult, CreateKnowledgeArchiveInput, KnowledgeArchive } from "./api";

export function getKnowledgeArchives() {
  return api.get<KnowledgeArchive[]>("/archives");
}

export function createKnowledgeArchive(payload: CreateKnowledgeArchiveInput) {
  return api.post<KnowledgeArchive>("/archives", payload);
}

export function activateKnowledgeArchive(archiveId: string) {
  return api.post<KnowledgeArchive>(`/archives/${archiveId}/activate`);
}

export function extractKnowledgeArchive(archiveId: string) {
  return api.post<KnowledgeArchive>(`/archives/${archiveId}/extract`);
}

export function formalizeArchiveDocument(archiveId: string, documentId: string) {
  return api.post<ArchiveDocumentFormalizeResult>(`/archives/${archiveId}/documents/${documentId}/formalize`);
}

export function removeArchiveDocument(archiveId: string, documentId: string) {
  return api.post<ArchiveDocumentFormalizeResult>(`/archives/${archiveId}/documents/${documentId}/remove`);
}
