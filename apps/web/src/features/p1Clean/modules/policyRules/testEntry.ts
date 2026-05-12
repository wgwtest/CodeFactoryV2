import type { P1ModuleTestEntry } from "../../types";

export const policyRulesTestEntry: P1ModuleTestEntry = {
  moduleId: "policyRules",
  smokeRoute: "/p1/archives/:archiveId/policy",
  verifies: ["策略版本通过模块 API 读取", "规则 I/O 合同可编辑并校验", "规则变更只生成 ImpactSet 与候选重算任务"],
};
