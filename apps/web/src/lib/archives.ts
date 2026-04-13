import { api } from "./api";
import type { CreateKnowledgeArchiveInput, KnowledgeArchive } from "./api";

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
