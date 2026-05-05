# P2 Lab Working Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 P2 需求分析 Lab 以会话内临时正文作为主证据面，并把完成度树降为辅助对照视图。

**Architecture:** 后端在会话状态中新增 `working_document`，轮次执行链调整为 `write -> apply -> review -> decide`；前端把 `会话摘要 / 过程产物` 改为 Tab 视图，默认显示临时正文。调用日志与当前 Turn 审计同步暴露正文应用与回看对象。

**Tech Stack:** FastAPI, Python service layer, React, Ant Design, Vitest, pytest

---

### Task 1: 并入主设计文档

**Files:**
- Modify: `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`

- [ ] 将临时正文、会话摘要 Tabs、`write -> apply -> review -> decide`、`working_document` / `section_review` / `global_review` 并入 5.7 与 6.6。
- [ ] 自查章节对账，确认前端视图、后端会话、轮次执行、模块子服务四块内容一致。

### Task 2: 后端失败测试

**Files:**
- Modify: `apps/api/tests/test_requirement_analysis_api.py`

- [ ] 为会话 DTO 新增断言：`working_document` 必须存在并带标题与章节列表。
- [ ] 为 Turn DTO 新增断言：`spec_execution.working_document_update`、`post_update_review.section_review`、`post_update_review.global_review` 必须存在。
- [ ] 为 Provider 日志新增断言：`provider_request.prompt_bundle.working_document_json`、`current_section_draft`、`review_goal` 与 `provider_response.review_json` 必须可见。
- [ ] 运行目标 pytest 用例，确认先红。

### Task 3: 前端失败测试

**Files:**
- Modify: `apps/web/src/test/RequirementAnalysisLabPage.test.tsx`

- [ ] 为会话页新增断言：`会话摘要 / 过程产物` 默认显示临时正文，不默认显示完成度树。
- [ ] 为摘要区域新增断言：可切到 `需求规格完成度树` 与 `沟通路径`。
- [ ] 为当前 Turn 新增断言：可见临时正文应用结果、章节回看、全局回看。
- [ ] 运行目标 Vitest 用例，确认先红。

### Task 4: 后端实现

**Files:**
- Create: `apps/api/app/requirement_analysis/working_document_service.py`
- Create: `apps/api/app/requirement_analysis/working_document_review_service.py`
- Modify: `apps/api/app/requirement_analysis/session_service.py`
- Modify: `apps/api/app/requirement_analysis/session_snapshot.py`
- Modify: `apps/api/app/requirement_analysis/turn_context_builder.py`
- Modify: `apps/api/app/requirement_analysis/turn_engine.py`
- Modify: `apps/api/app/requirement_analysis/turn_audit_service.py`
- Modify: `apps/api/app/requirement_analysis/spec_tree_service.py`
- Modify: `apps/api/app/requirement_analysis/next_interaction_service.py`
- Modify: `apps/api/app/requirement_analysis/provider_call_log_service.py`
- Modify: `apps/api/app/requirement_analysis/deepseek_client.py`
- Modify: `apps/api/app/requirement_analysis/lab_config_service.py`

- [ ] 初始化会话时创建 `working_document`。
- [ ] 轮次中应用 patch 到临时正文，生成 `working_document_update`。
- [ ] 基于临时正文做 `section_review` / `global_review`，再决定树节点是否关闭或保持 `partial`。
- [ ] 在日志 prompt bundle 中暴露临时正文上下文和 review 目标。
- [ ] 跑后端测试至绿。

### Task 5: 前端实现

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/requirementAnalysisLabViewModel.ts`
- Modify: `apps/web/src/pages/RequirementAnalysisLabPage.tsx`
- Modify: `apps/web/src/pages/RequirementAnalysisLabPage.css`

- [ ] 扩展前端 DTO 类型，接收 `working_document`、`working_document_update`、`section_review`、`global_review`。
- [ ] 把 `SessionSummary` 改成 Tabs，默认切到 `临时正文`。
- [ ] 在 `Current Turn` 中展示 patch、临时正文应用结果、章节回看、全局回看。
- [ ] 保持现有 CLI 交互和 Provider 日志页不倒退。
- [ ] 跑前端测试至绿。

### Task 6: 端到端校验

**Files:**
- No direct file changes

- [ ] 运行后端目标 pytest。
- [ ] 运行前端目标 Vitest。
- [ ] 如有必要启动前后端，手查会话页默认视图、树切换、日志字段与当前 Turn 显示。
