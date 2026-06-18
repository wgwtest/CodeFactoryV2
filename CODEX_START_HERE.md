# Codex 新会话启动入口

> 目的：让新的 Codex 会话在较短上下文内理解 `CodeFactoryV2` 的项目边界、事实源、工作规则、P1-P6 子系统和验证入口。新会话优先读本文件，再按下面的读取顺序补充上下文。

## 1. 项目一句话

`CodeFactoryV2` 是一个知识驱动的软件工厂项目：从业务知识库开始，逐步完成需求分析、软件设计、工具供给、软件构建和平台门户观察层。

当前项目按 `P1-P6` 六个一级节点推进：

| 节点 | 名称 | 定位 |
| --- | --- | --- |
| `P1` | 业务知识库 | 文档接入、解析、知识抽取、治理发布、图谱/流程投影 |
| `P2` | 需求分析系统 | 从知识库和用户输入收敛应用需求规格 |
| `P3` | 软件设计系统 | 生成和冻结软件设计说明、模块工单、设计包 |
| `P4` | 工具仓库 | 管理工具需求、工具供给、真实工具运行与交付 |
| `P5` | 软件构建系统 | 绑定 P3/P4 输入，形成最小构建闭环、批阅和回流 |
| `P6` | 门户与平台入口 | 平台首屏、跨阶段状态观察、展示语言和前端实验场 |

## 2. 新会话必须先做的事

在任何编辑、启动服务、合并或提交前，先执行以下顺序：

1. 读本文件：`CODEX_START_HERE.md`
2. 看工作区状态：`git status --short --branch`
3. 确认当前目录是主目录还是 worktree：`git branch --show-current`
4. 读正式文档根入口：`DOC/CODEX_DOC/README.md`
5. 读工程策略映射：`DOC/CODEX_DOC/00-本地工程策略映射.md`
6. 读总体分析：`DOC/CODEX_DOC/01_需求分析/00-工程总体分析.md`
7. 按当前任务读取对应节点设计：
   - 跨系统数据互通、共性后台、部署形态：`DOC/CODEX_DOC/02_设计说明/00_总纲/03-P1-P6数据互联互通与平台交换层设计.md`
   - `P1`：`DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`
   - `P2`：`DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`
   - `P3`：`DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`
   - `P4`：`DOC/CODEX_DOC/02_设计说明/P4_工具仓库/P4-工具仓库设计.md`
   - `P5`：`DOC/CODEX_DOC/02_设计说明/P5_软件构建系统/P5-软件构建系统设计.md`
   - `P6`：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6-门户与平台入口设计.md`
8. 读最近交接记录：`DOC/CODEX_DOC/07_过程文档/01_会话交接/`
9. 读最近机测记录：`DOC/CODEX_DOC/06_测试文档/03_机测记录/`

不要一上来全仓扫描。先用上面的文件建立上下文，再按任务补读代码和测试。

## 3. 事实源和目录规则

### 3.1 主事实源

- 正式本地文档根：`DOC/CODEX_DOC/`
- 工作推演文档层：`docs/superpowers/`
- 远端仓库：`origin`，当前是 `https://github.com/wgwtest/CodeFactoryV2.git`
- 正式交付分支：`main`
- 正式交付目录：仓库主目录，不是 `.worktrees/*`

若 `DOC/CODEX_DOC/` 与 `docs/superpowers/` 表达冲突，以 `DOC/CODEX_DOC/` 为准。

### 3.2 worktree 规则

`.worktrees/` 是辅助隔离目录，不是正式交付根。不要删除 `.worktrees/`。

常见对应关系：

| worktree | 分支 | 用途 |
| --- | --- | --- |
| `.worktrees/p1-knowledge-base-review` | `feat/p1-knowledge-base-review` | P1 业务知识库审阅与建议型辅助分支 |
| `.worktrees/p-base-platform` | `feat/p-base-platform` | 跨阶段平台基础能力辅助分支 |
| `.worktrees/p-test` | `feat/p-test` | 跨阶段测试验证辅助分支 |
| `.worktrees/p2-requirement-analysis-system` | `feat/p2-requirement-analysis-system` | P2 需求分析系统辅助分支 |
| `.worktrees/p3-software-design-system` | `feat/p3-software-design-system` | P3 软件设计系统历史集成分支工作树 |
| `.worktrees/p3-requirement-to-design-conversion` | `feat/p3-requirement-to-design-conversion` | P3 需规文档到软设文档转换专项分支 |
| `.worktrees/p4-tool-hub` | `feat/p4-tool-hub` | P4 工具仓库辅助分支 |
| `.worktrees/p5-software-construction-system` | `feat/p5-software-construction-system` | P5 软件构建系统辅助分支 |
| `.worktrees/p6-portal-platform-entry` | `feat/p6-portal-platform-entry` | P6 门户与平台入口辅助分支 |

执行规则：

- 启动服务、正式验收、正式提交和推送默认在主目录执行。
- 在 worktree 中工作前，先确认该分支是否包含最新 `main`。
- 如果 worktree 有独立提交，合入主线前先检查差异，不要盲目 merge。
- 如果 worktree 只有旧基线，优先同步到最新 `main`。
- `.data/` 是本地运行数据，默认不提交，除非用户明确要求。

P1 特别规则：

- `.worktrees/p1-knowledge-base-review` 是审阅与建议型 worktree，不是 P1 主实现分支。
- P1 主要工作通常由其他同志主导完成；本分支默认承担差异审阅、运行验证、风险提示、验收反馈和建议文档整理。
- 除非用户明确授权，本分支不主动大规模修改 P1 主实现；较大问题优先形成审阅意见和改造建议。
- 新会话进入 P1 worktree 时，先读该目录下的 `WORKTREE_GUIDE.md`。

### 3.3 当前 P3 分支特别说明

`feat/p3-software-design-system` 当前保留为**历史集成分支**，不是后续 `P3` 的默认主开发分支。

原因：

- 该分支历史上承载过 `P3`、`P4`、`P5`、`P6` 以及部分 `P2` / 文档治理工作的阶段性集成；
- 其大量提交已经通过历史 merge 进入 `main`；
- 继续把该分支当作“当前活跃 P3 功能分支”容易误导后续会话，增加误合并风险。

执行规则：

- 该分支可以保留并推送远端，用于保全历史工作；
- 不应因为该分支存在，就再次把整条历史重新 merge 到 `main`；
- 若后续继续推进 `P3` 新工作，默认应从最新 `main` 新建干净分支，例如新的 `feat/p3-*` 分支；
- 新会话若看到该分支相对远端 ahead 很多，不应直接解读为“有大量未进主线的新功能”，应先检查它相对 `main` 是否还有独有提交。

当前已开设新的 `P3` 专项分支：

- worktree：`.worktrees/p3-requirement-to-design-conversion`
- 分支：`feat/p3-requirement-to-design-conversion`
- 用途：专门推进“需求规格说明文档 -> 软件设计说明文档”的转换能力，包括输入包解析、章节映射、设计草稿生成、人工校核和冻结输出。
- 默认入口：`/p3-design-lab`
- 新会话进入该 worktree 时，先读该目录下的 `WORKTREE_GUIDE.md`。

## 4. 代码结构速览

### 4.1 后端

后端位于 `apps/api/`，入口为：

- `apps/api/app/main.py`
- 路由目录：`apps/api/app/api/routes/`
- 核心服务目录：`apps/api/app/`
- 测试目录：`apps/api/tests/`

当前主要 API 路由族：

- `health`
- `archives`
- `documents`
- `governance`
- `knowledge`
- `requirements`
- `modeling`
- `tool_hub`
- `software_design`
- `software_build`
- `p6`
- `platform_config`
- `platform_display`

### 4.2 前端

前端位于 `apps/web/`，入口为：

- `apps/web/src/App.tsx`
- 页面目录：`apps/web/src/pages/`
- 组件目录：`apps/web/src/components/`
- 测试目录：`apps/web/src/test/`

常用页面入口：

| 路径 | 对应能力 |
| --- | --- |
| `/archives` | 知识库管理 |
| `/documents` | 知识库文档 |
| `/documents/intake` | 文档接入解析验证 |
| `/governance` | 知识审核发布 |
| `/graph` | 知识图谱 |
| `/requirements` | 需求规格 |
| `/modeling` | 建模引导 |
| `/xx-p2-sim` | P2 轻量需求模拟 |
| `/xx-p3` | P3 软件设计驾驶舱 |
| `/xx-p3-sim` | P3 到 P4 工具包模拟链路 |
| `/xx-p3-doc-sim` | P3 冻结设计说明模拟输出 |
| `/xx-p4` | P4 工具仓库页面 |
| `/xx-p4-supply-sim` | P4 已供给结果模拟输出 |
| `/build` | P5 软件构建工作台 |
| `/portal` | P6 门户投影 |
| `/observation` | P6 观察页 |

## 5. P1-P6 代码和测试入口

| 节点 | 重点代码 | 重点测试 |
| --- | --- | --- |
| `P1` | `apps/api/app/api/routes/archives.py`、`apps/api/app/api/routes/documents.py`、`apps/api/app/api/routes/knowledge.py`、`apps/web/src/pages/DocumentsPage.tsx` | `apps/api/tests/test_archive_*`、`apps/api/tests/test_document_*`、`apps/web/src/test/DocumentsPage.test.tsx` |
| `P2` | `apps/api/app/api/routes/requirements.py`、`apps/api/app/api/routes/modeling.py`、`apps/web/src/pages/RequirementsPage.tsx`、`apps/web/src/pages/XXP2SimPage.tsx` | `apps/api/tests/test_requirement_specs_api.py`、`apps/api/tests/test_application_modeling_api.py`、`apps/web/src/test/XXP2SimPage.test.tsx` |
| `P3` | `apps/api/app/api/routes/software_design.py`、`apps/web/src/pages/XXP3Page.tsx`、`apps/web/src/components/p3/` | `apps/api/tests/test_software_design_api.py`、`apps/web/src/test/P3OrderQueue.test.tsx`、`apps/web/src/test/XXP3Page.test.tsx` |
| `P4` | `apps/api/app/api/routes/tool_hub.py`、`apps/web/src/pages/XXP4Page.tsx` | `apps/api/tests/test_tool_hub_*`、`apps/web/src/test/XXP4Page.test.tsx`、`apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx` |
| `P5` | `apps/api/app/api/routes/software_build.py`、`apps/web/src/pages/BuildWorkspacePage.tsx`、`apps/web/src/pages/XXP3DocSimPage.tsx`、`apps/web/src/pages/XXP4SupplySimPage.tsx` | `apps/api/tests/test_software_build_api.py`、`apps/web/src/test/BuildWorkspacePage.test.tsx`、`apps/web/src/test/XXP3DocSimPage.test.tsx`、`apps/web/src/test/XXP4SupplySimPage.test.tsx` |
| `P6` | `apps/api/app/api/routes/p6.py`、`apps/api/app/api/routes/platform_config.py`、`apps/api/app/api/routes/platform_display.py`、`apps/api/app/p6/`、`apps/web/src/pages/P6PortalPage.tsx`、`apps/web/src/pages/P6ObservationPage.tsx`、`apps/web/src/components/p6/` | `apps/api/tests/test_p6_api.py`、`apps/web/src/test/P6PortalPage.test.tsx`、`apps/web/src/test/P6ObservationPage.test.tsx`、`apps/web/src/test/p6PortalGeometry.test.ts` |

## 6. 常用启动命令

首次或依赖变化后：

```bash
cp .env.example .env
docker compose up -d
uv sync
corepack pnpm install
```

启动后端：

```bash
just api-dev
```

Windows PowerShell 可用：

```powershell
just api-dev-ps
```

启动前端：

```bash
just web-dev
```

Windows PowerShell 可用：

```powershell
just web-dev-ps
```

启动端口读取规则：

1. `just api-dev` 和 `just web-dev` 都会先读取当前目录 `.env.local`。
2. 启动脚本会读取 `config/dev-ports.env` 中可提交的端口和 Dify 非密钥配置。
3. 启动脚本会读取 `C:\Users\wgw\.codefactory\dify.local.env` 中的本机 Dify API Key；也可用 `CODEFACTORY_LOCAL_DIFY_ENV` 覆盖路径。
4. 如果当前目录存在 `.env.local`，它最后加载，可覆盖本 worktree 的本地调试值。
5. 如果分支没有登记端口，才回退到主目录默认值：API `8020`、Web `5173`。

分支端口表：

| 目录 | API | Web | 默认入口 |
| --- | --- | --- | --- |
| 主目录 `main` | `8020` | `5173` | `/documents` |
| `.worktrees/p1-knowledge-base-review` | `8021` | `5171` | `/documents` |
| `.worktrees/p2-requirement-analysis-system` | `8060` | `5183` | `/requirements` |
| `.worktrees/p3-software-design-system` | `8030` | `5174` | `/xx-p3` |
| `.worktrees/p3-requirement-to-design-conversion` | `8031` | `5175` | `/p3-design-lab` |
| `.worktrees/p4-tool-hub` | `8010` | `5180` | `/xx-p4` |
| `.worktrees/p5-software-construction-system` | `8040` | `5181` | `/build` |
| `.worktrees/p6-portal-platform-entry` | `8050` | `5182` | `/portal` |
| `.worktrees/p-test` | `8070` | `5190` | `/portal` |
| `.worktrees/p-base-platform` | `8080` | `5191` | `/portal` |

主目录常用地址：

- Web：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8020/api`
- MinIO API：`localhost:9000`
- MinIO Console：`localhost:9001`
- PostgreSQL：`localhost:5432`

Dify 接入变量：

| 服务 | 非密钥配置位置 | 本机密钥变量 |
| --- | --- | --- |
| P3 需规转软设主转换 | `config/dev-ports.env` | `CODEFACTORY_P3_DIFY_API_KEY` |
| P3 软设局部补丁提案 | `config/dev-ports.env` | `CODEFACTORY_P3_SCOPED_DIFY_API_KEY` |

密钥只放 `C:\Users\wgw\.codefactory\dify.local.env` 或进程环境变量，不提交到仓库。

## 7. 常用验证命令

全量倾向：

```bash
uv run pytest apps/api/tests -q
corepack pnpm --dir apps/web test
```

P6 快速回归：

```bash
uv run pytest apps/api/tests/test_p6_api.py -q
corepack pnpm --dir apps/web exec vitest run \
  src/test/P6PortalPage.test.tsx \
  src/test/P6ObservationPage.test.tsx \
  src/test/p6PortalGeometry.test.ts \
  src/test/AppRoutes.test.tsx
```

P3/P5 快速回归：

```bash
corepack pnpm --dir apps/web exec vitest run \
  src/test/P3OrderQueue.test.tsx \
  src/test/XXP2SimPage.test.tsx \
  src/test/XXP3Page.test.tsx \
  src/test/XXP3DocSimPage.test.tsx \
  src/test/XXP4SupplySimPage.test.tsx
```

## 8. 协作和提交规则

- 用户偏好：提交 summary 使用中文。
- Git 作者：`wgw <hugowangguowei@hotmail.com>`。
- 默认不提交 `.data/`、`__pycache__/`、本地缓存、临时运行产物。
- 不删除 `.worktrees/`。
- 不在未检查远端和工作区状态时合并、rebase、push。
- 合并外部分支前，先判断：
  - 是否包含未提交改动；
  - 是否有未并入主线的有效提交；
  - 是否只是旧基线落后；
  - 是否存在运行数据或无关文件。
- 提交前必须有新鲜验证证据。不能用“应该可以”替代测试输出。

## 9. 文档更新规则

当发生以下事件时，应更新本文件或相关正式入口：

- 新增一级节点、重要子节点、正式页面入口或 API 路由；
- P1-P6 的职责边界改变；
- worktree 策略、分支事实源或交付目录规则改变；
- 常用启动/验证命令改变；
- 新增对 Codex 新会话有必要知道的长期约束。

本文件只记录稳定事实和启动路径，不记录每轮临时细节。临时过程写入：

- 机测记录：`DOC/CODEX_DOC/06_测试文档/03_机测记录/`
- 交接记录：`DOC/CODEX_DOC/07_过程文档/01_会话交接/`

UI / 页面工作特别注意：若已有用户确认的设计稿、原型图、HTML 原型或效果图，必须把它作为实现基线，而不是布局参考。编码前要拆成设计稿到代码转换清单；编码后要用运行态截图对照设计稿，列出并修正偏离，再汇报完成。详细规则见 `DOC/CODEX_DOC/00-本地工程策略映射.md` 的 `3.6 确认设计稿到代码实现规则`。

## 10. 给新 Codex 会话的推荐开场指令

可以直接这样要求新会话：

```text
请先读取 CODEX_START_HERE.md，然后读取其中指定的正式文档入口。
先汇报你对当前项目、当前分支、事实源和工作约束的理解，不要立刻改代码。
确认无误后，再根据我的任务继续。
```
