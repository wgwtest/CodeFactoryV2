# Unified Knowledge Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“知识图谱 / 流程视图”收敛为统一知识浏览器，支持“实体 / 事件 / 流程”类型筛选与“列表 / 图谱”双视图组合浏览。

**Architecture:** 保留现有发布态知识接口与详情抽屉能力，但把页面交互从“实体页 + 独立流程页”升级为单页统一浏览。后端补齐事件接口与图谱节点类型信息；前端在知识图谱页顶层增加类型筛选和视图选择，并用统一知识项列表驱动内容区与图谱过滤。

**Tech Stack:** FastAPI, Python, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

### Task 1: 回写 WBS 承载节点

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Create: `docs/superpowers/plans/2026-04-14-unified-knowledge-browser.md`

- [ ] **Step 1: 在 `P1.5.3` 下新增统一知识浏览器节点**
- [ ] **Step 2: 写清本次改造的实现计划与边界**

### Task 2: 先锁定统一浏览页行为

**Files:**
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`
- Modify: `apps/web/src/test/archiveKnowledge.test.ts`
- Modify: `apps/api/tests/test_archive_knowledge_api.py`

- [ ] **Step 1: 先写失败测试，覆盖类型多选、视图二选一、流程页并入后的主行为**
- [ ] **Step 2: 跑定向测试，确认当前实现先红**

### Task 3: 补齐统一浏览所需的后端与客户端契约

**Files:**
- Modify: `apps/api/app/api/routes/knowledge.py`
- Modify: `apps/api/app/archive_knowledge/service.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/archiveKnowledge.ts`

- [ ] **Step 1: 暴露事件查询接口**
- [ ] **Step 2: 在图谱节点中补 `item_type`**
- [ ] **Step 3: 前端补齐 `events` 查询方法与统一节点类型定义**

### Task 4: 实现统一知识浏览页

**Files:**
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Modify: `apps/web/src/components/knowledgeTopology.ts`
- Modify: `apps/web/src/components/KnowledgeTopologyGraph.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: 将视图切换和类型筛选提升到“档案知识总览”层**
- [ ] **Step 2: 将内容区改为受“类型 + 视图”联合驱动**
- [ ] **Step 2.1: 列表主表新增“投影”列，位置固定为“类别”后、“释义”前**
- [ ] **Step 2.2: “投影”列展示中文主名、英文原名/缩写和中文化状态；“释义”列继续保留解释文本**
- [ ] **Step 3: 统一详情抽屉为知识项详情，不再绑定实体专用命名**
- [ ] **Step 4: 移除独立流程页入口，避免重复导航**

### Task 5: 回归验证并提交

**Files:**
- Verify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`
- Verify: `apps/web/src/test/archiveKnowledge.test.ts`
- Verify: `apps/api/tests/test_archive_knowledge_api.py`

- [ ] **Step 1: 跑 API 与前端定向测试**
- [ ] **Step 2: 必要时跑前端相关全量测试**
- [ ] **Step 3: 本地提交**
