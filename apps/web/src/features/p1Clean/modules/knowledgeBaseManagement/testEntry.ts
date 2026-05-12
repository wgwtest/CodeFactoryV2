import type { P1ModuleTestEntry } from "../../types";

export const knowledgeBaseManagementTestEntry: P1ModuleTestEntry = {
  moduleId: "knowledgeBaseManagement",
  smokeRoute: "/p1",
  verifies: ["真实知识库列表加载", "进入工作区路由包含 archiveId", "不显示工作区内部导航"],
};
