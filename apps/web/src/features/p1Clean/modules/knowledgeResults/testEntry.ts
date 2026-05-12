import type { P1ModuleTestEntry } from "../../types";

export const knowledgeResultsTestEntry: P1ModuleTestEntry = {
  moduleId: "knowledgeResults",
  smokeRoute: "/p1/archives/:archiveId/results",
  verifies: [
    "只通过 knowledgeResults/api.ts 读取知识成果",
    "区分抽取工作态、发布候选态和正式入库态",
    "展示知识对象、关系、证据和来源文档",
  ],
};
