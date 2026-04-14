import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  DEFAULT_ARCHIVE_ID,
  getArchiveDocumentDetail,
  getArchiveDocuments,
  getArchiveEntities,
  getArchiveEvents,
  getArchiveGraph,
  getArchiveItemDetail,
  getArchiveProcesses,
  getArchiveReviewCandidates,
  getArchiveSummary,
} from "../lib/archiveKnowledge";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

describe("archive knowledge client", () => {
  beforeEach(() => {
    getMock.mockReset();
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
});
