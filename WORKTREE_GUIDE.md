# P3 需规转软设专项 worktree 启动指南

> 适用目录：`.worktrees/p3-requirement-to-design-conversion`  
> 对应分支：`feat/p3-requirement-to-design-conversion`  
> 默认角色：P3 专项开发分支；专门推进“需求规格说明文档 -> 软件设计说明文档”的转换能力。

## 1. 分支定位

本分支是新的 `P3` 活跃专项分支，从最新 `main` 切出，不沿用 `feat/p3-software-design-system` 的历史集成分支。

目标不是重做整个 P3，而是聚焦一条主链：

```text
P2 冻结需求规格说明
  -> P3 读取需求规格输入包
  -> 识别需求章节、业务对象、流程、功能项、数据与接口、非功能和验收准则
  -> 映射为软件设计说明章节骨架
  -> 生成可审阅的软件设计说明草稿
  -> 人工校核、修订和冻结
  -> 输出 P4/P5 可消费的设计对象或模块工单投影
```

本分支应强调“文档转换质量”和“需求/设计边界清晰”，不得把需求规格说明原文简单改标题伪装成软件设计说明。

## 2. 必读事实源

新会话进入本 worktree 后，按以下顺序读取：

1. `CODEX_START_HERE.md`
2. `WORKTREE_GUIDE.md`
3. `DOC/CODEX_DOC/README.md`
4. `DOC/CODEX_DOC/00-本地工程策略映射.md`
5. `DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`
6. `DOC/CODEX_DOC/05_节点合同/03-P3-软件设计系统-节点合同.md`
7. `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`
8. `DOC/CODEX_DOC/02_设计说明/00_总纲/03-P1-P6数据互联互通与平台交换层设计.md`
9. `DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/01-需求规格说明范本-SX-DataStore.md`
10. `DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/02-软件设计说明范本-SX-DataStore.md`
11. 最近相关测试记录：`DOC/CODEX_DOC/06_测试文档/03_机测记录/`

若 `DOC/CODEX_DOC/` 与 `docs/superpowers/` 表达冲突，以 `DOC/CODEX_DOC/` 为正式事实源。

## 3. 当前基线

本 worktree 从主目录 `main` 的以下提交切出并同步：

```text
905aaf8 新增P3需规转软设专项分支配置
```

当前远端 GitHub 推送可能受网络重置影响。推送前先验证：

```bash
git ls-remote origin -h refs/heads/main
```

如果出现 `Recv failure: Connection reset by peer`，不要反复强推；先处理 GitHub 网络或代理问题。

## 4. 工作边界

### 4.1 默认可以做

- 增强 P3 输入包读取，明确从冻结需规包提取转换所需事实。
- 建立需求章节到软设章节的映射模型。
- 建立设计草稿生成服务，输出结构化软件设计说明草稿。
- 建立转换过程产物，例如章节映射、对象识别、缺口清单、校核结果和人工修订记录。
- 增强 `P3 Design Lab` 中的需规输入、软设草稿、结构化状态和校核视图。
- 使用 `SX-DataStore` 需规/软设范本作为生成验证样例。
- 补充后端转换服务测试、前端视图测试和端到端链路验证。
- 同步更新 P3 设计说明、节点合同、测试文档和交接记录。

### 4.2 默认不应做

- 不继续把 `feat/p3-software-design-system` 当作活跃开发分支。
- 不重做 P2 需求规格编写系统。
- 不改变 P2 发布冻结的正式职责。
- 不把 P3 转换器设计成任意文档改写器。
- 不把需求内容直接平铺成软件设计，不做架构、模块、对象、API、流程和质量门推导。
- 不绕过人工校核直接冻结软件设计说明。
- 不直接修改 P4/P5 主流程，除非为了验证 P3 输出兼容性补最小投影。

## 5. 核心转换口径

### 5.1 输入对象

核心输入应来自冻结后的需求规格说明或平台交换层提供的 `RequirementSpecPackage`。最低应包含：

- 标准需求规格正文。
- 结构化需求对象。
- 功能项清单。
- 业务角色和职责。
- 核心业务流程。
- 数据与接口需求。
- 非功能需求。
- 验收准则。
- 来源追溯和冻结状态。

### 5.2 中间对象

建议建立以下中间对象或等价结构：

- `DesignConversionInputPackage`
- `RequirementSectionMap`
- `BusinessObjectCandidate`
- `FlowToModuleMapping`
- `FunctionToServiceMapping`
- `DataInterfaceToApiMapping`
- `NonFunctionalDesignConstraint`
- `DesignDraftSection`
- `DesignConversionReviewFinding`

### 5.3 输出对象

核心输出应至少包括：

- 软件设计说明草稿正文。
- 结构化设计对象。
- 章节映射追溯。
- 设计缺口清单。
- 人工校核记录。
- 冻结后的软件设计说明版本。
- 面向 P4/P5 的模块工单或设计包投影。

## 6. 软件设计说明目标结构

转换输出的软件设计说明应至少覆盖：

1. 文档目的与设计口径。
2. 系统定位。
3. 业务目标与边界。
4. 总体架构。
5. 前端软件设计。
6. 后端软件设计。
7. 核心对象模型。
8. API 设计。
9. 关键运行流程。
10. 智能能力、模型调用或专项服务设计。
11. 设计约束与质量门。
12. 目标目录结构。
13. 验收口径。
14. 面向平台展示与验证输出接口。
15. 设计结论。

该结构可参考 P3/P2 现有设计说明的组织方式，但内容必须来自输入项目事实，不得复制 P2/P3 平台自身内容。

## 7. 主要代码入口

后端重点关注：

- `apps/api/app/software_design_v2/`
- `apps/api/app/api/routes/software_design_v2.py`
- `apps/api/app/platform_exchange/`
- `apps/api/app/requirement_spec_work_items/`
- `apps/api/tests/test_software_design_v2_api.py`
- `apps/api/tests/test_platform_exchange_p2_p3_api.py`

前端重点关注：

- `apps/web/src/pages/P3DesignLabPage.tsx`
- `apps/web/src/pages/adapters/p3DesignLabWorkbenchAdapter.ts`
- `apps/web/src/pages/adapters/p3DesignMorphAdapter.ts`
- `apps/web/src/components/stageWorkbench/`
- `apps/web/src/test/P3DesignLabPage.test.tsx`
- `apps/web/src/test/P3DesignMorphModel.test.ts`
- `apps/web/src/test/DesignMorphCanvasPlatform.test.tsx`

文档重点关注：

- `DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`
- `DOC/CODEX_DOC/05_节点合同/03-P3-软件设计系统-节点合同.md`
- `DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/`

## 8. 本地启动端口

启动命令：

```bash
just api-dev
just web-dev
```

当前分支登记端口：

- API：`http://127.0.0.1:8031/api`
- Web：`http://127.0.0.1:5175`
- 默认入口：`/p3-design-lab`

完整端口表见主目录 `CODEX_START_HERE.md` 的“分支端口表”。

## 9. 验证命令

后端最小验证：

```bash
uv run pytest apps/api/tests/test_software_design_v2_api.py -q
uv run pytest apps/api/tests/test_platform_exchange_p2_p3_api.py -q
```

前端最小验证：

```bash
corepack pnpm --dir apps/web exec vitest run \
  src/test/P3DesignLabPage.test.tsx \
  src/test/P3DesignMorphModel.test.ts \
  src/test/DesignMorphCanvasPlatform.test.tsx \
  --testTimeout 20000
```

文档校验：

```bash
git diff --check
rg -n "TODO|TBD|待定|空域|态势分析" DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore DOC/CODEX_DOC/02_设计说明/P3_软件设计系统
```

## 10. 验收标准

首轮完成至少满足：

1. 能从一份冻结需规包识别角色、对象、流程、功能、数据接口、非功能和验收准则。
2. 能生成符合目标结构的软件设计说明草稿。
3. 软设草稿包含架构、前端、后端、对象、API、流程和质量门，不只是需求复述。
4. 每个主要设计章节可追溯到需求来源或明确标记为设计推导。
5. 能输出缺口清单，说明哪些需求不足以支撑设计，需要人工补充。
6. 人工确认后才能冻结软件设计说明。
7. 以 `SX-DataStore` 范本作为样例验证时，转换结果与软设范本的结构和核心事实基本对齐。
8. P3 现有关键测试不回退。

## 11. 与主线同步规则

- 工作前执行：`git status --short --branch`、`git log --oneline --decorate -n 10`。
- 若远端恢复可达，再执行 `git fetch origin`。
- 从主线同步时优先使用 `git merge --ff-only main`；如果本分支已有独立提交，则先检查差异再 merge。
- 合入主线前，列出本分支相对 `main` 的独有提交和文件差异。
- 不删除其他 worktree，不覆盖其他分支未提交内容。
