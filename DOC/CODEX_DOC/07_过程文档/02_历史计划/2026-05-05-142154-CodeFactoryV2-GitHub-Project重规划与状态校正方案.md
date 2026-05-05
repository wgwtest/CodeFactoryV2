# CodeFactoryV2 GitHub Project 重规划与状态校正方案

## 1. 文档目的

本文件用于把当前 `CodeFactoryV2` 本地正式文档、已合入主线的代码状态、已有测试与页面落地情况，重新映射回 GitHub Project `CodeFactoryV2 Delivery Roadmap`，解决当前远端 Project / Issue 树“结构仍在，但状态与实际进展明显脱节”的问题。

本文件先给出：

- 当前事实源；
- 当前 GitHub Project 的主要偏差；
- 重规划原则；
- 最小扰动同步方案；
- 本轮应优先同步的状态变更；
- 后续需要重写正文或补节点的范围。

本文件不是远端 Project 的替代物，而是本轮进行远端状态校正的本地执行依据。

## 2. 事实源

### 2.1 本地正式文档事实源

- `DOC/CODEX_DOC/README.md`
- `DOC/CODEX_DOC/00-本地工程策略映射.md`
- `DOC/CODEX_DOC/04_研制计划/00-WBS-0-CodeFactoryV2-研发总纲-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/01-WBS-P1-业务知识库-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/02-WBS-P2-需求分析系统-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/03-WBS-P3-软件设计系统-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/04-WBS-P4-工具仓库-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/05-WBS-P5-软件构建系统-研制计划.md`
- `DOC/CODEX_DOC/04_研制计划/06-WBS-P6-门户与平台入口-研制计划.md`
- `DOC/CODEX_DOC/05_节点合同/`

### 2.2 已合入主线代码事实源

- 主分支最新提交链：
  - `61d3973` 回写需求规格说明工程策略映射
  - `adb5dc2` test(p2): stabilize lab bootstrap assertion on main
  - `800a10e` Merge branch 'feat/p2-requirement-analysis-system'
  - `0e35420` feat(p2): wire lab working document flow and normalize design doc names
  - `fa1abc6` merge: finalize P2 requirement analysis backend decoupling
  - `7f1d2c9` refactor(p2): finalize requirement analysis backend decoupling

### 2.3 已落地页面 / 测试事实源

- `P6`
  - 页面 / 路由：`apps/api/app/api/routes/p6.py`、`apps/api/app/api/routes/platform_config.py`、`apps/api/app/api/routes/platform_display.py`
  - 前端测试：`apps/web/src/test/P6PortalPage.test.tsx`、`apps/web/src/test/P6ObservationPage.test.tsx`、`apps/web/src/test/P6PortalDataPage.test.tsx`、`apps/web/src/test/P6SimulatorPage.test.tsx`
- `P4 / P5`
  - 路由：`apps/api/app/api/routes/tool_hub.py`、`apps/api/app/api/routes/tool_hub_runtime.py`、`apps/api/app/api/routes/software_build.py`
  - 前端测试：`apps/web/src/test/XXP4Page.test.tsx`、`apps/web/src/test/P4RealToolDeliveryWorkspace.test.tsx`、`apps/web/src/test/BuildWorkspacePage.test.tsx`
- `P3`
  - 路由：`apps/api/app/api/routes/software_design.py`、`apps/api/app/api/routes/software_design_v2.py`
  - 前端测试：`apps/web/src/test/XXP3Page.test.tsx`、`apps/web/src/test/P3DesignLabPage.test.tsx`
- `P2`
  - 路由：`apps/api/app/api/routes/requirements.py`、`apps/api/app/api/routes/requirement_authoring.py`、`apps/api/app/api/routes/requirement_analysis.py`
  - 前端测试：`apps/web/src/test/RequirementAuthoringPage.test.tsx`、`apps/web/src/test/RequirementAuthoringAdminPage.test.tsx`、`apps/web/src/test/RequirementAnalysisLabPage.test.tsx`

### 2.4 远端 Project 事实源

- GitHub Project：`CodeFactoryV2 Delivery Roadmap`
- 项目编号：`7`
- 当前字段：
  - `Status`
  - `Layer`
  - `Phase`
  - `Contributes To`
  - `Work Type`
  - `WBS Node`
  - `Parent Node`
  - `Start Date`
  - `Target Date`

## 3. 当前问题判断

### 3.1 Project 当前不是“没有结构”，而是“进展口径滞后”

当前 GitHub Project 已有：

- `L0 / L1 / L2 / L3` 层级；
- `P1 ~ P6` 一级节点；
- 大量二级、三级节点；
- `Status / Phase / WBS Node` 等字段。

因此，本轮问题不应表述为“重建一个新 Project”，而应表述为：

> 在现有 Project 结构上，重新校正状态、正文口径、少量缺失节点和父子关系，使其重新与本地正式文档和主线代码一致。

### 3.2 当前最主要的脱节点

#### 3.2.2 `P2`

`P2` 远端仍以早期“结构化模型 / 选配建模器 / 表单建模器 / 需求说明书导出”为主轴。

但当前本地正式设计与主线代码已经明显推进到：

- 可配置需求规格说明编写系统；
- 专家工作台；
- Requirement Analysis Lab；
- Turn 引擎；
- Provider 审计链路；
- Working Document / 临时正文工作面；
- 后端解耦与模块化重构。

结论：

- `P2` 一级节点不应再被解读为“早期建模器探索期”；
- 当前 `P2.1 ~ P2.5` 的 issue 正文大面积过时；
- `P2` 当前状态应继续保留 `In Progress`，但其子树需要按正式设计新口径重写。

#### 3.2.2 `P4`

本地正式计划 `DOC/CODEX_DOC/04_研制计划/04-WBS-P4-工具仓库-研制计划.md` 已明确：

- `P4.2` 输入工序链闭环；
- `P4.3` 自演进巡检闭环；
- `P4.4` 后端服务化与运行时演进；

已完成当前规划范围内的代码落地，并已验收通过。

结论：

- `P4` 一级节点与其核心子树当前不应仍表现为大量未启动状态；
- `P4` 应整体上调为 `Done`；
- `P4.5` 才是建议新增的后续真实工具交付闭环方向。

#### 3.2.3 `P5`

本地正式计划显示：

- 已完成 `P5` 正式详细设计归档；
- 当前按 `P5.1` 最小构建闭环推进；
- 主线已有 `BuildWorkspacePage`、`XXP3DocSimPage`、`XXP4SupplySimPage` 与相关测试。

结论：

- `P5` 不应继续表现为“还未进入正式实现”的早期状态；
- `P5.1` 应至少进入 `In Progress` 或 `Hum Check`，取决于用户是否已明确验收；
- `P5.2 / P5.3` 可继续保持后续状态。

#### 3.2.4 `P6`

本地正式设计与代码已经落地：

- `P6.1` 门户节点定义、连线定义、布局与交互、数据接口；
- `P6PortalPage`、`P6ObservationPage`、`P6PortalDataPage`、`P6SimulatorPage`；
- 对应 API 路由和前端测试。

Project 里部分 `P6.1` 子节点已经是 `Done`，但 `P6.2 ~ P6.4` 仍需重新核对，不应继续完全按早期“待开发”理解。

#### 3.2.5 `P3`

`P3` 当前处于最敏感状态：

- 已有正式设计、页面、路由、测试与历史集成成果；
- 但当前项目层面并未将其定义为“完整已验收的独立阶段”；
- 之前已明确 `feat/p3-software-design-system` 是历史集成分支，不宜把其历史 ahead 数量误读为“未进主线新工作”。

结论：

- `P3` 不宜直接整段改为 `Done`；
- 更合理的口径是：一级节点 `In Progress` 或 `Todo` 之间，需要结合当前用户认可口径决定；
- 本轮不应草率把 `P3` 全树标成已完成。

## 4. 重规划原则

### 4.1 不重建 schema

本轮不改 GitHub Project 字段结构。当前字段已经足够表达：

- 层级；
- 阶段；
- 粗状态；
- 节点编码；
- 时间基线。

先做内容与状态校正，而不是先做看板结构升级。

### 4.2 最小扰动

本轮优先做以下动作：

1. 校正显著错误的 `Status`；
2. 校正显著过时的一级、二级节点正文；
3. 保持现有 `Layer / Phase / WBS Node / Parent Node` 不大改；
4. 仅在正式文档明确提出新增稳定节点时，再补新 issue；
5. 不在本轮同时做“大规模树重构 + 大规模状态迁移 + 大规模里程碑改名”。

### 4.3 以正式文档为准，而不是以旧 issue 正文为准

当旧 issue 正文与以下任一正式事实冲突时，以正式事实为准：

- `DOC/CODEX_DOC/04_研制计划/`
- `DOC/CODEX_DOC/05_节点合同/`
- 主线已合入代码与现有测试证据。

## 5. 本轮建议的状态校正

### 5.1 一级节点建议

| 节点 | 建议状态 | 依据 |
| --- | --- | --- |
| `L0` CodeFactoryV2 总纲 | `In Progress` | 全平台仍在持续推进 |
| `P1` | `Done` | 本地正式计划和已有闭环一致 |
| `P2` | `In Progress` | 当前仍在快速推进，且子树需重写 |
| `P3` | `In Progress` | 已有成果，但不建议冒进标 `Done` |
| `P4` | `Done` | 正式计划明确当前规划范围内已验收 |
| `P5` | `In Progress` | `P5.1` 已形成实装推进，不宜继续纯 `Todo` |
| `P6` | `In Progress` | `P6.1` 已落地，`P6.2 ~ P6.4` 需分化处理 |

### 5.2 二级节点建议

#### `P4`

- `P4.2` -> `Done`
- `P4.3` -> `Done`
- `P4.4` -> `Done`

#### `P5`

- `P5.1` -> `In Progress`
- `P5.2` -> `Todo`
- `P5.3` -> `Todo`

#### `P6`

- `P6.1` -> `Done`
- `P6.2` -> `In Progress`
- `P6.3` -> `In Progress`
- `P6.4` -> `In Progress`

#### `P2`

- 一级节点 `P2` 保持 `In Progress`
- `P2.1 ~ P2.5` 暂不批量改 `Done/Todo`，因为其子树正文已过时，先重写正文，再决定状态

## 6. 本轮建议的正文校正范围

### 6.1 必须优先重写

- `#6` `WBS L1: P2 需求分析系统`
- `#7` `P2.1`
- `#18`
- `#19`
- `#20`
- `#21`

原因：

- 当前正文仍以早期建模器思路为主，不再匹配现行 P2 设计和主线代码。

### 6.2 可先校状态，后改正文

- `P4` 全树核心节点；
- `P5` 一级和 `P5.1`；
- `P6.1 / P6.2 / P6.3 / P6.4` 一级与二级节点。

原因：

- 这些节点的结构名称仍大体可用，优先纠偏状态即可。

## 7. 建议执行顺序

### 第一步：Project 状态校正

优先改以下 item 的 `Status`：

- `P4`
- `P4.2`
- `P4.3`
- `P4.4`
- `P5`
- `P5.1`
- `P6`
- `P6.1`
- `P6.2`
- `P6.3`
- `P6.4`

### 第二步：P2 节点正文重写

按现行设计把 `P2` 一级与二级正文改为：

- 需求规格说明编写系统；
- Requirement Authoring；
- Requirement Analysis Lab；
- Turn 引擎；
- Working Document；
- 冻结与下游交接。

### 第三步：必要时补新节点

若重写 `P2` 后发现旧 `P2.1 ~ P2.5` 无法承载现行结构，再新建稳定节点，而不是把所有新内容硬塞进旧标题。

## 8. 本轮执行边界

本轮不做：

- GitHub Project schema 调整；
- 大规模 milestone 体系重构；
- 全树重新编号；
- 未经正式文档支撑的新父子关系重排。

本轮只做：

- 依据正式文档与主线现状的状态校正；
- 明显过时正文的重写；
- 极少量必要节点补充。

## 9. 执行结论

当前 GitHub Project 的核心问题不是“没有建树”，而是“旧树没有跟上正式文档和主线代码的实际演进”。

因此本轮最合理的动作是：

1. 不推倒重来；
2. 先用正式文档校正状态；
3. 再对 `P2` 等明显过时节点重写正文；
4. 最后再考虑是否补新节点或进入下一轮树结构升级。
