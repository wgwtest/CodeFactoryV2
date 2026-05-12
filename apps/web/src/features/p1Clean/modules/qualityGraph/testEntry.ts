import type { P1ModuleTestEntry } from "../../types";

export const qualityGraphTestEntry: P1ModuleTestEntry = {
  moduleId: "qualityGraph",
  smokeRoute: "/p1/archives/:archiveId/quality",
  verifies: ["消费 runtimeSnapshotId", "显示图谱质量指标", "不生成发布候选"],
};
