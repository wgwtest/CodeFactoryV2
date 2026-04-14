import { api } from "./api";
import type {
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeDocumentDetail,
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeEvent,
  ArchiveKnowledgeItemGraph,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeProcess,
  ArchiveKnowledgeSummary,
  ArchivePublicationOverview,
  ArchiveReviewCandidate,
} from "./api";

export const DEFAULT_ARCHIVE_ID = "20161116-nas";

export type ArchiveKnowledgeQueryOptions = {
  documentIds?: string[];
};

function withArchiveId(archiveId: string) {
  return `/knowledge/archive/${archiveId}`;
}

function withQueryOptions(options?: ArchiveKnowledgeQueryOptions) {
  if (!options?.documentIds?.length) {
    return undefined;
  }

  return {
    params: {
      document_ids: options.documentIds.join(","),
    },
  };
}

export function getArchiveSummary(archiveId = DEFAULT_ARCHIVE_ID, options?: ArchiveKnowledgeQueryOptions) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeSummary>(`${withArchiveId(archiveId)}/summary`, queryOptions)
    : api.get<ArchiveKnowledgeSummary>(`${withArchiveId(archiveId)}/summary`);
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

export function getArchiveGraph(archiveId = DEFAULT_ARCHIVE_ID, options?: ArchiveKnowledgeQueryOptions) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeGraph>(`${withArchiveId(archiveId)}/graph`, queryOptions)
    : api.get<ArchiveKnowledgeGraph>(`${withArchiveId(archiveId)}/graph`);
}

export function getArchiveEntities(archiveId = DEFAULT_ARCHIVE_ID, options?: ArchiveKnowledgeQueryOptions) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeEntity[]>(`${withArchiveId(archiveId)}/entities`, queryOptions)
    : api.get<ArchiveKnowledgeEntity[]>(`${withArchiveId(archiveId)}/entities`);
}

export function getArchiveEvents(archiveId = DEFAULT_ARCHIVE_ID, options?: ArchiveKnowledgeQueryOptions) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeEvent[]>(`${withArchiveId(archiveId)}/events`, queryOptions)
    : api.get<ArchiveKnowledgeEvent[]>(`${withArchiveId(archiveId)}/events`);
}

export function getArchiveItemDetail(
  itemId: string,
  archiveId = DEFAULT_ARCHIVE_ID,
  options?: ArchiveKnowledgeQueryOptions,
) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeItemDetail>(`${withArchiveId(archiveId)}/items/${itemId}`, queryOptions)
    : api.get<ArchiveKnowledgeItemDetail>(`${withArchiveId(archiveId)}/items/${itemId}`);
}

export function getArchiveItemGraph(
  itemId: string,
  archiveId = DEFAULT_ARCHIVE_ID,
  options?: ArchiveKnowledgeQueryOptions,
) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeItemGraph>(`${withArchiveId(archiveId)}/items/${itemId}/graph`, queryOptions)
    : api.get<ArchiveKnowledgeItemGraph>(`${withArchiveId(archiveId)}/items/${itemId}/graph`);
}

export function getArchiveProcesses(archiveId = DEFAULT_ARCHIVE_ID, options?: ArchiveKnowledgeQueryOptions) {
  const queryOptions = withQueryOptions(options);
  return queryOptions
    ? api.get<ArchiveKnowledgeProcess[]>(`${withArchiveId(archiveId)}/processes`, queryOptions)
    : api.get<ArchiveKnowledgeProcess[]>(`${withArchiveId(archiveId)}/processes`);
}

export function getArchivePublication(archiveId = DEFAULT_ARCHIVE_ID) {
  return api.get<ArchivePublicationOverview>(`${withArchiveId(archiveId)}/publication`);
}
