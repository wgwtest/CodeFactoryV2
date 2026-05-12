import type { P1ModuleTestEntry } from "../../types";

export const intakeTestEntry: P1ModuleTestEntry = {
  moduleId: "intake",
  smokeRoute: "/p1/archives/:archiveId/intake",
  verifies: ["只依赖 archiveId", "输出 documentSetId 和 documents[]", "不直接修改策略或质量状态"],
};
