import { describe, expect, test, vi } from "vitest";

import {
  DEFAULT_ARCHIVE_ID,
  getArchiveDocumentDetail,
  getArchiveDocuments,
  getArchiveEntities,
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
  test("uses the default archive id for standard archive knowledge queries", async () => {
    getMock.mockResolvedValue({ data: {} });

    await getArchiveSummary();
    await getArchiveDocuments();
    await getArchiveDocumentDetail("doc-1");
    await getArchiveReviewCandidates();
    await getArchiveGraph();
    await getArchiveEntities();
    await getArchiveItemDetail("item-1");
    await getArchiveProcesses();

    expect(DEFAULT_ARCHIVE_ID).toBe("20161116-nas");
    expect(getMock).toHaveBeenNthCalledWith(1, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/summary`);
    expect(getMock).toHaveBeenNthCalledWith(2, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/documents`);
    expect(getMock).toHaveBeenNthCalledWith(3, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/documents/doc-1`);
    expect(getMock).toHaveBeenNthCalledWith(4, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/review-candidates`);
    expect(getMock).toHaveBeenNthCalledWith(5, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/graph`);
    expect(getMock).toHaveBeenNthCalledWith(6, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/entities`);
    expect(getMock).toHaveBeenNthCalledWith(7, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/items/item-1`);
    expect(getMock).toHaveBeenNthCalledWith(8, `/knowledge/archive/${DEFAULT_ARCHIVE_ID}/processes`);
  });
});
