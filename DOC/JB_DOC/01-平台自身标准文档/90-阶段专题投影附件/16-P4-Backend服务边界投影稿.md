# P4 Backend 服务边界投影稿

## 1. 文档定位

**文档类别：** 标准化投影文档  
**标准依据：** 主要服务平台设计说明中的服务边界专题补充，不直接对应单一军标原件  
**当前状态：** 候选  
**主要来源文档：**

- `DOC/CODEX_DOC/02_设计说明/08-P4-Backend服务边界设计.md`

## 2. 投影目标

本专题用于把未来 `P4 backend service` 的边界固定清楚，使其既可独立部署，又不提前陷入微服务碎片化。

基本取向为：

`独立 P4 backend service + 服务内强分域 + 后续可拆微服务`

## 3. 服务总边界

未来独立的 `P4 backend service` 对外只承担与工具资产相关的职责：

- 接收外部工具需求
- 管理工具资产
- 推进未命中项研制
- 执行工具池自演进巡检
- 提供查询、供给和审计能力

明确不承担：

- `P1` 的知识解析、治理与图谱存储
- `P3` 的设计生成逻辑
- `P5` 的构建执行逻辑
- 跨全厂通用任务调度

## 4. 分域设计投影

当前已建议固定 6 个域：

- `Registry Domain`
- `Demand Domain`
- `Manufacture Domain`
- `Evolution Domain`
- `Projection Domain`
- `Runtime Domain`

各域应在服务内强分域，但对外仍维持统一 `P4 backend service` 边界。

## 5. 端口与外部视角

当前外部视角已经明确：

- `P3 / P3-sim`
  - 通过 `P3 Input Port`
- `XX-P4 / Operator`
  - 通过 `Operator Port`
- `Worker / Runtime Coordinator`
  - 通过 `Internal Runtime Port`
- `P5 / P5-sim`
  - 通过 `P5 Query Port`

这种划分的意义是：

- 把命令、操作、内部推进与下游查询分开
- 为后续独立部署保留清晰边界

## 6. 与上下游的边界

### 6.1 与 `P1`

`P1` 只通过标准知识出口、只读 API 或冻结快照与 `P4` 协作。

### 6.2 与 `P3`

`P3` 只向 `P4` 输入冻结后的设计投影与供给目标。

### 6.3 与 `P5`

`P5` 只通过标准查询与获取接口消费 `P4` 结果，不应回写 `P4` 内部状态。

## 7. 当前未纳入投影的缺口声明

本投影稿当前**不补写**以下内容：

- 协议级 endpoint 定义
- request/response 结构
- 错误码表
- 鉴权约束

这些内容已归入 `B1`，应等待正式接口契约文档形成后再补投影。

## 8. 当前结论

`P4 backend service` 的边界、分域和端口视角当前已足够成熟，能够独立进入 `JB_DOC` 作为专题投影说明。
