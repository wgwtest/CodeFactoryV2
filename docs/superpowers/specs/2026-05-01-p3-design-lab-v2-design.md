# P3 Design Lab v2 设计

**日期：** 2026-05-01

**对应节点：**
- `P3` 软件设计系统
- `P3 v2` 需规到软设核心能力原理验证
- `P3 Design Lab`

## 1. 设计背景

当前 `P3` 已经形成订单、审批、评审、冻结和推送 `P4` 的流程外壳，但核心能力偏向工作流，尚未充分验证“需求规格说明到软件设计说明”的正文生成、设计基线沉淀和工单投影能力。

`P2` 最新设计已经从旧的结构化建模器升级为“可配置标准需求规格说明编写系统”。其成功经验不是业务上自然承接 `P3`，而是产品和实现方法：

- 专家正面工作对象是标准文档。
- 交互输入、表单校对、正文、批注和检查共享同一个后台语义状态。
- 独立 Lab 先验证核心组织器能力，验证通过后再并入正式工作台。
- 模拟器和 Lab 不污染正式编辑器主路径。

`P3 v2` 应按同样策略重构：先建立独立 `P3 Design Lab`，集中验证“P2 冻结需求规格说明包 -> 软件设计说明 -> 结构化设计基线 -> P4 工单投影”的核心链路。

## 2. 核心结论

首版新增独立页面：

```text
/p3-design-lab
```

该页面是 `P3 v2` 的原理验证台，不替换旧 `/xx-p3`。

旧 `/xx-p3` 可以保留为历史流程面，继续展示订单、审批、评审、冻结和推送流程；但它不参与 `P3 v2` 输入契约，不为 `P3 v2` 提供兼容路径，也不继续定义新版软件设计编制体验。

## 3. 输入契约

`P3 v2` 只消费 `P2` 新版 authoring 冻结包。

正式输入必须满足：

- 来源为 `P2` 新版需求规格编写系统的冻结文档。
- `frozen_package.p3_consumable` 为 `true`。
- 包含标准需求规格说明正文。
- 包含结构化 `RequirementSpec`。
- 包含条款批注、来源追溯、缺口检查结果或等价审计信息。

明确禁止：

- 不兼容旧 `/requirements/specs`。
- 不写旧 `RequirementSpec` 到新版冻结包的适配器。
- 不在 `P3 v2` 页面中暴露“旧规格池接入”“历史样例兼容”等分支。
- 不让旧 `XX-P2-Sim` 或旧规格池成为新版 Lab 的输入来源。

如需保留旧样例，只能留在旧 `/xx-p3` 或历史回归测试中，不进入 `P3 v2` 设计。

## 4. 页面主关系

`P3` 与 `P2` 的界面逻辑不同。

`P2` 的核心关系是：

```text
交互式问答 / 表单输入 -> 需求规格说明正文
```

因此 `P2` 使用左侧问答 / 表单、右侧需求规格正文的布局。

`P3` 的核心关系是：

```text
需求规格说明正文 -> 软件设计说明正文
```

自然语言交互仍然重要，但它不是 `P3` 的主输入本体，而是用于配置转换策略、补充缺失判断、校正输出方向和触发局部重生成的控制通道。

因此 `P3 Design Lab` 首版采用三块区域：

1. 左上：需求规格说明
   - 展示 `P2` 冻结包中的标准需求规格说明正文。
   - 只读。
   - 支持章节和条款定位。
   - 支持查看条款批注、来源追溯和 `P3` 映射提示。
2. 左下：自然语言配置 / CLI
   - 用于填写或调整设计生成策略。
   - 用于补充架构偏好、模块粒度、技术约束、输出风格。
   - 用于发起“细化模块”“重生成本节”“保守一点”“增加接口说明”等短指令。
   - 用于展示 `Design Turn` 的助手回复、轻量选项和待确认问题。
3. 右侧：软件设计说明
   - 展示实时生成的软件设计说明正文。
   - 作为页面视觉主产物，占最大展示权重。
   - 支持章节草稿、设计批注、完整性检查、冻结预览。
   - 后续从同一结构化设计基线投影出 `P4` 工单包。

首版比例建议：

- 左侧整体约 `38%`
- 右侧整体约 `62%`
- 左侧内部：需求规格说明约 `70%`，CLI 约 `30%`

## 5. Lab 对象模型

首版至少定义以下对象概念。

### 5.1 `P3DesignInputPackage`

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

### 5.2 `P3DesignSession`

一次需规到软设的设计会话。

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

状态建议：

```text
created
  -> generating
  -> waiting_user
  -> patch_ready
  -> baseline_ready
  -> frozen_preview
  -> archived
```

### 5.3 `P3DesignTurn`

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

### 5.4 `P3DesignPatch`

`Design Turn` 产生的结构化修补意图。

至少覆盖：

- 软件设计说明章节补丁
- 模块划分补丁
- 接口 / 数据 / 状态补丁
- 约束和风险补丁
- 需求条款到设计条款的映射补丁
- `P4` 工单投影补丁

### 5.5 `SoftwareDesignBaseline v2`

`P3 v2` 的后台权威状态。

它不只是旧版模块列表，而应同时支撑：

- 软件设计说明正文
- 架构与模块分解
- 接口、数据、状态、部署约束
- 需求到设计的追溯映射
- 设计批注和待确认项
- 完整性检查结果
- `P4` 模块工单投影

## 6. 服务边界

建议新增 `P3 Design Lab Service`，不要把核心能力继续塞进旧 `SoftwareDesignService` 的订单流程中。

最小 API 形态：

```text
GET /api/software-design-v2/input-packages
列出可被 P3 v2 消费的 P2 冻结包

POST /api/software-design-v2/sessions
基于一个 P2 冻结包创建设计会话

GET /api/software-design-v2/sessions/{session_id}
读取并恢复设计会话

POST /api/software-design-v2/sessions/{session_id}/generate
执行初始“需规 -> 软设”生成

POST /api/software-design-v2/sessions/{session_id}/turns
提交自然语言配置或校正，返回 Design Turn 与 Design Patch

POST /api/software-design-v2/sessions/{session_id}/check
执行设计完整性、追溯和工单投影检查
```

首版可以使用 `Mock Provider`，但对象、API 和页面必须按真实模型调用协议设计。

## 7. 与旧 P3 的关系

旧 `P3` 能力保留为历史流程面：

- `P3Order`
- 审批通过 / 驳回
- 评审线程
- 冻结动作
- 批次工单包生成
- 推送 `P4`

但 `P3 v2` 不把这些能力作为首屏中心。

后续若要把审批流接回新版，应作为侧线接入：

```text
P3 v2 Design Baseline 冻结预览
  -> 发起评审 / 审批
  -> 正式冻结
  -> 下发 P4 工单包
```

这个接入动作必须以 `P3 v2` 的 `SoftwareDesignBaseline v2` 为事实源，而不是把新版 Lab 产物反向塞进旧订单模型。

## 8. 首版验收口径

`P3 Design Lab` 首版验收应至少覆盖：

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

## 9. 设计结论

`P3 v2` 的第一步不是继续扩展审批流，而是建立 `P3 Design Lab`，把“需规到软设”的核心转换能力独立验证清楚。

首版采用：

- 独立路由：`/p3-design-lab`
- 独立服务：`software-design-v2`
- 输入契约：只消费 `P2` 新版 authoring 冻结包
- 兼容策略：不兼容旧 `/requirements/specs`
- 页面布局：左上需规、左下 CLI、右侧软设正文
- 输出目标：软件设计说明、结构化设计基线、`P4` 工单投影同源生成

## 10. 局部沟通与补丁提案补充设计

本节是对 `P3 Design Lab v2` 的补充约定，解决“初版软设生成完成后，针对局部段落继续沟通并形成补丁提案”的场景。

### 10.1 设计目的

局部沟通工作流的目标不是重新启动整份软设转换，而是在已有软件设计说明草稿基础上，针对选中章节、段落或功能对象进行补充修正、重写建议和映射补齐。

它必须满足以下原则：

- 只处理局部修正，不替代初版需规转软设流程。
- 输出补丁提案和解释信息，不直接把正文写成最终态。
- 与 Dify 工作流解耦，CodeFactory 只负责调用约定和结果归一化，不负责编辑 Dify 内部实现。
- 保持和现有 `P3DesignTurn` / `P3DesignPatch` 结构兼容。

### 10.2 工作流边界

局部修正入口继续复用同一个会话 API：

```text
POST /api/software-design-v2/sessions/{session_id}/turns
```

当 `turn_type = scoped_design_edit` 时，后端优先进入“局部沟通与补丁提案”分支。

初版转换路径保持不变：

- `POST /api/software-design-v2/sessions/{session_id}/conversion`
- 仍然负责从 `P2` 冻结包生成初版软设、设计基线和工单投影。

普通回合路径也保持不变：

- `turn_type = design_turn`
- 继续使用现有的轻量本地补充逻辑，作为非局部修正的常规设计回合。

### 10.3 Dify 接入协议

局部沟通工作流对应独立的 Dify 执行单元，建议使用以下环境变量：

```bash
CODEFACTORY_P3_SCOPED_DIFY_BASE_URL=http://localhost/v1
CODEFACTORY_P3_SCOPED_DIFY_API_KEY=<Dify Console 中复制的 App API Key>
CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=f2413e20-7cfc-4188-ae7f-7c23eaa353ff
CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS=180
```

约定：

- `BASE_URL` 只表示 Dify API 根地址，不把工作流运行逻辑写死在 CodeFactory。
- `API_KEY` 必须是 Dify Console 的 App API Key，不使用内部 `api_key_id`。
- `WORKFLOW_ID` 只用于固定某个发布版本；如果没有配置，允许走默认发布工作流路径。
- `TIMEOUT_SECONDS` 默认建议 `180`，局部修正通常不需要比初版生成更长的等待。
- 远端输出变量统一读取 `result_json`。

### 10.4 输入与输出

局部沟通工作流的输入应至少包含：

- 当前 `session_id`
- 当前软设标题和版本标识
- 当前 `scope_anchor`
- 用户本轮输入
- 当前设计正文摘要
- 当前设计基线摘要
- 相关章节或对象上下文
- `expected_output`

输出在 CodeFactory 侧归一化为现有 turn 结构，至少保留：

- `turn_id`
- `turn_type`
- `normalized_intent`
- `assistant_message`
- `scope_anchor`
- `patch_proposal`
- `context_receipt`
- `provider_call_audit`
- `created_at`

其中：

- `patch_proposal` 表示局部修正建议，不直接等于最终正文。
- `context_receipt` 记录本轮调用时带入了哪些上下文。
- `provider_call_audit` 记录本轮由哪个 provider / workflow 生成，便于排障。

### 10.5 运行策略

推荐策略是“优先 Dify，缺省回退本地”：

1. 当局部 Dify 配置完整且工作流可用时，后端调用 Dify 生成补丁提案。
2. 当局部 Dify 配置缺失时，保留现有本地补丁提案逻辑，保证页面可运行。
3. 当远端返回缺少 `result_json`、JSON 非法、或 workflow 执行失败时，后端返回明确错误，不悄悄改成另一条初版转换路径。

这样可以保证：

- 初版软设生成和局部修正完全解耦。
- 局部修正不会反向污染初版转换器协议。
- CodeFactory 的接口形状对前端保持稳定。

### 10.6 验收口径

本补充设计完成后，至少要满足：

1. `scoped_design_edit` 可以独立触发局部补丁提案。
2. 新增 Dify 工作流只影响局部修正，不影响初版转换。
3. `result_json` 是局部工作流的唯一远端输出读取点。
4. `patch_proposal` 继续以结构化对象形式返回。
5. 会话页不需要知道 Dify 的内部编排细节。
6. 未配置局部 Dify 时，页面仍可用本地逻辑回退。
