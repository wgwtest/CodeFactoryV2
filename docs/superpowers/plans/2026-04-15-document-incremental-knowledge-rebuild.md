# Document Incremental Knowledge Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为知识库补齐“文档级正式抽取产物持久化 + 单文档正式并入/移出当前知识全集”正式能力，并提供前端验证入口。

**Architecture:** 后端新增文档级正式产物仓与文档纳入状态清单。整库正式抽取时同步落盘文档级产物并默认纳入；单文档正式并入时只重抽目标文档并重新纳入，单文档正式移出时保留正式产物但从全集聚合中排除。前端在文档页提供“正式并入/移出”切换、状态标签与知识库级禁用反馈。

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, React, Ant Design, Vitest, Docling, OpenAI-compatible structured LLM adapter

---

### Task 1: 回写 WBS 与专项设计

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Create: `docs/superpowers/specs/2026-04-15-document-incremental-knowledge-rebuild-design.md`

- [x] 把节点归位明确写成 `P1.3.5` 与 `P1.4.5`
- [x] 说明为什么该能力不属于 `P1.2`
- [x] 固化文档级产物仓、增量重建、治理态继承和前端验证入口设计

### Task 2: 先写后端失败测试

**Files:**
- Create: `apps/api/tests/test_archive_incremental_rebuild.py`
- Modify: `apps/api/tests/test_archive_registry_api.py`

- [ ] 先写“文档级正式产物聚合”失败测试
- [ ] 先写“单文档正式并入接口”失败测试
- [ ] 先写“单文档正式移出后仍保留文档产物，但从全集剔除”失败测试
- [ ] 运行定向测试，确认当前为红

### Task 3: 实现文档级正式产物仓与全集聚合

**Files:**
- Create: `apps/api/app/archive_knowledge/document_artifacts.py`
- Modify: `apps/api/app/knowledge_builder.py`
- Modify: `apps/api/app/archive_knowledge/builder.py`
- Modify: `apps/api/app/archive_knowledge/rebuild.py`
- Modify: `apps/api/app/archive_knowledge/service.py`

- [ ] 新增文档级正式产物序列化与清单管理
- [ ] 为文档级正式产物清单增加 `included_in_archive` 状态
- [ ] 把整库正式抽取改造成“先产出文档级产物，再聚合全集”
- [ ] 让文档页列表/详情优先读取文档级正式产物仓，支持查看已移出文档
- [ ] 补治理态保守继承规则
- [ ] 运行后端定向测试，确认转绿

### Task 4: 实现单文档正式并入/移出接口

**Files:**
- Modify: `apps/api/app/archive_knowledge/extraction.py`
- Modify: `apps/api/app/api/routes/archives.py`
- Modify: `apps/api/app/archive_knowledge/registry.py`

- [ ] 新增单文档正式并入服务
- [ ] 新增单文档正式移出服务
- [ ] 接入全局抽取协调器，禁止并发重复执行
- [ ] 返回明确的执行模式与更新摘要
- [ ] 运行相关 API 测试

### Task 5: 补前端验证入口

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/archives.ts`
- Modify: `apps/web/src/pages/DocumentsPage.tsx`
- Modify: `apps/web/src/test/DocumentsPage.test.tsx`

- [ ] 在已建库文档表增加“正式并入 / 正式移出”互斥操作
- [ ] 执行中在当前行显示“正在并入 / 正在移出”，并对整个知识库文档操作禁用
- [ ] 已并入文档默认切到“移出”，未并入文档显示“正式并入”
- [ ] 成功后刷新文档列表、摘要与当前详情抽屉
- [ ] 运行前端定向测试

### Task 6: 做完整回归验证

**Files:**
- Modify: `docs/development-policy.md`

- [ ] 跑后端测试：`uv run pytest apps/api/tests -q`
- [ ] 跑前端测试：`corepack pnpm --dir apps/web test`
- [ ] 视结果补充本地工程策略说明，明确该能力基于文档级正式产物仓实现
