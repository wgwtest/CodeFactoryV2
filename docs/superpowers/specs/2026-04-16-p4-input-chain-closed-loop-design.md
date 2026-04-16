# P4 输入工序链闭环与 P3/P5 模拟页设计

**日期：** 2026-04-16

**对应节点建议：**
- `P4.2` 输入工序链闭环探索
- `P4.2.1` 协议与对象模型
- `P4.2.2` `P3-sim` 模拟发生器页
- `P4.2.3` `P4` 输入工序链处理闭环
- `P4.2.4` `P5-sim` 模拟消费页
- `P4.2.5` 三段联调与回归验证

## 1. 设计目标

在不引入真实 `P3`、真实 `P5`、真实工具开发编排的前提下，为当前 `P4` 增加一条可演示、可查询、可校验的输入工序链闭环：

`P3 模拟发生器 -> P4 接收工具需求总单 -> 拆叶子项 -> 分析/核对/匹配 -> 未命中模拟制造 -> P5 模拟消费与查询`

本轮目标不是补齐完整平台，而是把跨阶段协议、查询机制和页面边界固定清楚，给后续 `P3`、`P4`、`P5` 的正式开发留下稳定外壳。

## 2. 设计边界

### 2.1 本轮要做

- 定义 `P3 -> P4 -> P5` 的标准协议对象
- 提供独立 `P3-sim` 页面，模拟 `P3` 产生工具需求总单
- 提供升级后的 `P4` 输入工具链工作区，处理总单与叶子项
- 提供独立 `P5-sim` 页面，模拟 `P5` 查询和消费 `P4` 输出
- 支持整单查询、叶子查询、进度查询
- 支持未命中后由 `P4` 内部进行“模拟制造”

### 2.2 本轮不做

- 不做真实 `P3` 建模链
- 不做真实 `P5` 执行链
- 不做真实工具开发、真实制品发布、真实调度器
- 不做消息推送、审批流、权限治理
- 不做多工具依赖编排

## 3. 页面拓扑与解耦原则

### 3.1 页面拓扑

本轮使用 3 个独立页面：

- `/xx-p3-sim`
- `/xx-p4`
- `/xx-p5-sim`

### 3.2 页面职责

`/xx-p3-sim`：

- 只负责生成并提交 `工具需求总单`
- 不负责查看 `P4` 内部处理细节

`/xx-p4`：

- 只负责受理、拆叶子项、匹配、模拟制造、结果输出
- 不负责 `P3` 的树编辑体验，也不负责 `P5` 的消费决策界面

`/xx-p5-sim`：

- 只负责查询整单、查询叶子进度、查看可取工具信息
- 不负责修改 `P4` 内部状态

### 3.3 解耦原则

三页只能共享协议对象，不能共享业务页面组件。

允许共享：

- 后端 API 契约
- 前端镜像类型
- 通用请求封装

不允许共享：

- `P3-sim` 与 `P4` 的页面组件
- `P4` 与 `P5-sim` 的页面状态
- 把 `P3` 或 `P5` 的模拟流程直接嵌进 `P4` 页面

## 4. 业务案例与树型拆分

本轮统一业务案例固定为：`模拟蓝军`

### 4.1 一级分解

`模拟蓝军系统` 的一级分系统固定为：

- `战场建模`
- `蓝军编组`
- `对抗推演`
- `行动控制`
- `评估复盘`

### 4.2 固定层级

工具需求树固定为 5 层：

- `系统`
- `分系统`
- `子系统`
- `模块`
- `组件（工具）`

对应 `node_type` 固定为：

- `system`
- `subsystem`
- `sub_subsystem`
- `module`
- `component`

其中只有 `component` 是 `P4` 真正处理的叶子项。

### 4.3 默认演示树

默认演示树至少覆盖以下路径：

- `模拟蓝军系统 / 战场建模 / 空间环境建模 / 地图地形建模 / 战场底图导入器`
- `模拟蓝军系统 / 战场建模 / 空间环境建模 / 环境条件建模 / 通视遮蔽分析器`
- `模拟蓝军系统 / 蓝军编组 / 兵力结构编组 / 编制树生成 / 蓝军编组树构造器`
- `模拟蓝军系统 / 对抗推演 / 推演规则驱动 / 规则集装配 / 交战规则装配器`
- `模拟蓝军系统 / 行动控制 / 任务下达控制 / 行动计划编排 / 行动计划编排器`
- `模拟蓝军系统 / 评估复盘 / 结果评估 / 指标评估 / 效果指标计算器`

这棵树是默认演示基线，不代表最终业务全量拆分。

## 5. 核心协议对象

### 5.1 `ToolDemandSheetCreateRequest`

`P3` 或 `P3-sim` 发给 `P4` 的标准输入对象。

```yaml
sheet_name:
source:
  phase:
  producer:
  business_case:
  scenario_id:
  scenario_name:
requested_by:
root_node:
notes:
```

字段规则：

- `sheet_name`：总单名称
- `source.phase`：当前阶段固定允许 `p3_simulator` 或未来真实 `p3`
- `source.producer`：来源组件标识
- `source.business_case`：本轮固定为 `simulated_blue_force`
- `requested_by`：当前固定为 `P3`
- `root_node`：完整树型需求根节点

### 5.2 `ToolDemandNode`

树节点标准对象。

```yaml
node_id:
node_type:
node_name:
node_code:
description:
business_domain_id:
children:
component_spec:
```

规则：

- `node_id`：单张总单内唯一
- `node_type`：只允许 `system / subsystem / sub_subsystem / module / component`
- `children`：非 `component` 必须有子节点
- `component`：必须没有子节点，且必须携带 `component_spec`

### 5.3 `ComponentSpec`

叶子组件的需求规格对象。

```yaml
component_name:
component_code:
problem_statement:
required_input_types:
expected_output_types:
preferred_tool_forms:
preferred_runtime_platforms:
lifecycle_stage_ids:
keywords:
acceptance_notes:
```

这是 `P4` 拆分叶子项时的直接输入源。

### 5.4 `ToolDemandSheet`

`P4` 受理后的总单对象。

```yaml
sheet_id:
sheet_name:
status:
source:
requested_by:
business_case:
root_node:
item_count:
matched_existing_count:
manufacturing_count:
ready_for_fetch_count:
failed_count:
submitted_at:
updated_at:
```

### 5.5 `ToolDemandItem`

由叶子 `component` 拆出来的独立受理项。

```yaml
item_id:
sheet_id:
source_node_id:
ancestry:
business_domain_id:
component_name:
required_input_types:
expected_output_types:
preferred_tool_forms:
preferred_runtime_platforms:
lifecycle_stage_ids:
status:
analysis_result:
check_result:
match_result:
supply_result:
submitted_at:
updated_at:
```

### 5.6 `ToolManufacturePlan`

`P4` 内部对象，不直接给 `P5`。

```yaml
plan_id:
item_id:
status:
estimated_ready_at:
planned_tool_name:
planned_tool_form_id:
planned_runtime_platform_ids:
created_at:
updated_at:
```

### 5.7 `ToolSupplyResult`

`P4 -> P5` 的标准输出对象。

```yaml
result_type:
item_id:
tool_ref:
fetch_interface:
progress_query_interface:
estimated_ready_at:
suggested_poll_after_seconds:
available_at:
last_message:
```

`result_type` 固定为：

- `existing_tool`
- `pending_manufacture`
- `manufactured_tool`

## 6. 获取接口与查询接口协议

### 6.1 `ToolFetchManifest`

`P5` 真正获取工具时，不直接拿内部文件路径，而是通过统一获取接口拿一个标准清单。

```yaml
tool_id:
tool_name:
tool_version:
tool_form_id:
runtime_platform_ids:
fetch_mode:
entrypoint_type:
entrypoint_locator:
contract_version:
updated_at:
```

字段规则：

- `fetch_mode`：当前固定为 `descriptor`
- `entrypoint_type`：允许 `http / descriptor / artifact_ref / manual`
- `entrypoint_locator`：调用或获取位置

### 6.2 `ItemProgressView`

叶子项进度查询的轻量对象。

```yaml
item_id:
status:
progress_percent:
result_type:
estimated_ready_at:
suggested_poll_after_seconds:
fetch_interface:
last_message:
updated_at:
```

## 7. 状态机

### 7.1 叶子项状态机

`ToolDemandItem.status` 固定为：

- `accepted`
- `analyzing`
- `checking`
- `matched_existing`
- `manufacturing_pending`
- `manufacturing_in_progress`
- `ready_for_fetch`
- `failed`

状态流固定为：

- 命中链路：
  `accepted -> analyzing -> checking -> matched_existing`
- 未命中链路：
  `accepted -> analyzing -> checking -> manufacturing_pending -> manufacturing_in_progress -> ready_for_fetch`
- 异常链路：
  任一非终态可进入 `failed`

### 7.2 总单状态机

`ToolDemandSheet.status` 固定为：

- `accepted`
- `processing`
- `partially_ready`
- `ready`
- `failed`

聚合规则：

- 刚受理成功：`accepted`
- 至少一个叶子项在处理中，且没有任何叶子可取：`processing`
- 至少一个叶子已可取，但整单未全部可取：`partially_ready`
- 所有叶子进入 `matched_existing` 或 `ready_for_fetch`：`ready`
- 总单解析失败或全部叶子失败：`failed`

## 8. P4 处理规则

### 8.1 受理规则

- `P4` 收到 `ToolDemandSheetCreateRequest` 后，立即生成 `sheet_id`
- 对树执行结构校验
- 自动从所有 `component` 叶子节点拆出 `ToolDemandItem`

### 8.2 分析与核对规则

每个 `ToolDemandItem` 必须经过：

- 结构分析
- 需求核对
- 工具匹配

当前阶段这三步可以是规则型实现，不要求复杂推理。

### 8.3 匹配规则

匹配维度固定为：

- 业务域
- 生命周期
- 输入类型
- 输出类型
- 工具形态
- 运行平台
- 关键词

命中后立即生成 `existing_tool` 类型的 `ToolSupplyResult`。

### 8.4 未命中规则

未命中后：

- `P4` 内部生成 `ToolManufacturePlan`
- 返回 `pending_manufacture` 类型结果
- 给出 `estimated_ready_at`
- 给出 `progress_query_interface`

### 8.5 模拟制造规则

本轮不启动后台调度器，采用“按查询自动推进”的模拟制造方式。

规则固定为：

- 创建计划时写入 `estimated_ready_at`
- 每次查询 `item progress` 时，根据当前时间推进状态
- 未到预计时间：返回 `manufacturing_pending` 或 `manufacturing_in_progress`
- 到达预计时间：自动转为 `ready_for_fetch`
- 同时写入一个模拟工具定义和可取清单

## 9. API 设计

### 9.1 模拟发生器入口

```text
POST /api/tool-hub/mock-generators/blue-force-demand-sheets
```

用途：

- 由 `P3-sim` 调用
- 生成一张默认“模拟蓝军”工具需求总单
- 内部再提交给正式受理入口

### 9.2 正式受理入口

```text
POST /api/tool-hub/demand-sheets
```

请求体：

- `ToolDemandSheetCreateRequest`

### 9.3 总单列表

```text
GET /api/tool-hub/demand-sheets
```

用途：

- 展示最近总单
- 给 `P4` 和 `P5-sim` 页面做历史选择

### 9.4 整单查询

```text
GET /api/tool-hub/demand-sheets/{sheet_id}
```

返回：

- 总单头信息
- 原始树
- 聚合统计
- 所有叶子项状态
- 所有叶子项当前 `ToolSupplyResult`

### 9.5 叶子项详情

```text
GET /api/tool-hub/demand-items/{item_id}
```

返回：

- `ToolDemandItem`
- 当前 `ToolSupplyResult`
- 分析、核对、匹配结果

### 9.6 叶子项进度查询

```text
GET /api/tool-hub/demand-items/{item_id}/progress
```

返回：

- `ItemProgressView`

### 9.7 工具获取清单接口

```text
GET /api/tool-hub/tools/{tool_id}/fetch
```

返回：

- `ToolFetchManifest`

## 10. 页面设计

### 10.1 `/xx-p3-sim`

最小区块固定为：

- 案例选择区
- 需求树预览区
- 提交结果区

页面职责：

- 选择“模拟蓝军”默认案例
- 一键生成总单
- 预览树
- 提交到 `P4`
- 返回 `sheet_id`

### 10.2 `/xx-p4`

当前保留四个一级 Tab，但 `输入工具链` 工作区升级为闭环页。

`输入工具链` 工作区固定区块：

- `P3 模拟发生区`
- `总单摘要区`
- `总单树审查区`
- `叶子项处理流水区`
- `当前叶子详情区`
- `P5 输出预览区`
- `整单查询区`
- `叶子进度查询区`

### 10.3 `/xx-p5-sim`

最小区块固定为：

- 查询输入区
- 整单结果区
- 叶子进度区
- 可取工具区
- 自动轮询/人工决策切换区

页面职责：

- 输入 `sheet_id` 看整单
- 输入 `item_id` 看进度
- 命中时查看 `fetch_interface`
- 未命中时查看 `estimated_ready_at` 和 `progress_query_interface`

## 11. 数据层与目录建议

在现有 `.data/tool_hub/` 下新增：

- `.data/tool_hub/demand_sheets/`
- `.data/tool_hub/demand_items/`
- `.data/tool_hub/manufacture_plans/`

当前阶段仍采用文件型仓储。

统一快照在 `raw` 中新增：

- `demand_sheets`
- `demand_items`
- `manufacture_plans`

统一快照在 `derived` 中新增：

- `input_chain_summary`
- `sheet_status_board`
- `p5_delivery_projection`

## 12. 实施建议

建议按以下顺序实施：

1. 定义协议模型与接口契约
2. 补充文件型仓储
3. 实现 `P3-sim` 模拟发生器入口
4. 实现 `P4` 总单受理、拆叶子项、匹配、模拟制造
5. 实现整单查询、叶子详情、进度查询、工具获取清单接口
6. 改造 `/xx-p4` 输入工具链工作区
7. 新增 `/xx-p3-sim` 与 `/xx-p5-sim`
8. 做三页联调与回归测试

## 13. 验收标准

达到完成状态，至少满足：

1. 存在独立 `P3-sim` 页面 `/xx-p3-sim`
2. 存在独立 `P5-sim` 页面 `/xx-p5-sim`
3. `P3-sim` 能生成并提交一张“模拟蓝军”工具需求总单
4. `P4` 能把总单拆成叶子项并处理
5. 命中现有工具时，`P4` 能返回统一 `fetch_interface`
6. 未命中时，`P4` 能返回预计生成时间与进度查询接口
7. `P5-sim` 能查整单，也能查叶子项进度
8. 到达预计时间后，叶子项能自动转为 `ready_for_fetch`
9. 三页之间只通过协议联动，不共享业务页面组件
