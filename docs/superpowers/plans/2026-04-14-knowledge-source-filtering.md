# Knowledge Source Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为统一知识浏览器增加“来源文档筛选与素材对照”能力，默认浏览全部素材文档，也支持选择若干指定文档，只查看这些文档支撑出的统计、知识项、证据和图谱节点。

**Architecture:** 在后端发布态知识服务中新增按 `document_ids` 过滤的能力，由 API 在 `summary / graph / entities / events / processes / item detail / item graph` 等查询接口统一消费。前端知识图谱页新增来源文档多选控件，默认“全部素材文档”，选中文档后统一驱动知识列表、图谱视图、详情抽屉与统计数字的收敛。关系级来源尚未结构化到每条关系，本次先实现“按可见节点收敛关系”的可用版。

**Tech Stack:** FastAPI, Python, React 18, TypeScript, Ant Design 5, Vitest, Testing Library, pytest

---

### Task 1: 回写 WBS 承载节点

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Create: `docs/superpowers/plans/2026-04-14-knowledge-source-filtering.md`

- [x] **Step 1: 在 `P1.5.3` 下补充“来源文档筛选与素材对照”节点**
- [x] **Step 2: 写清本次改造的边界与非目标**

### Task 2: 先锁定来源筛选行为

**Files:**
- Modify: `apps/api/tests/test_archive_knowledge_api.py`
- Modify: `apps/web/src/test/archiveKnowledge.test.ts`
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [x] **Step 1: 先写失败测试，覆盖按文档来源过滤后的统计、列表、详情与图谱行为**
- [x] **Step 2: 跑定向测试，确认当前实现先红**

### Task 3: 为发布态知识查询补充来源过滤契约

**Files:**
- Modify: `apps/api/app/api/routes/knowledge.py`
- Modify: `apps/api/app/archive_knowledge/service.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/archiveKnowledge.ts`

- [x] **Step 1: 为知识查询接口增加 `document_ids` 过滤参数**
- [x] **Step 2: 在服务层统一实现按来源文档收敛 payload 的逻辑**
- [x] **Step 3: 保持详情、证据和图谱邻域与过滤结果一致**

### Task 4: 为统一知识浏览器增加来源筛选控件

**Files:**
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`

- [x] **Step 1: 加载当前知识库文档列表，作为来源筛选项**
- [x] **Step 2: 在总览层加入“来源文档”多选筛选**
- [x] **Step 3: 默认使用全部文档，选中后统一驱动知识数据重新加载**

### Task 5: 回归验证并提交

**Files:**
- Verify: `apps/api/tests/test_archive_knowledge_api.py`
- Verify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`
- Verify: `apps/web/src/test/archiveKnowledge.test.ts`

- [x] **Step 1: 跑 API 与前端定向测试**
- [x] **Step 2: 必要时跑前端相关全量测试**
- [x] **Step 3: 提交本地改动**
