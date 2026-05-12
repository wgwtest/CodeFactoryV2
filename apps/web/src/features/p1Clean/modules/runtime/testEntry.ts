import type { P1ModuleTestEntry } from "../../types";

export const runtimeTestEntry: P1ModuleTestEntry = {
  moduleId: "runtime",
  smokeRoute: "/p1/archives/:archiveId/runtime",
  verifies: ["运行上下文显示", "输出 runtimeSnapshotId", "不修改策略版本"],
};
