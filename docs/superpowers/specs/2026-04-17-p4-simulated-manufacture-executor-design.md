# P4 模拟研制执行器设计

**日期：** 2026-04-17

**对应节点：**
- `P4.2.6` 模拟研制执行器

## 1. 问题定义

当前 `P4` 已经支持：

- `approved_manufacture`
- `ToolManufacturePlan`
- `P5` 通过 `progress_query_interface` 查询进度

但当前实现仍存在一个关键偏差：

- 研制进度是由 `GET /demand-items/{item_id}/progress` 触发推进的

这意味着“有人来查，制造才前进”。该行为不符合后续真实系统的语义，也无法满足“工具仓库内存在多个并行研制中工具”的展示诉求。

因此，本轮需要为 `P4` 增加一个内部的、仅用于批次阶段闭环验证的 `模拟研制执行器`。

## 2. 设计目标

- 把“查询进度”和“推进进度”彻底解耦
- 支持多个 `approved_manufacture` 工具并行模拟研制
- 支持不同工具具有不同的模拟时长
- 允许 `P4` 内部持续推进计划，而 `P5` 只读查询结果
- 让工具仓库页能看到当前研制队列，而不是只能在单叶子项页面看到待完成结果

## 3. 设计边界

### 3.1 本轮要做

- 在 `P4` 后端内部创建后台模拟执行器
- 为 `ToolManufacturePlan` 增加时间与模拟配置字段
- 在研制计划进入队列后，由执行器自动推进
- 提供独立的研制计划查询接口，供 `P4` 页面展示
- 让 `P5` 继续只通过现有查询接口消费结果

### 3.2 本轮不做

- 不做真实编排器、任务队列、中间件
- 不做真实代码生成、制品发布、流水线
- 不做 WebSocket 或消息推送
- 不做跨进程分布式执行器

## 4. 核心原则

### 4.1 执行器推进原则

`progress` 查询接口只负责读取状态，不再承担状态推进职责。

状态推进由 `P4` 内部后台执行器完成。

### 4.2 解耦原则

`P5` 不知道 `P4` 内部是否用线程、定时器或其他机制推进。

`P5` 只知道：

- 当前进度是多少
- 是否可获取工具
- 建议多久之后再次查询

### 4.3 最小实现原则

执行器只需要支持单进程、单机、本地运行态。

不需要引入 Celery、Redis、APScheduler 或其他重型设施。

## 5. 数据模型调整

### 5.1 `ToolManufacturePlan`

在现有字段基础上新增：

- `simulation_profile`
- `target_duration_seconds`
- `started_at`
- `completed_at`
- `last_progress_message`

说明：

- `simulation_profile`：用于表达本次模拟采用的时长档位，例如 `fast / normal / slow`
- `target_duration_seconds`：总模拟时长
- `started_at`：执行器正式接管时间
- `completed_at`：完成时间
- `last_progress_message`：供页面直接展示的最近进展说明

### 5.2 `ToolManufacturePlanView`

新增一个面向页面消费的只读投影视图，至少包含：

- `plan_id`
- `item_id`
- `sheet_id`
- `component_name`
- `planned_tool_name`
- `status`
- `progress_percent`
- `simulation_profile`
- `target_duration_seconds`
- `estimated_ready_at`
- `started_at`
- `completed_at`
- `last_progress_message`

该对象用于 `P4` 工具仓库页展示“模拟研制队列”。

## 6. 执行流程

### 6.1 进入队列

当需求项被 `approve_manufacture` 后：

- 创建或复用 `ToolManufacturePlan`
- 初始状态为 `manufacturing_pending`
- 生成模拟时长与预计完成时间
- 写入 `pending_manufacture` 的供给结果

### 6.2 后台推进

后台执行器周期性扫描：

- 状态为 `manufacturing_pending`
- 或 `manufacturing_in_progress`

的计划。

推进规则：

- 尚未开始时，写入 `started_at` 并切到 `manufacturing_in_progress`
- 进行中按时间比例更新 `progress_percent`
- 到达目标时间后，创建模拟工具并切到 `ready_for_fetch`

### 6.3 完成产物

完成后执行器需要：

- 生成 `manufactured_tool`
- 为需求项写入正式 `fetch_interface`
- 把需求项状态改为 `ready_for_fetch`
- 触发总单聚合刷新

## 7. 后端结构建议

建议新增内部组件：

- `ToolManufactureExecutor`

职责：

- 持有仓库根目录
- 周期性扫描制造计划
- 根据当前时间推进状态
- 原子化写回计划、需求项、工具定义

它是 `P4` 内部实现细节，不对外暴露。

## 8. 并发与文件写入约束

由于本轮运行态基于本地 JSON 文件：

- 仓库读写必须具备共享锁
- JSON 写入应采用原子替换

否则后台线程与 API 请求并发时可能出现半写入或读取脏数据。

## 9. 对外接口

本轮新增：

- `GET /api/tool-hub/manufacture-plans`

返回当前模拟研制队列视图。

保留：

- `GET /api/tool-hub/demand-items/{item_id}/progress`

但该接口改为纯查询，不再触发推进。

## 10. 页面影响

### 10.1 `P4`

在“工具仓库”工作区增加“模拟研制队列”区块，展示：

- 在研组件
- 当前状态
- 当前进度
- 模拟时长档位
- 预计完成时间

### 10.2 `P5`

无需新增动作，只保留：

- 查询叶子项
- 刷新进度
- 自动轮询

但看到的状态将变成执行器驱动的真实变化。

## 11. 验收标准

- `approve_manufacture` 后，即使不调用 `progress` 查询，计划也会自动前进
- 多个待研制需求项可以并行推进
- 不同需求项具有不同模拟时长
- `P5` 轮询只读取状态，不会触发推进
- `P4` 工具仓库能看到研制队列
- 完成后会自动生成可获取的模拟工具

## 12. 风险与约束

- 当前执行器只适合单进程本地开发环境，不适合生产
- 如果服务被停止，模拟研制会暂停；重启后按时间与计划恢复
- 本轮不保证精确秒级调度，只保证状态变化正确、可观察、可验证
