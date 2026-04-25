# P6.1 Portal Blueprint Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前门户试验稿重构为归属 `P6.1` 的全屏蓝图画布，并用右下角图例承载 `P6.2 ~ P6.4` 的占位说明。

**Architecture:** 放弃“页面头图 + 弹窗摘要 + 中心点连线”的旧实现，改为统一视口、世界坐标、锚点连线、单击高亮、双击进入的蓝图画布结构。页面仍采用 React 前端实现，但以“画布视口 + 节点层 + 连线层 + 图例层”的混合路线组织。

**Tech Stack:** React 18、TypeScript、React Router 6、Vitest、Testing Library、CSS transforms、SVG wires、localStorage

---

### Task 1: 更新 P6 文档与本地 WBS 承载

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Modify: `docs/superpowers/specs/2026-04-17-portal-home-design.md`
- Create: `docs/superpowers/issues/2026-04-17-p6-platform-entry-issue-tree-mirror.md`

- [ ] 明确 `P6` 为平台入口层一级节点
- [ ] 将门户页改挂 `P6.1`
- [ ] 为 `P6.2 ~ P6.4` 写入占位说明

### Task 2: 用测试锁定新门户行为

**Files:**
- Create: `apps/web/src/test/P6PortalPage.test.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] `/portal` 仍必须绕开 `MainShell`
- [ ] 页面必须出现 `P6.1 门户蓝图画布`
- [ ] 页面不得再出现旧的头图提示词
- [ ] 单击节点不得弹出摘要卡
- [ ] 双击节点必须进入业务页
- [ ] 布局记忆仍然成立

### Task 3: 将门户实现迁移到 P6 命名空间

**Files:**
- Create: `apps/web/src/components/p6/p6PortalData.ts`
- Create: `apps/web/src/components/p6/P6BlueprintCanvas.tsx`
- Create: `apps/web/src/components/p6/P6BlueprintNode.tsx`
- Create: `apps/web/src/components/p6/P6BlueprintLegend.tsx`
- Create: `apps/web/src/pages/P6PortalPage.tsx`
- Create: `apps/web/src/pages/P6PortalPage.css`
- Modify: `apps/web/src/App.tsx`
- Delete: `apps/web/src/components/portal/*`
- Delete: `apps/web/src/pages/PortalHomePage.tsx`
- Delete: `apps/web/src/pages/PortalHomePage.css`

- [ ] 迁移到 `p6` 命名空间
- [ ] 保留 `/portal` 路由，但归属 `P6PortalPage`
- [ ] 删除旧弹窗摘要实现

### Task 4: 实现统一视口、锚点连线与图例

**Files:**
- Modify: `apps/web/src/components/p6/p6PortalData.ts`
- Modify: `apps/web/src/components/p6/P6BlueprintCanvas.tsx`
- Modify: `apps/web/src/components/p6/P6BlueprintNode.tsx`
- Modify: `apps/web/src/components/p6/P6BlueprintLegend.tsx`
- Modify: `apps/web/src/pages/P6PortalPage.css`

- [ ] 节点使用统一世界坐标
- [ ] 视口支持平移与缩放
- [ ] 连线从 pin/锚点出发
- [ ] 右下角图例承载 P6 信息
- [ ] 单击只高亮，双击进入

### Task 5: 验证、提交并推送

**Files:**
- Verify: `apps/web/src/test/P6PortalPage.test.tsx`
- Verify: `apps/web/src/test/AppRoutes.test.tsx`

- [ ] 运行 `npm test -- --run src/test/P6PortalPage.test.tsx src/test/AppRoutes.test.tsx`
- [ ] 运行 `npm run build`
- [ ] 启动前端供用户查看 `/portal`
- [ ] 提交并推送仅包含 P6 门户相关改动

### Task 6: 对照远端评论补齐 P6.1 语言与规则层

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Modify: `docs/superpowers/specs/2026-04-17-portal-home-design.md`
- Modify: `docs/superpowers/issues/2026-04-17-p6-platform-entry-issue-tree-mirror.md`

- [ ] 将 `P6.1` 拆解为 `P6.1.1 ~ P6.1.4`
- [ ] 明确元素分类、图形语言与表现约束
- [ ] 明确连线语义、流向编码与拥塞处理规则
- [ ] 明确拖拽边界、自动布局与人工覆盖的交互规则
- [ ] 明确门户主节点、关系、产物和布局的投影数据模型
