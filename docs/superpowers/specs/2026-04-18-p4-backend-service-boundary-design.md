# P4 Backend Service 边界与分域接口设计

**日期：** 2026-04-18

**对应节点建议：**
- `P4`
- `P4.2`
- `P4.3`

## 1. 设计目标

把未来的 `P4` 后端服务边界固定清楚，使其既能独立部署，又不会过早陷入微服务碎片化。

本设计采用的基本取向是：

`独立 P4 backend service + 服务内强分域 + 后续可拆微服务`

它要解决三个问题：

- `P4` 内部到底有哪些域
- 各域之间通过什么接口协作
- `P3 / P5 / P1 / 前端` 分别应看到什么边界

## 2. 服务总边界

未来独立的 `P4 backend service` 对外应只承担与工具资产相关的职责：

- 接收外部工具需求
- 管理工具资产
- 推进未命中项研制
- 执行工具池自演进巡检
- 提供查询、供给和审计能力

不承担：

- `P1` 的知识解析、治理与图谱存储
- `P3` 的设计生成逻辑
- `P5` 的构建执行逻辑
- 跨全厂的通用任务调度

## 3. 分域设计

建议把 `P4 backend service` 内部固定为 6 个域。

### 3.1 Registry Domain

职责：

- 管理 `ToolDefinition`
- 管理工具分类、标签、形态、平台、生命周期阶段
- 管理验证态和获取清单

拥有的事实对象：

- `ToolDefinition`
- `ToolVerification`
- `ToolFetchManifest`

对外接口：

- 工具创建、更新、删除
- 工具详情查询
- 工具列表查询
- 工具获取清单查询

不拥有：

- 工单审定过程
- 巡检任务状态

### 3.2 Demand Domain

职责：

- 接收 `P3 / P3-sim` 输入
- 管理 `ToolDemandSheet`
- 管理 `ToolDemandItem`
- 管理审定动作与生命周期事件

拥有的事实对象：

- `ToolDemandSheet`
- `ToolDemandItem`
- `ToolDemandLifecycleEvent`

对外接口：

- 创建需求单
- 查询整单
- 查询叶子项
- 撤销需求单
- 驳回需求单
- 审定叶子项

不拥有：

- 工具资产本体
- 自演进规则和任务

### 3.3 Manufacture Domain

职责：

- 接管未命中项的研制推进
- 管理研制计划、进度与完成结果

拥有的事实对象：

- `ToolManufacturePlan`
- 研制推进日志
- 预计完成时间

对外接口：

- 制造计划查询
- 叶子项进度视图
- 完成结果绑定

不拥有：

- 需求树结构
- 巡检任务

### 3.4 Evolution Domain

职责：

- 管理巡检配置
- 生成巡检轮次
- 管理发现项与内部任务
- 执行自动改写与回退

拥有的事实对象：

- `EvolutionInspectionConfig`
- `EvolutionRun`
- `EvolutionFinding`
- `EvolutionTask`
- `EvolutionChangeSet`
- `EvolutionRollbackRecord`

对外接口：

- 配置读取/更新
- 手动触发巡检
- 轮次查询
- 发现项决策
- 任务查询
- 回退操作

不拥有：

- 外部需求单
- 工具真实研发流程

### 3.5 Runtime Domain

职责：

- 管理后台任务和调度
- 管理租约、重试、恢复、超时处理

拥有的事实对象：

- `RuntimeJob`
- `RuntimeLease`
- `RuntimeExecutionRecord`

对外接口：

- 只对内部 worker 暴露
- 不对 `P3 / P5 / 前端` 直接开放

### 3.6 Query Projection Domain

职责：

- 提供页面与外部系统查询所需的只读投影
- 提供概览、卡片、列表、进度和供给视图

拥有的对象：

- `OverviewProjection`
- `DemandQueryProjection`
- `RegistryProjection`
- `EvolutionWorkspaceProjection`
- `P5DeliveryProjection`

对外接口：

- `XX-P4` 的总览与工作区查询
- `P5` 的整单、叶子项和获取清单查询

## 4. 对外端口设计

未来 `P4 backend service` 对外建议只保留 4 类端口。

### 4.1 `P3 Input Port`

给 `P3 / P3-sim` 使用。

允许：

- 创建需求单
- 撤销需求单
- 查询受理状态

禁止：

- 直接操作工具仓
- 直接操作研制任务
- 直接操作巡检配置

### 4.2 `P5 Query Port`

给 `P5 / P5-sim` 使用。

允许：

- 查询整单状态
- 查询叶子项进度
- 查询工具获取信息
- 查询预计完成时间

禁止：

- 改变内部推进状态
- 驱动研制执行
- 修改巡检任务

### 4.3 `Operator Port`

给 `XX-P4` 和未来人工运营工作台使用。

允许：

- 管理工具仓
- 审定工单项
- 配置巡检
- 采纳/忽略发现项
- 回退自动改写
- 查看审计记录

### 4.4 `Internal Runtime Port`

给内部 worker 和调度器使用。

允许：

- 领取任务
- 续租任务
- 提交完成/失败
- 触发投影刷新

不允许对外部系统开放。

## 5. 跨域协作规则

### 5.1 命令与查询分离

各域对外暴露命令接口和查询接口，但命令不能穿透写其他域的底层数据。

### 5.2 通过事实对象协作，不通过页面状态协作

例如：

- `Demand Domain` 审定通过后，生成 `Manufacture Domain` 可消费的研制计划
- `Evolution Domain` 自动改写后，更新 `Registry Domain` 的工具定义
- `Registry Domain` 变化后，触发 `Query Projection Domain` 刷新

### 5.3 通过内部事件或任务协作

建议内部协作统一使用：

- 领域事件
- 后台任务

而不是：

- 页面回调
- 控制器互调
- 跨域直接写文件/表

## 6. 域接口建议

### 6.1 Registry Domain Command

- `CreateTool`
- `UpdateTool`
- `DeleteTool`
- `ArchiveTool`
- `ApplyToolMetadataPatch`

### 6.2 Registry Domain Query

- `GetTool`
- `ListTools`
- `GetToolFetchManifest`

### 6.3 Demand Domain Command

- `CreateDemandSheet`
- `WithdrawDemandSheet`
- `RejectDemandSheet`
- `ReviewDemandItem`

### 6.4 Demand Domain Query

- `GetDemandSheet`
- `ListDemandSheets`
- `GetDemandItem`

### 6.5 Manufacture Domain Command

- `CreateManufacturePlan`
- `AdvanceManufacturePlan`
- `CompleteManufacturePlan`

### 6.6 Manufacture Domain Query

- `ListManufacturePlans`
- `GetDemandItemProgress`

### 6.7 Evolution Domain Command

- `UpdateEvolutionConfig`
- `RunEvolutionScan`
- `DecideEvolutionFinding`
- `RollbackEvolutionTask`

### 6.8 Evolution Domain Query

- `GetEvolutionConfig`
- `ListEvolutionRuns`
- `GetEvolutionRun`
- `ListEvolutionTasks`
- `GetEvolutionTask`

## 7. 与 `P1 / P3 / P5` 的服务边界

### 7.1 `P1 -> P4`

`P4` 只能消费标准知识出口。

建议固定为：

- 已发布知识摘要
- 实体列表
- 事件列表
- 流程列表
- 单项详情
- 图谱查询
- 搜索
- 冻结快照

### 7.2 `P3 -> P4`

`P3` 只向 `P4` 提交标准需求对象。

不得：

- 直接写 `P4` 内部状态
- 越过 `P4` 工具资产规则

### 7.3 `P4 -> P5`

`P4` 只向 `P5` 提供：

- 查询接口
- 获取接口
- 预计时间

不替 `P5` 创建自己的任务，不接管 `P5` 的执行节奏。

## 8. 服务部署形态建议

第一阶段建议部署为：

- `p4-api`
- `p4-worker`
- `p4-db`
- `p4-queue`

必要时补：

- `p4-object-store`

这里的重点是**先分角色部署，再决定是否拆微服务**。

## 9. 未来可拆分路径

当以下条件同时出现时，再考虑把 `P4 backend service` 拆成多个服务：

- 单一服务发布频率已明显受阻
- 单域流量或资源消耗远高于其他域
- 团队组织已经按域稳定分工
- 任务队列、审计和数据契约已稳定

优先拆分顺序建议：

1. `runtime service`
2. `evolution service`
3. `manufacture service`

`registry` 与 `demand` 可继续留在主服务更久。

## 10. 与当前代码的对应关系

当前代码中，`ToolHubService` 同时承担了多个域职责。

未来建议的重构方向不是重写接口，而是：

- 先把服务层逻辑拆成分域 service
- 再把后台运行剥离到独立 worker
- 最后再决定是否拆成多个服务

## 11. 验收标准

本设计完成后，应能明确回答：

- `P4` 内部到底有哪些域
- 每个域拥有哪类事实对象
- `P3 / P5 / XX-P4 / worker` 分别应该访问哪个端口
- 哪些接口是对外稳定契约
- 未来若拆微服务，先拆什么、为什么

