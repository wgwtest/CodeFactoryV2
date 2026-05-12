import { getArchiveDocuments, normalizeArchiveDocumentRuntime } from "../../../../lib/archiveKnowledge";
import { api, resolveApiUrl } from "../../../../lib/api";
import type { ArchiveDocumentRuntimeStreamOptions, ArchiveDocumentRuntimeStreamSubscription } from "../../../../lib/archiveKnowledge";
import type { RuntimeContract, RuntimeModuleInput } from "./types";

type RuntimeRequestInput = Pick<RuntimeModuleInput, "archiveId" | "documentId"> &
  Partial<Pick<RuntimeModuleInput, "documentSetId" | "policyPackageVersionId">>;

export type RuntimeStreamHandlers = {
  onRuntime: (runtime: RuntimeContract) => void;
  onHeartbeat?: (payload: Record<string, unknown>) => void;
  onError?: (error: Event | Error) => void;
};

function buildRuntimeParams(input: RuntimeRequestInput, options?: ArchiveDocumentRuntimeStreamOptions) {
  const params = new URLSearchParams();
  params.set("document_id", input.documentId);
  if (input.documentSetId) {
    params.set("document_set_id", input.documentSetId);
  }
  if (input.policyPackageVersionId) {
    params.set("policy_package_version_id", input.policyPackageVersionId);
  }
  if (options?.intervalMs) {
    params.set("interval_ms", String(options.intervalMs));
  }
  if (options?.heartbeatMs) {
    params.set("heartbeat_ms", String(options.heartbeatMs));
  }
  return params;
}

function normalizeRuntime(runtime: RuntimeContract): RuntimeContract {
  return normalizeArchiveDocumentRuntime(runtime) as RuntimeContract;
}

export function getRuntimeDocuments(archiveId: string) {
  return getArchiveDocuments(archiveId);
}

export function getRuntimeContract(input: RuntimeRequestInput) {
  return api.get<RuntimeContract>(`/archives/${input.archiveId}/runtime`, {
    params: {
      document_id: input.documentId,
      document_set_id: input.documentSetId,
      policy_package_version_id: input.policyPackageVersionId,
    },
  }).then((response) => ({
    ...response,
    data: normalizeRuntime(response.data),
  }));
}

export function subscribeRuntimeContract(
  input: RuntimeRequestInput,
  handlers: RuntimeStreamHandlers,
  options?: ArchiveDocumentRuntimeStreamOptions,
): ArchiveDocumentRuntimeStreamSubscription {
  if (typeof EventSource === "undefined") {
    throw new Error("Current environment does not support EventSource");
  }

  const params = buildRuntimeParams(input, options);
  const eventSource = new EventSource(resolveApiUrl(`/archives/${input.archiveId}/runtime/stream?${params.toString()}`));

  const runtimeListener = (event: MessageEvent<string>) => {
    try {
      handlers.onRuntime(normalizeRuntime(JSON.parse(event.data) as RuntimeContract));
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error : new Error("Failed to parse archive runtime stream payload"));
    }
  };

  const heartbeatListener = (event: MessageEvent<string>) => {
    if (!handlers.onHeartbeat) {
      return;
    }
    try {
      handlers.onHeartbeat(JSON.parse(event.data) as Record<string, unknown>);
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error : new Error("Failed to parse archive runtime heartbeat payload"));
    }
  };

  const streamErrorListener = (event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as { detail?: string };
      handlers.onError?.(new Error(payload.detail ?? "Archive runtime stream returned an error event"));
    } catch {
      handlers.onError?.(new Error("Archive runtime stream returned an error event"));
    }
  };

  eventSource.addEventListener("runtime", runtimeListener as EventListener);
  eventSource.addEventListener("heartbeat", heartbeatListener as EventListener);
  eventSource.addEventListener("error", streamErrorListener as EventListener);
  eventSource.onerror = (event) => handlers.onError?.(event);

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

export function startRuntimeExtraction(archiveId: string) {
  return api.post(`/archives/${archiveId}/extract`);
}

export function canUseRuntimeStream() {
  return typeof EventSource !== "undefined";
}

export const runtimeApi = {
  canUseRuntimeStream,
  getRuntimeContract,
  getRuntimeDocuments,
  startRuntimeExtraction,
  subscribeRuntimeContract,
};
