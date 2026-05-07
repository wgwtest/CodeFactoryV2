# P2 Session Phase And Decision State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 P2 需求分析 Lab 从固定四阶段写正文链路升级为“会话阶段 + 决策状态主循环 + A4 结构化状态承载页”的目标态实现，并同步主设计文档。

**Architecture:** 后端将探索阶段主循环收敛为“意图理解 -> 决策增量生成 -> 状态应用 -> 下一步交互规划”，把状态展示改为系统渲染，把正式落稿从探索主链路中拆出并先落会话阶段与快照基础。前端新增结构化状态 A4 页，按会话阶段切换展示和行为，并保留现有临时正文与完成度树作为投影视图。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, Vitest/Jest style frontend tests, pytest

---

### Task 1: 回写主设计文档

**Files:**
- Modify: `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`

- [ ] **Step 1: 将 5.7、6.6、9.2、10.7、10.8 相关章节改为会话阶段和调用链口径**

更新主文档，使其不再把 `write` / `review_after_apply` 作为探索阶段固定模型链路，而改为：

- 探索与收束阶段：意图理解、决策增量生成、状态应用、下一步交互规划
- 状态展示：系统渲染结构化状态 A4 页
- 落稿确认：冻结结构化状态快照
- 落稿与成稿：正式落稿与正文校核

- [ ] **Step 2: 自查主文档中的旧四阶段表述**

检查并替换以下旧概念：

- `intent_write_review_plan`
- `write`
- `review_after_apply`
- “四阶段模型阶段”

把它们改成会话阶段、调用链、处理节点的分层表述。

### Task 2: 写后端失败测试，锁定目标态 DTO 和执行链

**Files:**
- Modify: `apps/api/tests/test_requirement_analysis_api.py`
- Modify: `apps/api/tests/test_requirement_analysis_modules.py`

- [ ] **Step 1: 为会话阶段和结构化状态增加失败测试**

新增测试覆盖：

- 会话详情包含 `session_phase`
- 会话详情包含 `decision_state`
- 会话详情包含 `decision_state_document`
- 探索阶段 provider 日志只记录 3 个模型调用节点

- [ ] **Step 2: 为阶段规划与 reducer 目标态增加失败测试**

新增测试覆盖：

- 启发式组织器默认阶段序列为 `intent_understanding`、`decision_state_delta`、`next_interaction_planning`
- 不再包含探索阶段 `write` 和 `review_after_apply`
- 状态展示不产生 provider log

### Task 3: 后端实现会话阶段与结构化状态

**Files:**
- Modify: `apps/api/app/requirement_analysis/models.py`
- Modify: `apps/api/app/requirement_analysis/session_service.py`
- Modify: `apps/api/app/requirement_analysis/turn_engine.py`
- Modify: `apps/api/app/requirement_analysis/turn_stage_planner.py`
- Modify: `apps/api/app/requirement_analysis/turn_stage_reducer.py`
- Modify: `apps/api/app/requirement_analysis/provider_call_service.py`
- Modify: `apps/api/app/requirement_analysis/stage_runtime_context_builder.py`
- Modify: `apps/api/app/orchestrators/stage_prompt_resolver.py`
- Modify: `apps/api/app/orchestrators/stage_schema_resolver.py`
- Modify: `apps/api/app/orchestrators/stage_adoption_policy_resolver.py`
- Modify: `orchestrators/xg/xg-heuristic-orchestrator/spec_strategy.json`

- [ ] **Step 1: 增加会话阶段和结构化状态字段**

后端状态中新增：

- `session_phase`
- `decision_state`
- `decision_state_document`
- `draft_snapshot`（可为空）

- [ ] **Step 2: 将探索阶段模型链路改为三次调用**

把 `turn_engine` 主链路改为：

- `intent_understanding`
- `decision_state_delta`
- 系统应用决策增量
- `next_interaction_planning`
- 系统渲染 `decision_state_document`

- [ ] **Step 3: 用系统渲染替换探索阶段 write / review**

实现：

- 结构化状态 A4 文档渲染函数
- 会话状态补丁更新
- provider log 只记录真实模型调用节点

- [ ] **Step 4: 保留正式落稿基础状态而不硬做完整成稿器**

先落：

- `draft_entry_confirmation`
- `draft_generation`
- `draft_review`
- `draft_snapshot`

但本轮不把正式需求规格说明完整生成器强塞进探索闭环。

### Task 4: 前端失败测试

**Files:**
- Modify: `apps/web/src/test/RequirementAnalysisLabPage.test.tsx`
- Modify: `apps/web/src/test/requirementAnalysisLabViewModel.test.tsx`

- [ ] **Step 1: 为结构化状态 A4 页和会话阶段展示写失败测试**

新增测试覆盖：

- 会话摘要区域出现“结构化状态”页签
- 默认可看到结构化状态 A4 文档内容
- 页面显示当前会话阶段标识

- [ ] **Step 2: 为调用日志页写失败测试**

新增测试覆盖：

- 探索阶段只展示 3 条 provider 调用日志
- “输出格式要求”等中文分组名称仍然正常显示

### Task 5: 前端实现结构化状态页与阶段投影

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/pages/RequirementAnalysisLabPage.tsx`
- Modify: `apps/web/src/pages/RequirementAnalysisLabPage.css`

- [ ] **Step 1: 扩展前端 API 类型**

增加：

- `session_phase`
- `decision_state`
- `decision_state_document`
- `draft_snapshot`

- [ ] **Step 2: 增加结构化状态 A4 页签**

在会话摘要 / 过程产物区域加入：

- 结构化状态（A4）
- 临时正文（A4）
- 完成度树
- 沟通路径

- [ ] **Step 3: 增加会话阶段标识与确认态展示**

在页面中展示当前阶段：

- 探索与收束阶段
- 落稿确认阶段
- 落稿与成稿阶段
- 成稿审阅阶段

### Task 6: 验证

**Files:**
- No file changes required

- [ ] **Step 1: 运行后端测试**

Run: `pytest apps/api/tests/test_requirement_analysis_api.py apps/api/tests/test_requirement_analysis_modules.py apps/api/tests/test_requirement_analysis_session_service.py -q`

- [ ] **Step 2: 运行前端测试**

Run: `npm test -- --run apps/web/src/test/RequirementAnalysisLabPage.test.tsx apps/web/src/test/requirementAnalysisLabViewModel.test.tsx`

- [ ] **Step 3: 启动前后端并做一次手工验证**

Run backend: `uvicorn app.main:app --reload --port 8000`

Run frontend: `npm run dev -- --host 0.0.0.0 --port 4173`

验证：

- 结构化状态 A4 页可见
- 会话阶段标识可见
- 一轮探索只产生 3 条 provider 调用日志
- 临时正文与完成度树仍能正常展示
