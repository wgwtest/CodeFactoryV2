# Knowledge Source Filtering Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正知识图谱页来源文档筛选器的交互问题，提供稳定摘要显示、显式全选/清空操作，并避免误清空已选来源。

**Architecture:** 保留现有来源文档多选 `Select`，不重做为新组件。通过自定义已选摘要、去除控件自带清空入口、在下拉面板增加“全选 / 清空”操作来修正交互，同时以页面测试锁定行为。

**Tech Stack:** React 18, TypeScript, Ant Design 5, Vitest, Testing Library

---

### Task 1: 回写 WBS 与交互范围

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Create: `docs/superpowers/plans/2026-04-14-knowledge-source-filtering-usability.md`

- [x] **Step 1: 在 `P1.5.3.2` 下补充“来源筛选器可用性修正”子节点**
- [x] **Step 2: 写清本次仅修复来源选择器交互，不改变来源过滤的数据语义**

### Task 2: 先锁定来源筛选器行为

**Files:**
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [x] **Step 1: 先写失败测试，覆盖稳定摘要显示、显式全选/清空、再次展开不误清空**
- [x] **Step 2: 运行定向前端测试，确认当前实现先红**

### Task 3: 修正来源筛选器交互实现

**Files:**
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx`

- [x] **Step 1: 移除易误触的控件自带清空入口**
- [x] **Step 2: 改为稳定的已选摘要显示**
- [x] **Step 3: 在下拉面板增加“全选 / 清空”操作**

### Task 4: 回归验证并提交

**Files:**
- Verify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [x] **Step 1: 跑定向前端测试**
- [x] **Step 2: 必要时跑相关前端回归测试**
- [x] **Step 3: 提交本地改动**
