import { api } from "./api";
import type {
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeDocumentDetail,
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeProcess,
  ArchiveKnowledgeSummary,
  ArchiveReviewCandidate,
} from "./api";

export const DEFAULT_ARCHIVE_ID = "20161116-nas";

function withArchiveId(archiveId: string) {
  return `/knowledge/archive/${archiveId}`;
}

export function getArchiveSummary(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeSummary>(`${withArchiveId(archiveId)}/summary`);
}

export function getArchiveDocuments(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeDocument[]>(`${withArchiveId(archiveId)}/documents`);
}

export function getArchiveDocumentDetail(documentId: string, archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeDocumentDetail>(`${withArchiveId(archiveId)}/documents/${documentId}`);
}

export function getArchiveReviewCandidates(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveReviewCandidate[]>(`${withArchiveId(archiveId)}/review-candidates`);
}

export function getArchiveGraph(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeGraph>(`${withArchiveId(archiveId)}/graph`);
}

export function getArchiveEntities(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeEntity[]>(`${withArchiveId(archiveId)}/entities`);
}

export function getArchiveItemDetail(itemId: string, archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeItemDetail>(`${withArchiveId(archiveId)}/items/${itemId}`);
}

export function getArchiveProcesses(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchiveKnowledgeProcess[]>(`${withArchiveId(archiveId)}/processes`);
}
