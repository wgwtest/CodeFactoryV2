# P4 工具中台统一数据层与同源快照验证设计

**日期：** 2026-04-15

**对应节点：**
- `P4.1.6` 统一数据层与同源快照验证

**上级节点：**
- `P4.1` 第一批最小闭环

## 1. 设计目标

在不改变 `XX-P4` 当前四个一级工作区信息架构的前提下，为 `P4` 补齐一套独立且统一的数据层，使总览、输入工具链、自演进巡检和工具仓库都从同一份状态快照投影数据，而不是分别拼装各自的局部结果。

本节点聚焦两个结果：

- 建立 `ToolHubStateSnapshot` 作为 `P4` 的统一状态视图
- 建立“同源快照验证”机制，证明多路页面数据属于同一份状态快照

## 2. 当前问题

当前实现已经具备“同一数据根”的基础：

- 工具定义、匹配运行、自演进运行都存放在同一个 `tool_hub_root`
- `overview` 已经从 `tools + runs` 派生一部分摘要状态

但当前仍存在以下问题：

- 前端分别请求 `overview / tools / evolution-runs`，尚未明确这些接口是否来自同一份统一状态
- `metrics / risk_summary / coverage_matrix / recent runs` 仍是页面导向的拼装结果，尚未沉淀为独立的派生层
- 缺少统一的 `snapshot_id`，无法证明四个工作区看到的是同一时刻的 `P4` 状态
- 旧版矩阵语义曾把平台建设能力误当成工具仓业务域，导致 `coverage_matrix` 轴线本身存在建模偏差

## 3. 设计边界

### 3.1 本节点要解决的问题

- 统一 `P4` 的读模型
- 明确原始事实层与派生状态层的边界
- 为四个工作区建立一致的数据消费方式
- 增加同源快照校验和回归验证

### 3.2 本节点明确不做

- 不重写当前 `P4` 页面结构
- 不扩展完整数据库表设计
- 不引入复杂事件总线或任务编排
- 不继续扩展详细工具字段设计
- 不把前端临时 UI 状态纳入统一数据层

## 4. 统一数据层原则

### 4.1 一份事实源原则

`P4` 只能有一份业务事实源。

页面、组件和不同 API 可以返回不同切片，但这些切片都必须来自同一个统一状态快照，而不是各自重新定义状态。

### 4.2 原始事实与派生状态分层

统一数据层必须分为两层：

- `raw`：原始事实
- `derived`：从原始事实稳定推导出来的派生状态

判断标准：

- 可独立持久化、可被追溯、可被审核的数据属于 `raw`
- 可由 `raw` 重算得到、无需独立审批落库的数据属于 `derived`

### 4.3 页面只消费投影

四个工作区不直接定义自己的局部状态模型，只能消费统一快照的投影切片。

## 5. 统一状态快照模型

建议定义统一对象：`ToolHubStateSnapshot`

```yaml
ToolHubStateSnapshot:
  meta:
    snapshot_id:
    generated_at:
    state_version:
    source_contract_version:

  raw:
    catalogs:
    tools:
    match_runs:
    evolution_runs:

  derived:
    metrics:
    run_monitor:
    risk_summary:
    coverage_matrix:
    pending_suggestions:
```

### 5.1 `meta`

至少包含：

- `snapshot_id`
- `generated_at`
- `state_version`
- `source_contract_version`

其中 `snapshot_id` 是同源验证的核心锚点。

### 5.2 `raw`

第一批最小事实对象固定为：

- `catalogs`
- `tools`
- `match_runs`
- `evolution_runs`

其中 `catalogs` 至少包含：

- `domains`
- `lifecycle_stages`
- `tool_forms`
- `runtime_platforms`
- `input_types`
- `output_types`
- `supported_sources`

### 5.3 `derived`

第一批最小派生状态固定为：

- `metrics`
- `run_monitor`
- `risk_summary`
- `coverage_matrix`
- `pending_suggestions`

## 6. 派生层边界

### 6.1 `metrics`

回答“当前 `P4` 的整体规模和健康度是什么”。

建议至少包含：

- `tool_count`
- `active_tool_count`
- `verified_tool_count`
- `draft_tool_count`
- `archived_tool_count`
- `match_run_count`
- `evolution_run_count`
- `overlap_candidate_count`
- `pending_suggestion_count`
- `recent_success_rate`

### 6.2 `run_monitor`

回答“当前运行态如何”。

建议至少包含：

- `active_match_run_count`
- `active_evolution_run_count`
- `latest_match_run`
- `latest_evolution_run`
- `failing_run_count`
- `stale_run_count`

### 6.3 `risk_summary`

回答“当前最值得关注的风险是什么”。

建议作为最新一轮 `EvolutionRun` 或聚合 `open` finding 的轻量摘要。

### 6.4 `coverage_matrix`

回答“工具在业务域 × 工具形态上的覆盖情况如何”。

它只是 `raw.tools + raw.catalogs` 的投影，不是单独维护的数据表。

### 6.5 `pending_suggestions`

回答“当前有哪些待处理的演进建议”。

第一批可由 `EvolutionRun.findings` 投影得到，后续若需要人工确认闭环，再提升为独立事实对象。

## 7. 四个工作区的消费规则

### 7.1 总览

只消费：

- `meta`
- `derived.metrics`
- `derived.run_monitor`
- `derived.risk_summary`

### 7.2 输入工具链

只消费：

- `meta`
- `raw.tools`
- `raw.catalogs`
- `raw.match_runs`

### 7.3 自演进巡检

只消费：

- `meta`
- `raw.evolution_runs`
- `derived.pending_suggestions`
- `raw.tools`
- `raw.catalogs`

### 7.4 工具仓库

只消费：

- `meta`
- `raw.tools`
- `raw.catalogs`
- `derived.coverage_matrix`

## 8. API 投影策略

本节点不要求第一批就暴露单独的 `/api/tool-hub/state`。

推荐先采用“内部统一快照 + 外部多接口投影”的方式：

- `GET /api/tool-hub/overview`
- `GET /api/tool-hub/tools`
- `GET /api/tool-hub/evolution-runs`

这些接口都返回：

```yaml
{
  meta: { snapshot_id, generated_at, state_version },
  data: ...
}
```

这样可以在不破坏当前页面接口结构的前提下，先建立统一状态快照机制。

## 9. 同源快照验证

### 9.1 验证目标

证明当前页面中不同工作区看到的数据来自同一份 `ToolHubStateSnapshot`。

### 9.2 验证方法

后端：

- `overview / tools / evolution-runs` 必须返回同一个 `snapshot_id`

前端：

- 页面并发请求这三路数据后，必须校验三者 `snapshot_id` 是否一致
- 若不一致，页面必须给出显式一致性警告

### 9.3 联动验证样例

最小联动验证建议为：

1. 新增或修改一个工具
2. 再次请求 `overview / tools / evolution-runs`
3. 验证三路响应 `snapshot_id` 一致
4. 验证 `tool_count` 与工具列表长度一致
5. 验证覆盖矩阵和风险/建议派生结果随事实变化同步更新

## 10. 实现建议

建议后端内部组织为：

```text
repository
-> snapshot builder
-> service projection
-> route response
```

对应职责：

- `repository`：只读写事实
- `snapshot builder`：统一构建 `ToolHubStateSnapshot`
- `service`：从快照投影各接口返回
- `route`：暴露 API 契约

## 11. 验收标准

本节点完成时，至少满足：

1. 后端内部存在统一的 `ToolHubStateSnapshot`
2. `overview / tools / evolution-runs` 三个读接口统一返回 `meta + data`
3. 三个读接口在同一次读取中返回同一个 `snapshot_id`
4. 前端会校验三路数据的 `snapshot_id`
5. 若快照不一致，页面会给出显式警告
6. 存在自动化测试证明“不同工作区消费的是同一份状态快照投影”
