# P4 自演进巡检闭环设计

**日期：** 2026-04-18

**对应节点建议：**
- `P4.3` 自演进巡检闭环
- `P4.3.1` 巡检协议与运行规范
- `P4.3.2` 自演进巡检前端卡片工作区
- `P4.3.3` 巡检引擎、存储与统一运行管理

## 1. 设计目标

在不把 `P4` 扩展成完整治理平台、审批平台或编排平台的前提下，为工具中台补上一条真正独立的“自演进巡检闭环”：

`工具仓快照 -> 巡检轮次 -> 发现项 -> 人工采纳/忽略 -> P4 内部执行任务 -> 自动改写或人工跟进 -> 留痕/回退`

本轮目标不是做复杂治理体系，而是把以下内容固定清楚：

- 自演进巡检不再只是一个报告面板，而是独立生命周期
- 巡检结果不再停留在 `finding`，而是能进入 `P4` 内部任务队列
- 低风险任务允许自动改写工具数据
- 自动改写必须可追溯、可回退
- 后端不继续为每条链路各写一个私有线程，而是形成 `P4` 统一运行协调器

## 2. 设计边界

### 2.1 本轮要做

- 新开 `P4.3`，与 `P4.2` 输入工序链彻底解耦
- 定义巡检配置、巡检轮次、发现项、内部任务、变更集、回退记录
- 支持 `手动 + 定时` 两类触发
- 支持人工对发现项执行 `采纳 / 忽略`
- 采纳后立即生成 `P4` 内部任务，不单独引入治理审批流
- 支持一部分低风险任务自动改写 `ToolDefinition`
- 支持任务级单次回退
- 前端提供卡片式自演进工作区
- 后端提供统一运行协调器，统一承接 `manufacture` 与 `evolution`

### 2.2 本轮不做

- 不做权限系统
- 不做专门的治理审批流
- 不做消息中间件、分布式调度、微服务拆分
- 不做 WebSocket 推送
- 不做高风险操作自动执行
- 不做自动归档、自动删除、自动合并工具

## 3. 生命周期定位与边界

### 3.1 `P4.2` 与 `P4.3` 边界

`P4.2` 处理：

- `P3 / P3-sim` 发来的 `工具需求单`
- 外部输入触发的工具命中、审定、交付、研制

`P4.3` 处理：

- `P4` 工具仓自身的规范性、重复性、覆盖性和可维护性
- 内部巡检触发的建议、内部任务与自动修复

因此：

- `P4.3` 不创建 `工具需求单`
- `P4.3` 的输出不发给 `P3`、不发给 `P5`
- `P4.3` 的产物是 `P4` 内部事实对象

### 3.2 自演进闭环目标

首版闭环固定为：

1. 工具池扫描
2. 生成本轮发现项
3. 人工对发现项做 `采纳 / 忽略`
4. 采纳项进入内部任务
5. 低风险任务自动落库，高风险任务保留为人工跟进任务
6. 所有写入保留前后快照、日志与回退能力

## 4. 运行口径

### 4.1 触发方式

第一版固定支持：

- `manual`
- `scheduled`

其中：

- `manual` 由页面操作员主动触发
- `scheduled` 由 `P4 runtime coordinator` 按配置周期触发

### 4.2 脏状态

为避免“每次改一个字段就立刻重新巡检”，系统维护一个 `evolution_dirty` 运行态标记。

以下行为会把 `evolution_dirty` 标记为 `true`：

- 新建工具
- 编辑工具
- 删除工具
- 自动改写工具
- 回退自动改写

定时巡检只在以下条件都满足时触发：

- `config.enabled = true`
- 到达 `interval_minutes`
- `evolution_dirty = true`

### 4.3 操作者模型

第一版不做权限控制，但所有写动作必须留痕。

- 查看范围：所有进入 `P4` 页面的操作者都可见
- 决策、回退、配置修改都必须带 `actor_id`
- 不做角色限制
- 留痕对象统一记录 `actor_id / actor_phase / action / occurred_at / message`

## 5. 协议对象

### 5.1 `EvolutionInspectionConfig`

```yaml
config_id: default
enabled: true
schedule_mode: manual_and_scheduled
interval_minutes: 60
include_draft_tools: true
focus_rule_ids:
  - missing_description
  - taxonomy_issue
  - overlap_risk
  - coverage_gap
overlap_threshold: 3
max_run_history: 50
auto_apply_rule_ids:
  - missing_description
  - taxonomy_issue
updated_by: p4-operator
updated_at: 2026-04-18T10:00:00Z
```

字段规则：

- `schedule_mode` 首版固定 `manual_and_scheduled`
- `focus_rule_ids` 控制本轮启用哪些巡检规则
- `auto_apply_rule_ids` 只允许出现低风险规则
- `interval_minutes` 允许前端配置，但必须大于 0

### 5.2 `EvolutionInspectionRun`

```yaml
run_id: evolution-run-xxx
status: queued | running | completed | failed
trigger_type: manual | scheduled
triggered_by: p4-operator | system
started_at: ...
completed_at: ...
failed_at: ...
snapshot_id: ...
summary:
  tool_count: 12
  finding_count: 5
  missing_description_count: 1
  taxonomy_issue_count: 1
  overlap_risk_count: 2
  coverage_gap_count: 1
  accepted_count: 0
  ignored_count: 0
  generated_task_count: 0
error_message: ""
created_at: ...
updated_at: ...
```

说明：

- `queued / running / completed / failed` 是运行态，不再把巡检轮次简化成固定 `completed`
- `summary` 同时包含“发现结构”和“处置聚合”

### 5.3 `EvolutionFinding`

```yaml
finding_id: finding-xxx
run_id: evolution-run-xxx
rule_id: missing_description | taxonomy_issue | overlap_risk | coverage_gap
severity: info | warning | critical
title: xxx
description: xxx
affected_tool_ids:
  - tool-1
evidence:
  current_summary: ""
  current_problem_statement: ""
  current_tags: []
decision_status: pending | accepted_to_task | ignored
decision_by: p4-operator
decision_at: ...
decision_note: ""
linked_task_id: evolution-task-xxx
created_at: ...
updated_at: ...
```

### 5.4 `EvolutionTask`

```yaml
task_id: evolution-task-xxx
source_run_id: evolution-run-xxx
source_finding_id: finding-xxx
task_type: auto_apply | manual_followup
task_status: queued | running | completed | failed | rolled_back
priority: low | medium | high
planned_action: normalize_metadata | enrich_description | manual_overlap_review | manual_coverage_followup
target_tool_ids:
  - tool-1
result_summary: ""
change_count: 0
rollback_available: false
created_by: p4-operator
created_at: ...
started_at: ...
completed_at: ...
updated_at: ...
```

### 5.5 `EvolutionChangeSet`

```yaml
change_set_id: ecs-xxx
task_id: evolution-task-xxx
tool_id: tool-1
change_kind: metadata_normalization | description_enrichment
before_snapshot: { ...ToolDefinition }
after_snapshot: { ...ToolDefinition }
applied_at: ...
applied_by: p4-runtime
```

### 5.6 `EvolutionRollbackRecord`

```yaml
rollback_id: erb-xxx
task_id: evolution-task-xxx
change_set_ids:
  - ecs-xxx
rolled_back_by: p4-operator
rolled_back_at: ...
rollback_summary: 已回退 1 个工具定义变更
```

## 6. 状态机与完成判定

### 6.1 巡检轮次状态

- `queued`
- `running`
- `completed`
- `failed`

### 6.2 发现项决策状态

- `pending`
- `accepted_to_task`
- `ignored`

### 6.3 内部任务状态

- `queued`
- `running`
- `completed`
- `failed`
- `rolled_back`

### 6.4 完成判定

必须明确区分 3 件事：

1. `巡检轮次完成`
   - 指本轮扫描、分析、发现项生成结束
2. `巡检轮次处置完成`
   - 指该轮所有 `finding` 都已变成 `accepted_to_task` 或 `ignored`
3. `优化执行完成`
   - 指由本轮生成的任务进入 `completed` 或 `rolled_back`

因此：

- `P4.3` 的“巡检完成”不等于“优化全部完成”
- 总览中的 `待演进建议数` 应统计 `decision_status = pending`
- 总览中的 `自演进任务积压数` 应统计 `task_status in (queued, running)`

## 7. 巡检规则与自动执行边界

### 7.1 首版巡检规则

- `missing_description`
- `taxonomy_issue`
- `overlap_risk`
- `coverage_gap`

### 7.2 允许自动执行的低风险改写

只允许非破坏性改写：

- `tags`
- `primary_domain_id`
- `tool_form_id`
- `runtime_platform_ids`
- `lifecycle_stage_ids`
- `summary`
- `problem_statement`
- `verification.last_verified_result`

### 7.3 禁止自动执行的高风险改写

- 自动归档
- 自动删除
- 自动合并
- 自动替换工具主记录

### 7.4 规则到任务类型的映射

- `missing_description`
  - 允许生成 `auto_apply`
- `taxonomy_issue`
  - 允许生成 `auto_apply`
- `overlap_risk`
  - 只允许生成 `manual_followup`
- `coverage_gap`
  - 只允许生成 `manual_followup`

## 8. 前端工作区设计

`P4.3` 页面工作区必须使用卡片式布局，卡片可独立增删，不把整块逻辑写成一个不可拆的大面板。

### 8.1 必要卡片

1. `巡检配置卡`
   - 频率、启用开关、重点规则、自动执行规则
2. `巡检轮次列表卡`
   - 展示已巡检轮次，可点选
3. `当前轮次摘要卡`
   - 展示当前选中轮次的统计、触发来源、运行状态
4. `发现项处置卡`
   - 展示当前轮次的发现项，并提供 `采纳 / 忽略`
5. `自演进任务队列卡`
   - 展示 `queued / running` 的内部任务
6. `已完成优化项卡`
   - 展示 `completed / rolled_back` 任务，并提供回退入口

### 8.2 推荐 DOM ID

- `xx-p4-evolution-config-card`
- `xx-p4-evolution-run-list-card`
- `xx-p4-evolution-summary-card`
- `xx-p4-evolution-findings-card`
- `xx-p4-evolution-task-queue-card`
- `xx-p4-evolution-completed-card`

### 8.3 页面交互规则

- 点选轮次时，只切换当前轮次上下文，不重建全页状态
- `发现项处置卡` 默认跟随当前轮次
- `已完成优化项卡` 不依赖选中轮次，展示全局优化历史
- 自动改写完成的任务必须展示“已改写工具数”和“回退”按钮

## 9. 后端结构设计

### 9.1 架构模式

当前 `apps/api` 仍是单体应用，不是微服务。本轮不拆微服务。

建议采用：

- `模块化单体`
- `tool_hub` 子域内部分层
- 单进程统一运行协调器

### 9.2 统一运行协调器

当前已有 `manufacture` 后台推进。`P4.3` 不再继续增加一个互不相干的私有线程，而是把底层统一为：

- `P4 runtime coordinator`

协调器内部负责两类任务源：

- `manufacture`
- `evolution`

协调器周期性执行：

1. 读取运行态与配置
2. 判断是否需要触发定时巡检
3. 推进 `evolution auto_apply` 队列
4. 推进 `manufacture` 队列

### 9.3 运行协调器原则

- 统一调度，前端分开展示
- 任务推进与查询解耦
- 不让前端查询动作推动状态前进
- 所有写入通过仓储层原子落盘

## 10. 存储设计

在 `.data/tool_hub` 下新增：

```text
evolution/
  config/
    default.json
  runs/
    <run_id>.json
  findings/
    <finding_id>.json
  tasks/
    <task_id>.json
  change_sets/
    <change_set_id>.json
  rollbacks/
    <rollback_id>.json
  operation_logs/
    <event_id>.json
runtime/
  state.json
```

说明：

- `runtime/state.json` 存放 `evolution_dirty`、`last_scheduled_evolution_at`
- `change_sets` 为回退提供事实依据
- `operation_logs` 保存操作者留痕

## 11. API 设计

首版使用 REST：

- `GET /api/tool-hub/evolution/config`
- `PATCH /api/tool-hub/evolution/config`
- `GET /api/tool-hub/evolution/runs`
- `POST /api/tool-hub/evolution/runs`
- `GET /api/tool-hub/evolution/runs/{run_id}`
- `POST /api/tool-hub/evolution/findings/{finding_id}/decision`
- `GET /api/tool-hub/evolution/tasks`
- `GET /api/tool-hub/evolution/tasks/{task_id}`
- `POST /api/tool-hub/evolution/tasks/{task_id}/rollback`

### 11.1 发现项决策请求

```yaml
actor_id: p4-operator
decision: accept | ignore
note: 接受该建议并转入内部优化任务
```

### 11.2 回退请求

```yaml
actor_id: p4-operator
note: 回退本次自动改写
```

## 12. 与统一数据层的关系

`P4.1.6` 已要求总览、输入工序链、自演进巡检、工具仓库消费统一事实源。

因此本轮需要把以下对象纳入 `ToolHubStateSnapshot.raw`：

- `evolution_config`
- `evolution_runs`
- `evolution_findings`
- `evolution_tasks`
- `runtime_state`

派生层至少补充：

- `pending_suggestion_count`
- `active_evolution_task_count`
- `recent_evolution_runs`
- `completed_optimization_count`

## 13. 验收标准

- `P4.3` 拥有独立设计文档与节点映射，不再附属于 `P4.2`
- 支持手动触发巡检并生成轮次、发现项
- 支持定时巡检配置与后台触发
- 支持对发现项执行 `采纳 / 忽略`
- 采纳后生成内部任务
- 低风险任务可自动改写工具数据
- 自动改写保留前后快照、日志，并可任务级回退
- 前端至少具备 6 张卡片式模块
- 后端运行协调器统一推进 `manufacture` 与 `evolution`

## 14. 风险与约束

- 当前统一运行协调器只适合本地单进程开发环境
- 调度不追求秒级精度，只追求状态正确、行为可观测
- 自动改写只处理低风险字段，避免错误扩大
- 高风险问题仍然需要人工跟进，不在本轮扩展为完整治理流程
