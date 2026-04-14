# Archive Management Extraction Logic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在知识库管理页增加抽取逻辑说明区，并把长文档正式抽取规则固化到设计与工程约束中。

**Architecture:** 先在平台设计与正式抽取硬门槛设计中补充“长文档分块抽取与全局归并”约束，再以知识库管理页作为验证投影，把正式链路、三层数据语义和当前受限模式直接展示给用户。页面布局改为左右双栏，左侧保留精简表单，右侧承载抽取逻辑说明。

**Tech Stack:** React 18, TypeScript, Ant Design 5, Vitest, Testing Library, Markdown specs

---

### Task 1: 回写 WBS 与正式抽取规则

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Modify: `docs/superpowers/specs/2026-04-14-formal-archive-extraction-hard-gate-design.md`
- Create: `docs/superpowers/plans/2026-04-14-archive-management-extraction-logic.md`

- [x] **Step 1: 在平台设计中补充知识库管理页说明面板与长文档抽取规则节点**
- [x] **Step 2: 在正式抽取硬门槛设计中补充长文档正式抽取规则**

### Task 2: 先锁定知识库管理页的新验证投影

**Files:**
- Modify: `apps/web/src/test/ArchiveManagementPage.test.tsx`

- [x] **Step 1: 先写失败测试，覆盖抽取逻辑说明区和三层数据语义文案**
- [x] **Step 2: 运行定向测试，确认当前实现先红**

### Task 3: 改造知识库管理页为左右双栏

**Files:**
- Modify: `apps/web/src/pages/ArchiveManagementPage.tsx`

- [x] **Step 1: 将新增知识库区域改为左右双栏**
- [x] **Step 2: 左栏保留精简表单与创建动作**
- [x] **Step 3: 右栏新增正式抽取逻辑说明、三层数据语义和当前限制说明**

### Task 4: 回归验证

**Files:**
- Verify: `apps/web/src/test/ArchiveManagementPage.test.tsx`
- Verify: `apps/web/src/pages/ArchiveManagementPage.tsx`

- [x] **Step 1: 跑定向前端测试**
- [x] **Step 2: 跑前端构建，确认类型与打包通过**
- [x] **Step 3: 视结果决定是否提交本地改动**
