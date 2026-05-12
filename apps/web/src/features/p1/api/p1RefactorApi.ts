import { api, resolveApiUrl } from "../../../lib/api";
import type {
  ArchiveKnowledgeResolutionSnapshot,
  DocumentRuntimeSnapshot,
  EvaluationRunReport,
  P1KnowledgeSupplyExport,
  P1RefactorBootstrap,
  P1ResponseEnvelope,
  P6DisplayExportContractV2,
  PolicyPackage,
  PolicyPackageVersion,
  PublicationCandidateSnapshot,
  RuleContract,
} from "../contracts";

export type P1DocumentRuntimeStreamHandlers = {
  onRuntime: (snapshot: DocumentRuntimeSnapshot, envelope: P1ResponseEnvelope<DocumentRuntimeSnapshot>) => void;
  onHeartbeat?: (payload: Record<string, unknown>) => void;
  onError?: (error: Event | Error) => void;
};

export type P1DocumentRuntimeStreamOptions = {
  intervalMs?: number;
  heartbeatMs?: number;
};

export type P1DocumentRuntimeStreamSubscription = {
  close: () => void;
};

export async function getP1RefactorBootstrap(): Promise<P1ResponseEnvelope<P1RefactorBootstrap>> {
  const { data } = await api.get<P1ResponseEnvelope<P1RefactorBootstrap>>("/p1/refactor/bootstrap");
  return data;
}

export async function getP1PolicyPackageFixture(): Promise<P1ResponseEnvelope<PolicyPackage>> {
  const { data } = await api.get<P1ResponseEnvelope<PolicyPackage>>("/p1/refactor/policy-package");
  return data;
}

export async function getP1PolicyPackageVersion(
  policyPackageVersionId: string,
): Promise<P1ResponseEnvelope<PolicyPackageVersion>> {
  const { data } = await api.get<P1ResponseEnvelope<PolicyPackageVersion>>(
    `/p1/refactor/policy-package/versions/${policyPackageVersionId}`,
  );
  return data;
}

export async function getP1RuleContract(
  policyPackageVersionId: string,
  ruleId: string,
): Promise<P1ResponseEnvelope<RuleContract>> {
  const { data } = await api.get<P1ResponseEnvelope<RuleContract>>(
    `/p1/refactor/policy-package/versions/${policyPackageVersionId}/rules/${ruleId}`,
  );
  return data;
}

export async function getP1DocumentRuntimeSnapshot(
  archiveId: string,
  documentId: string,
): Promise<P1ResponseEnvelope<DocumentRuntimeSnapshot>> {
  const { data } = await api.get<P1ResponseEnvelope<DocumentRuntimeSnapshot>>(
    `/p1/archives/${archiveId}/documents/${documentId}/runtime`,
  );
  return data;
}

export async function getP1EvaluationReport(
  archiveId: string,
  runId: string,
): Promise<P1ResponseEnvelope<EvaluationRunReport>> {
  const { data } = await api.get<P1ResponseEnvelope<EvaluationRunReport>>(
    `/p1/archives/${archiveId}/runs/${runId}/evaluation-report`,
  );
  return data;
}

export async function getP1KnowledgeResolutionSnapshot(
  archiveId: string,
): Promise<P1ResponseEnvelope<ArchiveKnowledgeResolutionSnapshot>> {
  const { data } = await api.get<P1ResponseEnvelope<ArchiveKnowledgeResolutionSnapshot>>(
    `/p1/archives/${archiveId}/knowledge-resolution/latest`,
  );
  return data;
}

export async function getP1PublicationCandidateSnapshot(
  archiveId: string,
): Promise<P1ResponseEnvelope<PublicationCandidateSnapshot>> {
  const { data } = await api.get<P1ResponseEnvelope<PublicationCandidateSnapshot>>(
    `/p1/archives/${archiveId}/publication-candidates/latest`,
  );
  return data;
}

export async function getP1KnowledgeSupplyExport(): Promise<P1ResponseEnvelope<P1KnowledgeSupplyExport>> {
  const { data } = await api.get<P1ResponseEnvelope<P1KnowledgeSupplyExport>>("/p1/knowledge-supply/read");
  return data;
}

export async function getP1P6DisplayExport(): Promise<P1ResponseEnvelope<P6DisplayExportContractV2>> {
  const { data } = await api.get<P1ResponseEnvelope<P6DisplayExportContractV2>>("/p1/knowledge-supply/graph/query");
  return data;
}

function buildP1RuntimeStreamUrl(
  archiveId: string,
  documentId: string,
  options?: P1DocumentRuntimeStreamOptions,
) {
  const search = new URLSearchParams();
  if (options?.intervalMs) {
    search.set("interval_ms", String(options.intervalMs));
  }
  if (options?.heartbeatMs) {
    search.set("heartbeat_ms", String(options.heartbeatMs));
  }

  const pathname = `/p1/archives/${archiveId}/documents/${documentId}/runtime/stream`;
  const query = search.toString();
  return resolveApiUrl(query ? `${pathname}?${query}` : pathname);
}

function parseRuntimeEnvelope(raw: string): P1ResponseEnvelope<DocumentRuntimeSnapshot> {
  const payload = JSON.parse(raw) as P1ResponseEnvelope<DocumentRuntimeSnapshot> | DocumentRuntimeSnapshot;
  if ("data" in payload && payload.data) {
    return payload as P1ResponseEnvelope<DocumentRuntimeSnapshot>;
  }

  return {
    contract_version: "p1.document_runtime.r0",
    source_kind: "live",
    generated_at: new Date().toISOString(),
    data: payload as DocumentRuntimeSnapshot,
    warnings: ["Runtime stream returned a bare snapshot; normalized to P1 response envelope."],
  };
}

export function createP1RuntimeEventSource(
  archiveId: string,
  documentId: string,
  options?: P1DocumentRuntimeStreamOptions,
): EventSource {
  return new EventSource(buildP1RuntimeStreamUrl(archiveId, documentId, options));
}

export function subscribeP1DocumentRuntimeSnapshot(
  archiveId: string,
  documentId: string,
  handlers: P1DocumentRuntimeStreamHandlers,
  options?: P1DocumentRuntimeStreamOptions,
): P1DocumentRuntimeStreamSubscription {
  if (typeof EventSource === "undefined") {
    throw new Error("Current environment does not support EventSource");
  }

  const eventSource = createP1RuntimeEventSource(archiveId, documentId, options);

  const runtimeListener = (event: MessageEvent<string>) => {
    try {
      const envelope = parseRuntimeEnvelope(event.data);
      handlers.onRuntime(envelope.data, envelope);
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error : new Error("Failed to parse P1 runtime stream payload"));
    }
  };

  const heartbeatListener = (event: MessageEvent<string>) => {
    if (!handlers.onHeartbeat) {
      return;
    }

    try {
      handlers.onHeartbeat(JSON.parse(event.data) as Record<string, unknown>);
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error : new Error("Failed to parse P1 runtime heartbeat payload"));
    }
  };

  const streamErrorListener = (event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as { detail?: string };
      handlers.onError?.(new Error(payload.detail ?? "P1 runtime stream returned an error event"));
    } catch {
      handlers.onError?.(new Error("P1 runtime stream returned an error event"));
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
