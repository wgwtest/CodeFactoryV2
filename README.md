# CodeFactoryV2

`CodeFactoryV2` 是一个知识驱动的软件工厂原型系统：以业务知识库为基础，逐步把“文档接入 → 知识治理 → 需求分析 → 软件设计 → 工具供给 → 软件构建 → 平台门户观察”串成可验证的工程闭环。

如果你第一次接触本项目，按本文档从上到下执行即可启动、访问主要页面、找到对应代码和验证命令。

> 给 Codex 或其他开发代理的新会话入口：先读 [`CODEX_START_HERE.md`](CODEX_START_HERE.md)，再读本 README。

## 1. 当前系统包含什么

| 节点 | 名称 | 当前定位 | 典型入口 |
| --- | --- | --- | --- |
| `P1` | 业务知识库 | 文档接入、解析、知识抽取、治理发布、图谱/流程投影 | `/archives`、`/documents`、`/documents/intake`、`/governance`、`/graph` |
| `P2` | 需求分析系统 | 需求规格编写、建模引导、XG 需求分析实验与 Provider 审计 | `/requirements`、`/modeling`、`/requirement-authoring`、`/p2-requirement-analysis-lab` |
| `P3` | 软件设计系统 | 软件设计驾驶舱、设计模板、冻结设计说明和设计包 | `/xx-p3`、`/p3-design-lab`、`/xx-p3-doc-sim` |
| `P4` | 工具仓库 | 工具需求、工具注册、工具供给、真实工具交付验证 | `/xx-p4`、`/xx-p4-supply-sim` |
| `P5` | 软件构建系统 | 绑定 P3 设计输入与 P4 工具供给，形成构建工作台 | `/build`、`/xx-p5-sim` |
| `P6` | 门户与平台入口 | 平台首屏、跨阶段观察、数据视图、模拟器与展示语言 | `/portal`、`/observation`、`/portal-data`、`/xx-p6-sim` |

系统当前仍是研发型原型，很多跨系统链路使用模拟数据、冻结样例或本地运行态数据验证。正式设计文档位于 `DOC/CODEX_DOC/`。

## 2. 技术栈与目录

| 区域 | 路径 | 说明 |
| --- | --- | --- |
| 后端 | `apps/api/` | FastAPI 服务，入口 `apps/api/app/main.py` |
| 后端测试 | `apps/api/tests/` | Pytest 测试 |
| 前端 | `apps/web/` | React + Vite + Ant Design，入口 `apps/web/src/App.tsx` |
| 前端测试 | `apps/web/src/test/` | Vitest/Testing Library 测试 |
| 正式文档 | `DOC/CODEX_DOC/` | 权威设计、计划、验收、交接文档 |
| 工作文档 | `docs/superpowers/` | 推演、草案、执行计划；正式结论需回写 `DOC/CODEX_DOC/` |
| 平台组织器 | `orchestrators/` | P2 XG Orchestrator 包与测试夹具 |
| 本地运行数据 | `.data/` | 本机运行态数据，默认不提交 |

## 3. 环境准备

本项目默认在 Linux/macOS 类环境中运行。需要先安装：

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+
- Corepack / pnpm
- Docker 与 Docker Compose

首次进入仓库后执行：

```bash
cp .env.example .env
docker compose up -d
uv sync
corepack pnpm install
```

如果本机已经有 `.env.local`，启动脚本会优先读取其中的端口覆盖项。

## 4. 启动系统

推荐使用仓库内脚本启动，避免端口和代理配置不一致。

### 4.1 启动依赖服务

```bash
docker compose up -d
```

会启动：

- PostgreSQL：`localhost:5432`
- MinIO API：`localhost:9000`
- MinIO Console：`http://localhost:9001`

### 4.2 启动后端

```bash
just api-dev
```

等价脚本：`scripts/start_api_dev.sh`。

默认地址：

- API 根：`http://127.0.0.1:8020/api`
- 健康检查：`http://127.0.0.1:8020/api/health`

### 4.3 启动前端

另开一个终端：

```bash
just web-dev
```

默认地址：

- Web：`http://127.0.0.1:5173`

前端通过 `VITE_API_PROXY_TARGET` 代理到后端，默认是 `http://127.0.0.1:8020`。

## 5. 快速访问入口

启动前后端后，打开 `http://127.0.0.1:5173`。

### 5.1 主导航内页面

| URL | 用途 |
| --- | --- |
| `/archives` | 管理知识库 |
| `/documents` | 查看和管理知识库文档 |
| `/documents/intake` | 文档接入、解析和验证 |
| `/governance` | 知识审核与发布 |
| `/graph` | 知识图谱浏览 |
| `/requirement-authoring/admin` | P2 需求编写配置台 |
| `/requirements` | 需求规格工作区 |
| `/modeling` | 应用建模引导 |

### 5.2 独立实验/子系统页面

| URL | 用途 |
| --- | --- |
| `/xx-p1-sim` | P1 上游知识服务模拟入口 |
| `/requirement-authoring` | P2 专家需求编写工作台 |
| `/p2-requirement-analysis-lab` | P2 XG 需求分析实验室 |
| `/xx-p2-sim` | P2 轻量需求模拟输出 |
| `/xx-p3` | P3 软件设计驾驶舱 |
| `/p3-design-lab` | P3 Design Lab |
| `/xx-p3-sim` | P3 到 P4 模拟链路 |
| `/xx-p3-doc-sim` | P3 冻结设计说明模拟输出 |
| `/xx-p4` | P4 工具仓库 |
| `/xx-p4-supply-sim` | P4 工具供给结果模拟输出 |
| `/build` | P5 软件构建工作台 |
| `/xx-p5-sim` | P5 模拟入口 |
| `/portal` | P6 门户首屏 |
| `/observation` | P6 跨阶段观察页 |
| `/portal-data` | P6 门户数据视图 |
| `/xx-p6-sim` | P6 模拟器 |

## 6. 常用验证命令

后端全量测试：

```bash
uv run pytest apps/api/tests -q
```

前端全量测试：

```bash
corepack pnpm --dir apps/web test
```

常用快速回归：

```bash
uv run pytest apps/api/tests/test_requirement_analysis_api.py apps/api/tests/test_requirement_analysis_modules.py apps/api/tests/test_orchestrator_runtime.py -q
corepack pnpm --dir apps/web test -- --run src/test/RequirementAnalysisLabPage.test.tsx
```

P6 快速回归：

```bash
uv run pytest apps/api/tests/test_p6_api.py -q
corepack pnpm --dir apps/web exec vitest run \
  src/test/P6PortalPage.test.tsx \
  src/test/P6ObservationPage.test.tsx \
  src/test/P6PortalDataPage.test.tsx \
  src/test/P6SimulatorPage.test.tsx \
  src/test/p6PortalGeometry.test.ts
```

代码提交前至少执行与改动相关的定向测试，并执行：

```bash
git diff --check
```

## 7. API 与主要代码入口

后端 API 路由注册在 `apps/api/app/main.py`。主要路由模块：

| 能力 | 路由代码 |
| --- | --- |
| 健康检查 | `apps/api/app/api/routes/health.py` |
| 知识库 | `apps/api/app/api/routes/archives.py` |
| 文档 | `apps/api/app/api/routes/documents.py` |
| 治理发布 | `apps/api/app/api/routes/governance.py` |
| 知识查询 | `apps/api/app/api/routes/knowledge.py` |
| 需求规格 | `apps/api/app/api/routes/requirements.py` |
| P2 需求编写 | `apps/api/app/api/routes/requirement_authoring.py` |
| P2 需求分析实验 | `apps/api/app/api/routes/requirement_analysis.py` |
| 应用建模 | `apps/api/app/api/routes/modeling.py` |
| P3 软件设计 | `apps/api/app/api/routes/software_design.py`、`apps/api/app/api/routes/software_design_v2.py` |
| P4 工具仓库 | `apps/api/app/api/routes/tool_hub.py` |
| P5 软件构建 | `apps/api/app/api/routes/software_build.py` |
| P6 门户/观察 | `apps/api/app/api/routes/p6.py`、`apps/api/app/api/routes/platform_config.py`、`apps/api/app/api/routes/platform_display.py` |

前端路由集中在 `apps/web/src/App.tsx`。页面组件集中在 `apps/web/src/pages/`。

## 8. 正式文档阅读顺序

如果要理解设计背景，不要只读代码。推荐顺序：

1. `DOC/CODEX_DOC/README.md`
2. `DOC/CODEX_DOC/00-本地工程策略映射.md`
3. `DOC/CODEX_DOC/01_需求分析/00-工程总体分析.md`
4. `DOC/CODEX_DOC/02_设计说明/00_总纲/00-软件工厂平台总体设计.md`
5. `DOC/CODEX_DOC/02_设计说明/00_总纲/03-P1-P6数据互联互通与平台交换层设计.md`
6. 按任务读取对应阶段设计：
   - `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`
   - `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`
   - `DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`
   - `DOC/CODEX_DOC/02_设计说明/P4_工具仓库/P4-工具仓库设计.md`
   - `DOC/CODEX_DOC/02_设计说明/P5_软件构建系统/P5-软件构建系统设计.md`
   - `DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6-门户与平台入口设计.md`

更完整的文档索引见 `DOC/CODEX_DOC/README.md`。

## 9. 开发与协作规则

- 默认在仓库根目录开发、启动、验证，不把 `.worktrees/*` 当作正式运行现场。
- `.worktrees/` 是历史和受控并行开发目录，不要删除；合并前必须逐一检查差异和提交状态。
- `.data/` 是本地运行态数据，默认不提交。
- 提交 summary 使用中文。
- 推荐 Git 作者：`wgw <hugowangguowei@hotmail.com>`。
- 合并外部分支前先执行 `git fetch origin`、`git status --short --branch`，不要在脏工作区盲目 merge。
- 提交前必须有新鲜验证证据，不能用“应该可以”替代测试输出。

## 10. 常见问题

### 10.1 前端打不开或接口 404

先确认后端是否跑在 `8020`：

```bash
curl http://127.0.0.1:8020/api/health
```

再确认前端代理目标：

```bash
cat .env.local 2>/dev/null || cat .env
```

`VITE_API_PROXY_TARGET` 应指向正在运行的后端，例如 `http://127.0.0.1:8020`。

### 10.2 数据库或对象存储连接失败

确认 Docker 服务状态：

```bash
docker compose ps
```

必要时重启：

```bash
docker compose up -d
```

### 10.3 不知道从哪个页面验收 P1-P6

优先看本文第 5 节入口表。正式验收材料见：

- `DOC/CODEX_DOC/06_测试文档/02_验收入口/README.md`
- `DOC/CODEX_DOC/06_测试文档/02_验收入口/00-验收主入口.md`

### 10.4 新 Codex 会话如何快速接手

直接给新会话这段指令：

```text
请先读取 CODEX_START_HERE.md 和 README.md。
先汇报你对当前项目、分支状态、启动方式、P1-P6 入口和文档事实源的理解，不要立刻改代码。
确认无误后，再根据我的任务继续。
```
