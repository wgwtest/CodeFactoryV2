# P3 Design Lab v2 设计

> 归档说明：本文件同步自 `docs/superpowers/specs/2026-05-01-p3-design-lab-v2-design.md`，用于沉淀 `P3 v2` 独立 Lab 的正式设计口径。
>
> 维护规则：后续若对 `P3 v2` 的输入契约、页面布局、对象模型、服务边界或与旧 `P3` 流程的关系作出确认性修改，必须同步回写本文件。

**日期：** 2026-05-01

## 1. 设计定位

`P3 Design Lab` 是 `P3 v2` 的独立原理验证台，目标是验证：

```text
P2 新版 authoring 冻结包 -> 软件设计说明 -> 结构化设计基线 -> P4 工单投影
```

它不替换旧 `/xx-p3`，也不继续沿用旧 `P3` 以订单、审批和流程状态为中心的页面组织方式。

旧 `/xx-p3` 可保留为历史流程面；`P3 Design Lab` 负责重新建立“虚规到软设”的核心能力。

## 2. 输入契约

`P3 v2` 只消费 `P2` 新版 authoring 冻结包。

正式输入必须满足：

- `frozen_package.p3_consumable = true`
- 包含标准需求规格说明正文
- 包含结构化 `RequirementSpec`
- 包含条款批注、来源追溯、缺口检查结果或等价审计信息

明确禁止：

- 不兼容旧 `/requirements/specs`
- 不写旧 `RequirementSpec` 到新版冻结包的适配器
- 不在 `P3 v2` 页面中暴露“旧规格池接入”“历史样例兼容”等分支
- 不让旧 `XX-P2-Sim` 或旧规格池成为新版 Lab 的输入来源

## 3. 页面结构

`P3` 的核心关系是：

```text
需求规格说明正文 -> 软件设计说明正文
```

自然语言交互不是 `P3` 的主输入本体，而是转换配置、补充判断和输出校正通道。

首版页面采用三块区域：

1. 左上：需求规格说明
   - 展示 `P2` 冻结包中的标准需求规格说明正文
   - 只读
   - 支持章节和条款定位
   - 支持查看条款批注、来源追溯和 `P3` 映射提示
2. 左下：自然语言配置 / CLI
   - 用于调整设计生成策略
   - 用于补充架构偏好、模块粒度、技术约束和输出风格
   - 用于发起“细化模块”“重生成本节”“保守一点”“增加接口说明”等短指令
3. 右侧：软件设计说明
   - 展示实时生成的软件设计说明正文
   - 作为页面视觉主产物，占最大展示权重
   - 支持章节草稿、设计批注、完整性检查和冻结预览

首版比例建议：

- 左侧整体约 `38%`
- 右侧整体约 `62%`
- 左侧内部：需求规格说明约 `70%`，CLI 约 `30%`

## 4. 核心对象

### 4.1 `P3DesignInputPackage`

来自 `P2` authoring 冻结包的输入包装。

最小字段：

- `input_package_id`
- `source_document_id`
- `source_title`
- `standard_document`
- `structured_spec`
- `annotations`
- `knowledge_binding`
- `frozen_at`
- `p3_consumable`

### 4.2 `P3DesignSession`

一次虚规到软设的设计会话。

最小字段：

- `session_id`
- `input_package_id`
- `design_template_id`
- `orchestrator`
- `provider`
- `generation_policy`
- `design_baseline`
- `design_document`
- `workorder_projection`
- `turns`
- `status`

### 4.3 `P3DesignTurn`

一次自然语言配置、校正或局部重生成请求。

最小字段：

- `turn_id`
- `session_id`
- `user_input`
- `normalized_intent`
- `source_clause_refs`
- `target_design_sections`
- `assistant_message`
- `quick_options`
- `design_patch`
- `validation_result`
- `created_at`

### 4.4 `SoftwareDesignBaseline v2`

`P3 v2` 的后台权威状态，至少支撑：

- 软件设计说明正文
- 架构与模块分解
- 接口、数据、状态、部署约束
- 需求到设计的追溯映射
- 设计批注和待确认项
- 完整性检查结果
- `P4` 模块工单投影

## 5. 服务边界

建议新增 `software-design-v2` 服务边界，不把核心能力继续塞进旧 `SoftwareDesignService` 的订单流程中。

最小 API：

```text
GET /api/software-design-v2/input-packages
POST /api/software-design-v2/sessions
GET /api/software-design-v2/sessions/{session_id}
POST /api/software-design-v2/sessions/{session_id}/generate
POST /api/software-design-v2/sessions/{session_id}/turns
POST /api/software-design-v2/sessions/{session_id}/check
```

首版可以使用 `Mock Provider`，但对象、API 和页面必须按真实模型调用协议设计。

## 6. 与旧 P3 的关系

旧 `P3` 能力保留为历史流程面：

- `P3Order`
- 审批通过 / 驳回
- 评审线程
- 冻结动作
- 批次工单包生成
- 推送 `P4`

后续若要把审批流接回新版，应作为侧线接入：

```text
P3 v2 Design Baseline 冻结预览
  -> 发起评审 / 审批
  -> 正式冻结
  -> 下发 P4 工单包
```

这个接入动作必须以 `P3 v2` 的 `SoftwareDesignBaseline v2` 为事实源。

## 7. 验收口径

`P3 Design Lab` 首版验收至少覆盖：

1. 页面入口 `/p3-design-lab` 独立可达。
2. 输入列表只显示 `P2` 新版 authoring 冻结包，不显示旧 `/requirements/specs`。
3. 可选择一个 `p3_consumable=true` 的冻结包创建设计会话。
4. 左上显示需求规格说明正文和条款信息。
5. 左下可输入自然语言配置或短指令。
6. 右侧能生成软件设计说明正文骨架和至少一个设计章节。
7. 后台保存结构化设计基线。
8. 设计基线可投影出 `P4` 工单包预览。
9. 页面不出现旧规格池兼容入口。
10. 旧 `/xx-p3` 不因新增 Lab 被破坏。

## 8. 设计结论

`P3 v2` 的第一步是建立独立 `P3 Design Lab`，把“虚规到软设”的核心转换能力验证清楚。

首版采用：

- 独立路由：`/p3-design-lab`
- 独立服务：`software-design-v2`
- 输入契约：只消费 `P2` 新版 authoring 冻结包
- 兼容策略：不兼容旧 `/requirements/specs`
- 页面布局：左上虚规、左下 CLI、右侧软设正文
- 输出目标：软件设计说明、结构化设计基线、`P4` 工单投影同源生成

