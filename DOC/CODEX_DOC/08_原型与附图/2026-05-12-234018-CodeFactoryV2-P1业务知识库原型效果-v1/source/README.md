# Source 说明

本版本包包含一个独立静态 HTML 原型源文件：

- `p1-consumer-views-prototype.html`

该文件用于生成第 5 章新增的 5 张消费者视图原型图：

- `14-1920x1080-消费者知识库总览驾驶舱.png`
- `15-1920x1080-消费者知识库查询页.png`
- `16-1920x1080-消费者目标问题知识结果页.png`
- `17-1920x1080-消费者知识对象与证据阅读页.png`
- `18-1920x1080-消费者图谱探索与版本说明页.png`

本版是基于当前代码实现、`P1` 软件设计说明和既有 P1 历史方向图整理出的“原型效果说明”。当前真实页面源代码位于：

- `apps/web/src/App.tsx`
- `apps/web/src/features/p1Clean/`
- `apps/web/src/pages/ArchiveManagementPage.tsx`
- `apps/web/src/pages/DocumentsPage.tsx`
- `apps/web/src/pages/DocumentIntakePage.tsx`
- `apps/web/src/pages/P1PrototypeWorkflowPages.tsx`
- `apps/web/src/pages/GovernancePage.tsx`
- `apps/web/src/pages/KnowledgeGraphPage.tsx`

后续如果需要逐像素验收，应启动真实前后端，对 `/p1` 与 `/p1/archives/:archiveId/*` 进行运行态截图，并把截图回填到本版本包。
