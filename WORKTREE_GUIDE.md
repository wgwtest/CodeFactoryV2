# P1 业务知识库审阅型 worktree 指南

> 适用目录：`.worktrees/p1-knowledge-base-review`
> 对应分支：`feat/p1-knowledge-base-review`
> 默认角色：审阅、建议、验证、风险提示；非 P1 主实现分支。

## 1. 分支定位

P1 对应 `业务知识库`，主要承载文档接入、解析、知识抽取、治理发布、图谱/流程投影等能力。与 P2-P6 多数辅助 worktree 不同，P1 的主要开发工作通常由其他同志主导完成，本 worktree 的默认职责不是持续直接改造主实现，而是：

- 审阅 P1 相关提交、设计文档、接口契约和运行效果；
- 复核 P1 是否符合 CodeFactoryV2 的主线架构、数据互联互通和验收规则；
- 形成审阅意见、修改建议、风险清单、验收反馈和必要的补充文档；
- 在用户明确授权时，才进行小范围修复、文档补充或验证脚本调整；
- 对较大实现变更，优先提出建议和可执行改造路径，不默认代替 P1 主负责人重写实现。

## 2. 工作边界

### 2.1 默认可以做

- 读取和对比 `main`、远端 P1 分支、P1 相关提交的差异；
- 运行 P1 后端、前端和专项测试，记录可复现结果；
- 检查知识库列表、文档接入、抽取质量、治理发布、图谱展示等关键路径；
- 补充审阅记录、验收意见、风险说明和交接文档；
- 对明显低风险的问题进行最小修复，例如文档路径、测试说明、入口说明、轻微配置问题。

### 2.2 默认不应做

- 未经用户确认，大规模重构 P1 主实现；
- 把 P1 主负责人的实现路线替换成本 worktree 的另一套实现；
- 在未检查远端和主线状态前直接 merge、rebase 或 force push；
- 用本 worktree 的过程性结论替代正式设计文档或主线验收事实；
- 将 `.worktrees/*` 当作正式运行、正式验收或正式交付目录。

## 3. 必读事实源

新会话进入本 worktree 后，建议按以下顺序读取：

1. `CODEX_START_HERE.md`
2. `README.md`
3. `DOC/CODEX_DOC/00-本地工程策略映射.md`
4. `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`
5. `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库重构设计.md`
6. `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-知识质量与图谱质量保障设计.md`
7. `DOC/CODEX_DOC/05_节点合同/01-P1-业务知识库-节点合同.md`
8. `docs/superpowers/specs/2026-05-11-p1-knowledge-quality-improvement-handoff.md`

若 `DOC/CODEX_DOC/` 与 `docs/superpowers/` 表达冲突，以 `DOC/CODEX_DOC/` 为正式事实源。

## 4. 主要代码入口

后端重点关注：

- `apps/api/app/api/routes/archives.py`
- `apps/api/app/api/routes/documents.py`
- `apps/api/app/api/routes/knowledge.py`
- `apps/api/app/api/routes/p1_refactor.py`
- `apps/api/app/archive_knowledge/`

前端重点关注：

- `apps/web/src/App.tsx`
- `apps/web/src/features/p1/`
- `apps/web/src/features/p1Clean/`
- `apps/web/src/pages/DocumentsPage.tsx`
- `apps/web/src/pages/DocumentIntakePage.tsx`
- `apps/web/src/pages/GovernancePage.tsx`
- `apps/web/src/pages/KnowledgeGraphPage.tsx`

测试重点关注：

- `apps/api/tests/test_archive_*`
- `apps/api/tests/test_document_*`
- `apps/api/tests/test_p1_*`
- `apps/web/src/test/DocumentsPage.test.tsx`
- `apps/web/src/test/p1Clean*.test.*`

## 5. 主要验收入口

常用前端路由：

- `/p1`
- `/p1/archives/:archiveId/*`
- `/archives`
- `/documents`
- `/documents/intake`
- `/governance`
- `/graph`
- `/xx-p1-sim`

P1 验收时应优先覆盖：

- 知识库列表加载和当前知识库切换；
- 文档上传、接入、解析、抽取状态展示；
- 知识单元、证据链、质量状态和失败原因展示；
- 审核、发布、治理规则和质量门禁路径；
- 图谱、流程或关系投影是否能解释来源文档。

## 6. 审阅输出格式

建议审阅结论采用以下结构：

1. `审阅范围`：分支、提交、文件或运行入口；
2. `事实证据`：命令输出、截图、测试结果、接口响应或文档路径；
3. `主要问题`：按阻塞、重要、一般分级；
4. `修改建议`：说明建议谁改、改哪里、为什么；
5. `是否建议合入主线`：明确 `建议合入`、`暂缓合入` 或 `需补证据后再判断`。

## 7. 与主线同步规则

- 工作前执行 `git fetch origin`、`git status --short --branch`、`git log --oneline --decorate -n 10`。
- 若本 worktree 落后 `main`，优先从最新 `main` 同步。
- 若发现 P1 远端有新提交，先审阅差异，再判断是否建议合并。
- 正式启动服务、用户验收、提交和推送默认回到仓库主目录执行。
- 如需把本 worktree 的审阅文档或小修复合入主线，必须先检查主目录是否干净，再以可追溯方式合并。
