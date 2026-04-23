import { api, resolveApiUrl } from "./api";
import type {
  ArchiveKnowledgeDocument,
  ArchiveKnowledgeDocumentDetail,
  ArchiveDocumentRuntimeContract,
  ArchiveDocumentRuntimeMode,
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

export type ArchiveDocumentRuntimeStreamHandlers = {
  onRuntime: (runtime: ArchiveDocumentRuntimeContract) => void;
  onHeartbeat?: (payload: Record<string, unknown>) => void;
  onError?: (error: Event | Error) => void;
};

export type ArchiveDocumentRuntimeStreamOptions = {
  intervalMs?: number;
  heartbeatMs?: number;
};

export type ArchiveDocumentRuntimeStreamSubscription = {
  close: () => void;
};

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

export function normalizeArchiveDocumentRuntime(runtime: ArchiveDocumentRuntimeContract): ArchiveDocumentRuntimeContract {
  const persistedStageIds =
    runtime.persisted_stage_ids?.length
      ? runtime.persisted_stage_ids
      : runtime.stages
          .filter((stage) => stage.status !== "pending" && stage.status !== "unavailable")
          .map((stage) => stage.stage_id);

  const runtimeMode: ArchiveDocumentRuntimeMode = runtime.runtime_mode ?? "legacy_fallback";

  return {
    ...runtime,
    runtime_mode: runtimeMode,
    persisted_stage_ids: persistedStageIds,
  };
}

export function getArchiveDocumentRuntime(documentId: string, archiveId = DEFAULT_ARCHIVE_ID) {
  return api
    .get<ArchiveDocumentRuntimeContract>(`${withArchiveId(archiveId)}/documents/${documentId}/runtime`)
    .then((response) => ({
      ...response,
      data: normalizeArchiveDocumentRuntime(response.data),
    }));
}

function buildArchiveDocumentRuntimeStreamUrl(
  documentId: string,
  archiveId: string,
  options?: ArchiveDocumentRuntimeStreamOptions,
) {
  const search = new URLSearchParams();
  if (options?.intervalMs) {
    search.set("interval_ms", String(options.intervalMs));
  }
  if (options?.heartbeatMs) {
    search.set("heartbeat_ms", String(options.heartbeatMs));
  }

  const pathname = `${withArchiveId(archiveId)}/documents/${documentId}/runtime/stream`;
  const query = search.toString();
  return resolveApiUrl(query ? `${pathname}?${query}` : pathname);
}

export function subscribeArchiveDocumentRuntime(
  documentId: string,
  archiveId = DEFAULT_ARCHIVE_ID,
  handlers: ArchiveDocumentRuntimeStreamHandlers,
  options?: ArchiveDocumentRuntimeStreamOptions,
): ArchiveDocumentRuntimeStreamSubscription {
  if (typeof EventSource === "undefined") {
    throw new Error("Current environment does not support EventSource");
  }

  const eventSource = new EventSource(buildArchiveDocumentRuntimeStreamUrl(documentId, archiveId, options));

  const runtimeListener = (event: MessageEvent<string>) => {
    try {
      const runtime = normalizeArchiveDocumentRuntime(JSON.parse(event.data) as ArchiveDocumentRuntimeContract);
      handlers.onRuntime(runtime);
    } catch (error) {
      handlers.onError?.(
        error instanceof Error ? error : new Error("Failed to parse archive document runtime stream payload"),
      );
    }
  };

  const heartbeatListener = (event: MessageEvent<string>) => {
    if (!handlers.onHeartbeat) {
      return;
    }

    try {
      handlers.onHeartbeat(JSON.parse(event.data) as Record<string, unknown>);
    } catch (error) {
      handlers.onError?.(
        error instanceof Error ? error : new Error("Failed to parse archive document runtime heartbeat payload"),
      );
    }
  };

  const streamErrorListener = (event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as { detail?: string };
      handlers.onError?.(new Error(payload.detail ?? "Archive document runtime stream returned an error event"));
    } catch {
      handlers.onError?.(new Error("Archive document runtime stream returned an error event"));
    }
  };

  const transportErrorListener = (event: Event) => {
    handlers.onError?.(event);
  };

  eventSource.addEventListener("runtime", runtimeListener as EventListener);
  eventSource.addEventListener("heartbeat", heartbeatListener as EventListener);
  eventSource.addEventListener("error", streamErrorListener as EventListener);
  eventSource.onerror = transportErrorListener;

  return {
    close() {
      eventSource.removeEventListener("runtime", runtimeListener as EventListener);
      eventSource.removeEventListener("heartbeat", heartbeatListener as EventListener);
      eventSource.removeEventListener("error", streamErrorListener as EventListener);
      eventSource.onerror = null;
      eventSource.close();
    },
  };
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
