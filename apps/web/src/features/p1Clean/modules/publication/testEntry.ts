import type { P1ModuleTestEntry } from "../../types";

export const publicationTestEntry: P1ModuleTestEntry = {
  moduleId: "publication",
  smokeRoute: "/p1/archives/:archiveId/publication",
  verifies: ["消费质量决策", "输出 publicationSnapshotId", "区分候选和正式输出"],
};
