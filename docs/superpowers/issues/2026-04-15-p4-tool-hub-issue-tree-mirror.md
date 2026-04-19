# P4 工具中台本地 Issue 树镜像

> 本地镜像最近已于 2026-04-19 根据当前验收结论完成同步。当前主树以 GitHub Issues 为准，这里保留一份工作树内可直接查阅的镜像与节点说明。

## GitHub Sync

- Root issue: `#12` `WBS L1: P4 工具仓库 / 工具中台`
- 已验收包: `#13` `WBS L2: P4.1 第一批最小闭环`
- 已验收包: `#45` `WBS L2: P4.2 输入工序链闭环探索`
- 已验收包: `#69` `WBS L2: P4.3 自演进巡检闭环`
- 已验收包: `#75` `WBS L2: P4.4 后端服务化与运行时演进`
- 本地新增包: `P4.5` `真实工具落地验证`
- Project: `CodeFactoryV2 Delivery Roadmap` `#7`

> Project `Status` 当前映射口径：issue `当前状态 = 已自测，待人工验收` 时，Project 侧统一标记为 `Hum Check`。
> 2026-04-19 当前轮次已按用户结论整体转为 `已验收 / Done`。

## 节点文档映射

> 从 2026-04-16 起，`P4` 节点默认维护“节点 -> 设计文档 / 执行文档”映射。至少要能回答：该节点由哪份设计文档约束、由哪份执行文档承接。

- `P4`
  - 设计文档：`docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md`
  - 补充设计：`docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md`
  - 补充设计：`docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
  - 补充设计：`docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md`
  - 补充设计：`docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md`
- `P4.1`
  - 设计文档：`docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md`
- `P4.1.6`
  - 设计文档：`docs/superpowers/specs/2026-04-15-p4-tool-hub-unified-data-snapshot-design.md`
  - 执行文档：`docs/superpowers/issues/P4.1.6-tool-hub-unified-data-snapshot-execution.md`
  - 实施计划：`docs/superpowers/plans/2026-04-15-p4-tool-hub-unified-data-snapshot.md`
- `P4.2`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-16-p4-input-chain-closed-loop.md`
- `P4.2.1`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-tool-demand-sheet-lifecycle-design.md`
  - 执行文档：`docs/superpowers/issues/P4.2.1-tool-demand-sheet-lifecycle-execution.md`
  - 上层关联设计：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
- `P4.2.2`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-16-p4-input-chain-closed-loop.md`
- `P4.2.3`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-16-p4-input-chain-closed-loop.md`
- `P4.2.4`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-16-p4-input-chain-closed-loop.md`
- `P4.2.5`
  - 设计文档：`docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-16-p4-input-chain-closed-loop.md`
- `P4.2.6`
  - 设计文档：`docs/superpowers/specs/2026-04-17-p4-simulated-manufacture-executor-design.md`
  - 执行文档：`docs/superpowers/issues/P4.2.6-simulated-manufacture-executor-execution.md`
  - 实施计划：`docs/superpowers/plans/2026-04-17-p4-simulated-manufacture-executor.md`
- `P4.3`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-evolution-inspection-closed-loop.md`
- `P4.3.1`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
- `P4.3.2`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
- `P4.3.3`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-evolution-inspection-closed-loop.md`
- `P4.4`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- `P4.4.1`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- `P4.4.2`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- `P4.4.3`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- `P4.4.4`
  - 设计文档：`docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- `P4.5`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.5.1`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.5.2`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.5.3`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.5.4`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.5.5`
  - 设计文档：`DOC/CODEX_DOC/02_设计说明/06-P4-真实工具落地验证设计.md`
  - 实施计划：`docs/superpowers/plans/2026-04-19-p4-real-tool-delivery-validation.md`
- `P4.1.2` 补充
  - 设计文档：`docs/superpowers/specs/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator.md`
- `P4.2.2` 补充
  - 设计文档：`docs/superpowers/specs/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator-design.md`
  - 实施计划：`docs/superpowers/plans/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator.md`

> 2026-04-18 已完成 `P4.3 / P4.4` 远端同步。当前 GitHub 有效树对应：
> - `#12` `WBS L1: P4 工具仓库 / 工具中台`
> - `#13` `WBS L2: P4.1 第一批最小闭环`
> - `#39 ~ #44` `P4.1.1 ~ P4.1.6`

## WBS Tree

- `#12` `P4` 工具仓库 / 工具中台 `[已验收]`
  - `#13` `P4.1` 第一批最小闭环 `[已验收]`
    - `#39` `P4.1.1` 工具描述模型 `[已验收]`
    - `#40` `P4.1.2` 工具仓库 CRUD `[已验收]`
    - `#41` `P4.1.3` 工具分类与标签体系 `[已验收]`
    - `#42` `P4.1.4` 工具匹配规则 MVP `[已验收]`
    - `#43` `P4.1.5` 工具验证工作台 `[已验收]`
    - `#44` `P4.1.6` 统一数据层与同源快照验证 `[已验收]`
  - `#45` `P4.2` 输入工序链闭环探索 `[已验收]`
    - `#46` `P4.2.1` 协议与对象模型 `[已验收]`
    - `#47` `P4.2.2` `P3-sim` 模拟发生器页 `[已验收]`
    - `#48` `P4.2.3` `P4` 输入工序链处理闭环 `[已验收]`
    - `#49` `P4.2.4` `P5-sim` 模拟消费页 `[已验收]`
    - `#50` `P4.2.5` 三段联调与回归验证 `[已验收]`
    - `待同步` `P4.2.6` 模拟研制执行器 `[已验收]`
  - `#69` `P4.3` 自演进巡检闭环 `[已验收]`
    - `#68` `P4.3.1` 巡检协议与运行规范 `[已验收]`
    - `#71` `P4.3.2` 自演进巡检前端卡片工作区 `[已验收]`
    - `#70` `P4.3.3` 巡检引擎、存储与统一运行管理 `[已验收]`
  - `#75` `P4.4` 后端服务化与运行时演进 `[已验收]`
    - `#72` `P4.4.1` 核心业务循环与统一命令模型 `[已验收]`
    - `#73` `P4.4.2` Runtime Coordinator、Worker 与 Queue 标准化 `[已验收]`
    - `#76` `P4.4.3` Backend Service 分域与接口边界落地 `[已验收]`
    - `#74` `P4.4.4` 数据模型、投影模型与存储升级 `[已验收]`
  - `待同步` `P4.5` 真实工具落地验证 `[开发中]`
    - `待同步` `P4.5.1` 工具定义与交付契约升级 `[已完成]`
    - `待同步` `P4.5.2` 产物存储、版本与比对机制 `[已完成]`
    - `待同步` `P4.5.3` AI 生成链与模板执行链 `[已完成]`
    - `待同步` `P4.5.4` 前端元组件样例实现与验证 `[已完成]`
    - `待同步` `P4.5.5` `P3 -> P4 -> P5` 真实交付闭环验证 `[已完成]`

## 已退役旧节点

- `#8` `WBS L2: P4.2 工具匹配分析与命中规则` `[已关闭，历史记录]`
- `#14` `WBS L2: P4.4 工具管理、优化与复用度量` `[已关闭，历史记录]`
- `#28` `WBS L2: P4.3 工具组合规则与装配约束` `[已关闭，历史记录]`

## 当前节点说明

### `P4.1` 已验收状态

`P4.1` 当前已经完成、合入 `main`，并按当前口径视为已验收，其结果包括：

- 工具描述模型
- 工具仓库 CRUD
- 工具分类与标签体系
- 工具匹配规则 MVP
- 工具验证工作台
- 统一数据层与同源快照验证

当前工作树后续开发默认直接承接 `P4.1` 已交付底座，不再重复创建旧节点。

### `P4.2` 当前范围

`P4.2` 用于把 `P3-sim -> P4 -> P5-sim` 的输入工序链闭环固定下来，当前轮次只做最小验证闭环，不做真实编排平台：

- `P3-sim` 负责生成并提交 `工具需求单`
- `P4` 负责受理总单、拆分叶子项、生成推荐、人工逐项审定，以及批准后的交付或研制输出
- `P5-sim` 负责整单查询、叶子查询、进度查询和结果消费验证
- 当前业务案例固定为 `模拟蓝军`
- `工具需求单` 是这一轮 `P3 / P4 / P5` 串联的主干交付流对象

## 2026-04-16 建模纠偏记录

本轮延续并固化一项建模纠偏：

- `P4.1.1` / `P4.1.3` / `P4.1.6` 不再把“资料接入 / 知识处理 / 知识治理”之类的平台建设能力当成工具仓业务域
- `ToolDefinition` 的核心结构化字段改为 `primary_domain_id / tool_form_id / runtime_platform_ids / lifecycle_stage_ids`
- `coverage_matrix` 的语义改为“业务域 × 工具形态”，不再使用知识仓内部阶段作为热力矩阵主轴

## 2026-04-16 新增闭环记录

本轮新增 `P4.2`，并固定以下协议方向：

- `P3` 发给 `P4` 的标准对象名为 `工具需求单`
- 工具需求树固定为 `系统 / 分系统 / 子系统 / 模块 / 组件（工具）` 五层
- 只有 `component` 叶子项进入 `P4` 实际处理
- 命中时，`P4` 直接返回现有工具的获取接口
- 未命中时，`P4` 只返回预计完成时间与进度查询接口；制造任务留在 `P4` 内部处理
- `P5` 支持整单查询与叶子项查询，可自动轮询，也可人工决策何时再次查询

## 2026-04-17 模拟研制执行器补充

本轮新增 `P4.2.6`，用于修正一个关键实现偏差：

- 当前 `manufacture` 分支不再允许由 `P5` 查询动作推动进度
- 研制推进改为 `P4` 内部后台模拟执行器负责
- `P4` 工具仓库页将增加“模拟研制队列”展示
- `P5` 保持只读查询角色，不知道 `P4` 内部采用何种推进机制

## 2026-04-17 工具仓库测试管理与多场景模拟补充

本轮为演示与回归效率补充两个能力：

- `P4.1.2` 工具仓库页增加单工具安全删除，以及当前阶段临时性的“一键清空全部工具”测试入口
- `P4.2.2` `P3-sim` 从单一蓝军发生器升级为“典型工单发生器”，固定支持 `模拟蓝军 / 导航规划 / 数据治理` 三类预置工单

## 2026-04-18 自演进巡检闭环补充

本轮新增 `P4.3`，用于修正另一个结构性缺口：

- 自演进巡检不再附着于 `P4.2` 输入工序链
- `P4.3` 作为独立生命周期存在，负责工具池自检、建议处置、内部任务和自动修复
- `P4.3` 首版固定拆为 `P4.3.1 协议与运行规范 / P4.3.2 前端卡片工作区 / P4.3.3 巡检引擎、存储与统一运行管理`
- `P4.3` 首版采用 `手动 + 定时` 触发，统一由 `P4 runtime coordinator` 推进
- 低风险建议允许自动改写工具数据，但必须保留变更前后快照与任务级回退能力
- 已同步远端节点 `#69 / #68 / #71 / #70`，并已加入 `Project 7`
- `#12 -> #69 -> (#68 / #71 / #70)` 已切换为 GitHub 原生 `sub-issue` 树，不再只是正文模拟关系

## 2026-04-18 后端架构演进补充

本轮新增 `P4.4`，用于把 `P4` 从“验证可用的工具中台”继续推进到“可独立服务化的后台架构底座”：

- `P4.4` 首版固定拆为 `P4.4.1 核心业务循环 / P4.4.2 Runtime Coordinator、Worker 与 Queue / P4.4.3 Backend Service 分域与接口边界 / P4.4.4 数据模型、投影模型与存储升级`
- 新增四份专项设计文档，分别覆盖业务循环、运行时、服务边界和数据投影
- 新增一份统一实施计划：`docs/superpowers/plans/2026-04-18-p4-backend-architecture-evolution.md`
- 已同步远端节点 `#75 / #72 / #73 / #76 / #74`
- `#12 -> #75 -> (#72 / #73 / #76 / #74)` 已切换为 GitHub 原生 `sub-issue` 树

## 2026-04-16 生命周期建模补充

本轮新增 `P4.2.1` 的专属约束文档后，`工具需求单` 的协议口径进一步固定为：

- `撤销` 属于 `P3` 侧动作，不属于 `P4`
- `驳回` 属于 `P4` 侧动作，且必须保留记录
- `撤销` 与 `驳回` 不是同一语义，不能混用
- 工单必须同时暴露 `lifecycle_status / review_status / delivery_status`
- `已审定` 不等于 `已交付`
- 只有全部批准项都形成可交付结果后，才算 `P4` 闭环完成
- 删除运行时 JSON 只能算开发重置，不能算业务生命周期动作
