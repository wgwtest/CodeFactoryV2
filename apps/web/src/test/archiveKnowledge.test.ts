import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  DEFAULT_ARCHIVE_ID,
  getArchiveDocumentDetail,
  getArchiveDocumentRuntime,
  getArchiveDocuments,
  getArchiveEntities,
  getArchiveEvents,
  getArchiveGraph,
  getArchiveItemDetail,
  getArchiveProcesses,
  getArchiveReviewCandidates,
  getArchiveSummary,
  subscribeArchiveDocumentRuntime,
} from "../lib/archiveKnowledge";

const getMock = vi.fn();
const eventSourceInstances: EventSourceMock[] = [];

class EventSourceMock {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readonly url: string;
  readonly close = vi.fn(() => {
    this.readyState = EventSourceMock.CLOSED;
  });
  onerror: ((event: Event) => void) | null = null;
  readyState = EventSourceMock.CONNECTING;
  private listeners = new Map<string, Set<EventListener>>();

  constructor(url: string) {
    this.url = url;
    eventSourceInstances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)?.add(listener);
  }

  removeEventListener(type: string, listener: EventListener) {
    this.listeners.get(type)?.delete(listener);
  }

  emit(type: string, data: string) {
    const event = { data } as MessageEvent<string>;
    this.listeners.get(type)?.forEach((listener) => listener(event as unknown as Event));
  }

  emitNetworkError() {
    this.onerror?.(new Event("error"));
  }
}

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
  resolveApiUrl: (path: string) => `/api${path}`,
}));

describe("archive knowledge client", () => {
  beforeEach(() => {
    getMock.mockReset();
    eventSourceInstances.length = 0;
    vi.stubGlobal("EventSource", EventSourceMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("uses the default archive id for standard archive knowledge queries", async () => {
    getMock.mockResolvedValue({ data: {} });

    await getArchiveSummary();
    await getArchiveDocuments();
    await getArchiveDocumentDetail("doc-1");
    await getArchiveReviewCandidates();
    await getArchiveGraph();
    await getArchiveEntities();
    await getArchiveEvents();
    await getArchiveItemDetail("item-1");
    await getArchiveProcesses();

    expect(DEFAULT_ARCHIVE_ID).toBe("20161116-nas");
    expect(getMock).toHaveBeenNthCalledWith(1, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/summary`);
    expect(getMock).toHaveBeenNthCalledWith(2, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/documents`);
    expect(getMock).toHaveBeenNthCalledWith(3, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/documents/doc-1`);
    expect(getMock).toHaveBeenNthCalledWith(4, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/review-candidates`);
    expect(getMock).toHaveBeenNthCalledWith(5, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/graph`);
    expect(getMock).toHaveBeenNthCalledWith(6, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/entities`);
    expect(getMock).toHaveBeenNthCalledWith(7, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/events`);
    expect(getMock).toHaveBeenNthCalledWith(8, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/items/item-1`);
    expect(getMock).toHaveBeenNthCalledWith(9, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/processes`);
  });

  test("passes selected source documents as knowledge query params", async () => {
    getMock.mockResolvedValue({ data: {} });

    await getArchiveSummary(DEFAULT_ARCHIVE_ID, { documentIds: ["doc-1", "doc-2"] });
    await getArchiveGraph(DEFAULT_ARCHIVE_ID, { documentIds: ["doc-1"] });
    await getArchiveEntities(DEFAULT_ARCHIVE_ID, { documentIds: ["doc-1"] });
    await getArchiveEvents(DEFAULT_ARCHIVE_ID, { documentIds: ["doc-2"] });
    await getArchiveProcesses(DEFAULT_ARCHIVE_ID, { documentIds: ["doc-2"] });
    await getArchiveItemDetail("item-1", DEFAULT_ARCHIVE_ID, { documentIds: ["doc-1"] });

    expect(getMock).toHaveBeenNthCalledWith(1, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/summary`, {
      params: { document_ids: "doc-1,doc-2" },
    });
    expect(getMock).toHaveBeenNthCalledWith(2, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/graph`, {
      params: { document_ids: "doc-1" },
    });
    expect(getMock).toHaveBeenNthCalledWith(3, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/entities`, {
      params: { document_ids: "doc-1" },
    });
    expect(getMock).toHaveBeenNthCalledWith(4, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/events`, {
      params: { document_ids: "doc-2" },
    });
    expect(getMock).toHaveBeenNthCalledWith(5, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/processes`, {
      params: { document_ids: "doc-2" },
    });
    expect(getMock).toHaveBeenNthCalledWith(6, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/items/item-1`, {
      params: { document_ids: "doc-1" },
    });
  });

  test("normalizes archive document runtime responses", async () => {
    getMock.mockResolvedValue({
      data: {
        archive_id: DEFAULT_ARCHIVE_ID,
        document_id: "doc-1",
        document_title: "SV-2",
        current_stage_id: "parser_router",
        current_stage_label: "Parser Router",
        status: "running",
        source_document: {},
        stages: [
          {
            stage_id: "asset_intake",
            label: "Asset Intake",
            group: "Asset Intake and Normalization",
            order: 1,
            status: "completed",
            is_current: false,
            graph: { nodes: [], edges: [], primary_node_ids: [], primary_edge_ids: [] },
            stage_observer: { mode: "stage", title: "Asset Intake", status: "completed", stream: [], sections: [], actions: [] },
            node_observers: {},
            edge_observers: {},
          },
          {
            stage_id: "parser_router",
            label: "Parser Router",
            group: "Asset Intake and Normalization",
            order: 2,
            status: "running",
            is_current: true,
            graph: { nodes: [], edges: [], primary_node_ids: [], primary_edge_ids: [] },
            stage_observer: { mode: "stage", title: "Parser Router", status: "running", stream: [], sections: [], actions: [] },
            node_observers: {},
            edge_observers: {},
          },
        ],
      },
    });

    const response = await getArchiveDocumentRuntime("doc-1");

    expect(response.data.runtime_mode).toBe("legacy_fallback");
    expect(response.data.persisted_stage_ids).toEqual(["asset_intake", "parser_router"]);
  });

  test("subscribes to the archive document runtime stream and parses runtime events", () => {
    const onRuntime = vi.fn();
    const onError = vi.fn();

    const subscription = subscribeArchiveDocumentRuntime("doc-1", DEFAULT_ARCHIVE_ID, { onRuntime, onError }, {
      intervalMs: 1200,
      heartbeatMs: 9000,
    });

    expect(eventSourceInstances).toHaveLength(1);
    expect(eventSourceInstances[0]?.url).toBe(
      `/api/knowledge/archive/${DEFAULT_ARCHIVE_ID}/documents/doc-1/runtime/stream?interval_ms=1200&heartbeat_ms=9000`,
    );

    eventSourceInstances[0]?.emit(
      "runtime",
      JSON.stringify({
        archive_id: DEFAULT_ARCHIVE_ID,
        document_id: "doc-1",
        document_title: "SV-2",
        current_stage_id: "parser_router",
        current_stage_label: "Parser Router",
        status: "running",
        source_document: {},
        stages: [
          {
            stage_id: "asset_intake",
            label: "Asset Intake",
            group: "Asset Intake and Normalization",
            order: 1,
            status: "completed",
            is_current: false,
            graph: { nodes: [], edges: [], primary_node_ids: [], primary_edge_ids: [] },
            stage_observer: { mode: "stage", title: "Asset Intake", status: "completed", stream: [], sections: [], actions: [] },
            node_observers: {},
            edge_observers: {},
          },
        ],
      }),
    );

    expect(onRuntime).toHaveBeenCalledWith(
      expect.objectContaining({
        runtime_mode: "legacy_fallback",
        persisted_stage_ids: ["asset_intake"],
      }),
    );
    expect(onError).not.toHaveBeenCalled();

    subscription.close();
    expect(eventSourceInstances[0]?.close).toHaveBeenCalled();
  });

  test("reports stream parse and transport errors", () => {
    const onRuntime = vi.fn();
    const onError = vi.fn();

    subscribeArchiveDocumentRuntime("doc-1", DEFAULT_ARCHIVE_ID, { onRuntime, onError });

    eventSourceInstances[0]?.emit("runtime", "{invalid-json");
    eventSourceInstances[0]?.emit("error", JSON.stringify({ detail: "stream failed" }));
    eventSourceInstances[0]?.emitNetworkError();

    expect(onRuntime).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(3);
    expect(onError.mock.calls[1]?.[0]).toBeInstanceOf(Error);
    expect((onError.mock.calls[1]?.[0] as Error).message).toContain("stream failed");
    expect(onError.mock.calls[2]?.[0]).toBeInstanceOf(Event);
  });
});
