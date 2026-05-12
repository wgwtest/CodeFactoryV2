import { api } from "../../../../lib/api";
import {
  getArchiveDocuments as requestArchiveDocuments,
  getArchiveSummary as requestArchiveSummary,
} from "../../../../lib/archiveKnowledge";
import {
  extractKnowledgeArchive as requestExtractKnowledgeArchive,
  importArchiveDocument as requestImportArchiveDocument,
} from "../../../../lib/archives";
import type { IntakeContractEnvelope } from "./types";

export function getArchiveDocuments(archiveId: string) {
  return requestArchiveDocuments(archiveId);
}

export function getArchiveSummary(archiveId: string) {
  return requestArchiveSummary(archiveId);
}

export function importArchiveDocument(archiveId: string, file: File) {
  return requestImportArchiveDocument(archiveId, file);
}

export function extractKnowledgeArchive(archiveId: string) {
  return requestExtractKnowledgeArchive(archiveId);
}

export function getIntakeSnapshot(archiveId: string) {
  return api.get<IntakeContractEnvelope>(`/p1/archives/${archiveId}/intake`);
}

export const intakeApi = {
  getArchiveDocuments,
  getArchiveSummary,
  getIntakeSnapshot,
  importArchiveDocument,
  extractKnowledgeArchive,
};
