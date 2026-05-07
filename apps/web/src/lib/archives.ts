import { api } from "./api";
import type {
  ArchivePolicyConfig,
  ArchiveIncrementalRebuildTask,
  ArchiveDocumentFormalizeResult,
  ArchiveDocumentImportResult,
  CreateKnowledgeArchiveInput,
  KnowledgeArchive,
  UpdateArchivePolicyConfigInput,
} from "./api";

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

export function getArchivePolicyConfig(archiveId: string) {
  return api.get<ArchivePolicyConfig>(`/archives/${archiveId}/policy-config`);
}

export function updateArchivePolicyConfig(archiveId: string, payload: UpdateArchivePolicyConfigInput) {
  return api.put<ArchivePolicyConfig>(`/archives/${archiveId}/policy-config`, payload);
}

export function listArchiveIncrementalRebuildTasks(archiveId: string) {
  return api.get<ArchiveIncrementalRebuildTask[]>(`/archives/${archiveId}/incremental-rebuild-tasks`);
}

export function getArchiveIncrementalRebuildTask(archiveId: string, taskId: string) {
  return api.get<ArchiveIncrementalRebuildTask>(`/archives/${archiveId}/incremental-rebuild-tasks/${taskId}`);
}

export function formalizeArchiveDocument(archiveId: string, documentId: string) {
  return api.post<ArchiveDocumentFormalizeResult>(`/archives/${archiveId}/documents/${documentId}/formalize`);
}

export function importArchiveDocument(archiveId: string, file: File) {
  const payload = new FormData();
  payload.append("file", file);
  return api.post<ArchiveDocumentImportResult>(`/archives/${archiveId}/documents/import`, payload, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
}

export function removeArchiveDocument(archiveId: string, documentId: string) {
  return api.post<ArchiveDocumentFormalizeResult>(`/archives/${archiveId}/documents/${documentId}/remove`);
}
