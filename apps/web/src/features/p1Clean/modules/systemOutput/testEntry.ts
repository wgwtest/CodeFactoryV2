import type { P1ModuleTestEntry } from "../../types";

export const systemOutputTestEntry: P1ModuleTestEntry = {
  moduleId: "systemOutput",
  smokeRoute: "/p1/archives/:archiveId/system-output",
  verifies: ["消费 publicationSnapshotId", "列出正式系统间接口", "不读取抽取临时节点"],
};
