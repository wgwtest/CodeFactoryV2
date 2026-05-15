# P-BasePlatform worktree 启动指南

> 适用目录：`.worktrees/p-base-platform`  
> 对应分支：`feat/p-base-platform`  
> 默认角色：平台基础能力实现分支；首版聚焦 `P2 -> P3` 平台交换层，不归属单一 P 阶段业务分支。

## 1. 分支定位

`P-BasePlatform` 是 `P1-P6` 之外的跨阶段平台基础能力分支。它不负责生成需求、生成设计、生产工具或构建软件，而是为各阶段之间的正式成果物流转提供统一底座。

首版目标只打通 `P2 -> P3`：

```text
P2 发布冻结需规包
  -> 平台交换层登记 ArtifactEnvelope
  -> P3 查询可消费 RequirementSpecPackage
  -> P3 消费时登记 ArtifactConsumption
  -> P3 创建 P3DesignInputPackage / P3DesignLabSession
```

该分支的长期方向是沉淀跨阶段通用能力：成果物登记、版本治理、payload hash、来源追溯、消费记录、幂等控制、只读查询和后续事件 outbox。

## 2. 必读事实源

新会话进入本 worktree 后，按以下顺序读取：

1. `CODEX_START_HERE.md`
2. `WORKTREE_GUIDE.md`
3. `DOC/CODEX_DOC/README.md`
4. `DOC/CODEX_DOC/00-本地工程策略映射.md`
5. `DOC/CODEX_DOC/02_设计说明/00_总纲/03-P1-P6数据互联互通与平台交换层设计.md`
6. `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`
7. `DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`
8. `DOC/CODEX_DOC/07_过程文档/02_历史计划/2026-05-14-1709-P-BasePlatform分支开设说明.md`
9. 最近相关测试记录：`DOC/CODEX_DOC/06_测试文档/03_机测记录/`

若 `DOC/CODEX_DOC/` 与 `docs/superpowers/` 表达冲突，以 `DOC/CODEX_DOC/` 为正式事实源。

## 3. 当前基线

本 worktree 从 `main` 的以下基线切出：

```text
32d0e02 完善P2到P3接口设计
```

当前本地分支已有启动说明提交：

```text
3c55320 新增P-BasePlatform分支开设说明
```

远端 GitHub 当前因 HTTPS/TLS 链路问题可能无法推送。推送前先执行：

```bash
git ls-remote origin -h refs/heads/main
```

若仍出现 `gnutls_handshake() failed`，不要反复强推；先处理 GitHub 网络或代理问题。

## 4. 工作边界

### 4.1 默认可以做

- 新增 `platform_exchange` 后端域模型、仓储、服务和 API 路由。
- 新增 `ArtifactEnvelope`、`ArtifactConsumption`、`RequirementSpecPackage` 的最小合同模型。
- 改造 `P2` 发布服务：冻结和创建 `RequirementSpec` 后登记平台成果物。
- 改造 `P3` 输入包服务：优先从平台交换层读取可消费成果物，保留旧扫描路径作为降级兼容。
- 在 `P3` 创建设计会话时登记 `ArtifactConsumption`。
- 补充合同测试和链路测试，证明 `P2 -> 平台交换层 -> P3` 可追溯。
- 同步更新总纲、P2、P3 和测试文档中的接口事实。

### 4.2 默认不应做

- 不重做 `P2` 需规管理 UI。
- 不重做 `P3 Design Lab` 页面布局。
- 不把 `P3Order` 恢复为新版主接口术语。
- 不在首版实现全量 `P3 -> P4`、`P4 -> P5`、`P1 ~ P5 -> P6` 交换层。
- 不引入微服务拆分、多租户权限系统或完整异步事件总线。
- 不直接覆盖 `p2`、`p3`、`p4` 等其他 worktree 的未提交改动。

## 5. 核心对象口径

### 5.1 ArtifactEnvelope

平台成果物信封。首版用于包装 `RequirementSpecPackage`。

最小字段包括：

- `artifact_id`
- `artifact_type`
- `artifact_version`
- `schema_version`
- `producer_stage`
- `producer_ref_id`
- `lifecycle_status`
- `payload_mode`
- `payload_ref`
- `payload_hash`
- `parent_artifact_ids`
- `source_trace`
- `idempotency_key`
- `created_at`
- `frozen_at`
- `published_at`
- `published_by`

### 5.2 ArtifactConsumption

平台消费记录。首版用于记录 `P3` 消费 `P2` 成果物。

最小字段包括：

- `consumption_id`
- `artifact_id`
- `consumer_stage`
- `consumer_ref_id`
- `consumption_mode`
- `accepted_schema_version`
- `result_status`
- `result_message`
- `consumed_at`

### 5.3 RequirementSpecPackage

首版 payload 复用当前 `P2` 冻结包和工作文档事实。

最小字段包括：

- `standard_document`
- `structured_spec`
- `annotations`
- `check_result`
- `knowledge_binding`
- `source_trace`
- `p3_consumable`

## 6. 主要代码入口

后端预计新增或重点修改：

- `apps/api/app/platform_exchange/`
- `apps/api/app/api/routes/platform_exchange.py`
- `apps/api/app/main.py`
- `apps/api/app/requirement_spec_work_items/service.py`
- `apps/api/app/software_design_v2/service.py`
- `apps/api/tests/test_platform_exchange_p2_p3_api.py`
- `apps/api/tests/test_software_design_v2_api.py`
- `apps/api/tests/test_requirement_spec_work_items_api.py`

前端原则上不应大改。若必须补充类型或调用封装，优先关注：

- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/softwareDesignV2.ts`
- `apps/web/src/pages/P3DesignLabPage.tsx`
- `apps/web/src/pages/RequirementAnalysisLabPage.tsx`

## 7. 首版 API 边界

建议 API 族：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/platform-exchange/artifacts` | 查询可消费成果物 |
| `GET` | `/api/platform-exchange/artifacts/{artifact_id}` | 获取成果物详情 |
| `POST` | `/api/platform-exchange/artifacts` | 登记成果物，首版可仅由 P2 发布服务内部调用 |
| `POST` | `/api/platform-exchange/artifacts/{artifact_id}/consume` | 登记 P3 消费 |
| `GET` | `/api/platform-exchange/consumptions` | 查询消费记录 |

`P2` 对外仍保留：

```text
POST /api/requirement-analysis/spec-items/{id}/publish
```

`P3` 对外仍保留：

```text
GET /api/software-design-v2/input-packages
POST /api/software-design-v2/sessions
```

首版目标是保持页面兼容，同时把输入来源逐步切换到平台交换层。

## 8. 本地启动端口

启动命令：

```bash
just api-dev
just web-dev
```

端口读取优先级：

1. 当前目录 `.env.local`；
2. 当前 git 分支在 `config/dev-ports.env` 中登记的端口；
3. 主目录默认端口：API `8020`、Web `5173`。

当前 `P-BasePlatform` 分支登记端口：

- API：`http://127.0.0.1:8080/api`
- Web：`http://127.0.0.1:5191`
- 默认入口：`/portal`

完整端口表见主目录 `CODEX_START_HERE.md` 的“常用启动命令”章节。

## 9. 验证命令

后端最小验证：

```bash
uv run pytest apps/api/tests/test_platform_exchange_p2_p3_api.py -q
uv run pytest apps/api/tests/test_requirement_spec_work_items_api.py apps/api/tests/test_software_design_v2_api.py -q
```

前端回归按改动范围选择：

```bash
corepack pnpm --dir apps/web exec vitest run src/test/RequirementAnalysisLabPage.test.tsx src/test/P3DesignLabPage.test.tsx
```

若只改后端平台交换层，前端测试不是每次必跑；但如果改了 `apps/web/src/lib/api.ts`、P2 或 P3 页面，必须跑对应前端测试。

## 10. 验收标准

首版完成必须满足：

1. `P2` 发布一条完整需规后生成 `ArtifactEnvelope<RequirementSpecPackage>`。
2. 成果物包含 `published_at`、`published_by`、`frozen_at`、`payload_hash`、`source_trace`。
3. `P3` 能通过平台交换层查询到该成果物，并转换为 `P3DesignInputPackage`。
4. `P3` 基于该输入包创建设计会话后生成 `ArtifactConsumption`。
5. 再次发布同一版本不会生成不可区分的重复成果物，具备幂等键或版本区分。
6. 当前 `/api/software-design-v2/input-packages` 仍可被 `/p3-design-lab` 使用。
7. 现有 P2 需规管理测试和 P3 Design Lab 测试不回退。

## 11. 与主线同步规则

- 工作前执行：`git status --short --branch`、`git log --oneline --decorate -n 10`。
- 若远端恢复可达，再执行 `git fetch origin`。
- 合并 `main` 前，先确认本 worktree 是否有未提交改动。
- 正式启动服务、用户验收、主线提交和推送默认回到仓库主目录执行。
- 将本分支成果合入主线前，必须说明它是否改动了 `P2`、`P3` 的业务接口，以及是否影响现有页面。

## 12. 交接输出格式

每轮重要工作后，建议补充交接记录，至少写清：

1. 本轮改了哪些平台交换对象；
2. 是否改动 `P2` 发布服务；
3. 是否改动 `P3` 输入包服务；
4. 新增或修改了哪些 API；
5. 跑过哪些测试，结果是什么；
6. 还剩哪些未打通的真实链路。
