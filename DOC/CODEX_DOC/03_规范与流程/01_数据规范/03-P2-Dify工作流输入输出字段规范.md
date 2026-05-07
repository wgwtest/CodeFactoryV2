# P2 Dify 工作流输入输出字段规范

> 归档说明：本文件作为 `P2` Dify workflow 型组织器的共享字段规范。凡涉及 `P2` adapter 调用 Dify Workflow API、向 Dify 传入变量、从 Dify 输出映射回组织器插件合同，均以本文件为统一约束来源。
>
> 维护规则：修改 Dify 输入变量名、输出 JSON 字段名或 adapter 映射规则时，必须同步更新本文件和对应组织器专项搭建规范。

**日期：** 2026-05-07

**适用范围：**

- `plugin_type = dify_workflow` 的组织器插件
- `brainstorm-v1-dify-workflow`
- 后续新增的 Dify workflow 型组织器

## 1. 规范定位

本规范只约束 `P2` 与 Dify workflow 之间的字段交换，不约束 Dify 内部节点数量、Prompt 内容和模型选择。不同组织器可以有不同工作流理念，但必须遵守本文件定义的输入输出边界。

## 2. 调用模式

当前开发分两阶段：

1. **本地 Dify-shaped workflow**
   - 插件目录内保留 `workflow.json`。
   - adapter 本地执行 workflow 形态，用于验证字段合同和页面挂载。
   - 不要求安装 Dify。

2. **真实 Dify Workflow API**
   - adapter 将输入映射为 Dify `inputs`。
   - Dify 返回结构化 JSON。
   - adapter 将 Dify 输出归一化为 `OrchestratorRunResult`。

Dify 官方 Workflow 运行接口使用 `POST /workflows/run`，请求体包含 `inputs`、`response_mode`、`user` 等字段，鉴权使用 `Authorization: Bearer {API_KEY}`。Workflow 需要发布后才能通过 API 调用。官方文档见：<https://docs.dify.ai/api-reference/workflows/run-workflow>。

## 3. Dify 输入变量

所有 Dify workflow 型组织器应优先使用以下输入变量名。

| 变量 | 类型 | 必填 | 来源 | 含义 |
| --- | --- | --- | --- | --- |
| `user_input` | string | 是 | `turn.user_input` | 用户原始输入 |
| `normalized_input_json` | string | 是 | `turn.normalized_input` | 输入归一化 JSON 字符串 |
| `topic` | string | 是 | `session.topic` | 当前需求分析主题 |
| `template_id` | string | 是 | `session.template_id` | 模板 ID |
| `template_content` | string | 否 | `template.content` | 模板正文 |
| `template_structure_json` | string | 是 | `template.parsed_structure` | 模板解析结构 JSON |
| `active_spec_node_json` | string | 是 | `document_context.active_spec_node` | 当前活动规格节点 |
| `spec_tree_json` | string | 是 | `document_context.spec_tree` | 规格完成度树 |
| `working_document_json` | string | 是 | `document_context.working_document` | Lab 临时正文 |
| `decision_state_json` | string | 否 | `document_context.state.decision_state` | 结构化决策状态 |
| `previous_interaction_json` | string | 否 | `turn.previous_interaction` | 上一轮交互 |
| `input_relation_json` | string | 否 | `turn.input_relation` | 本轮输入关系 |
| `confirmed_facts_json` | string | 否 | `document_context.confirmed_facts` | 已确认事实 |
| `open_questions_json` | string | 否 | `document_context.open_questions` | 未闭合问题 |
| `history_summary` | string | 否 | `document_context.history_summary` | 历史摘要 |
| `write_policy` | string | 是 | `session.write_policy` | 写入策略 |
| `expected_output` | string | 否 | `execution_options.expected_output` | 期望输出类型 |

### 3.1 JSON 字符串约定

Dify 输入变量对复杂对象的支持随版本和节点配置变化。为降低耦合，复杂对象统一以 JSON 字符串传入：

- 变量名以 `_json` 结尾。
- 内容必须是 UTF-8 JSON。
- Dify 节点内如需读取字段，可先用代码节点解析。

## 4. Dify 输出 JSON

Dify workflow 应返回一个可解析的 JSON 对象。推荐字段如下：

| 字段 | 类型 | 必填 | 映射目标 |
| --- | --- | --- | --- |
| `assistant_message` | string | 是 | `interaction_output.assistant_message` |
| `next_question` | string | 是 | `interaction_output.next_question` |
| `quick_options` | array | 是 | `interaction_output.quick_options` |
| `filled_document_text` | string | 是 | `final_output.filled_document_text` |
| `document_patch` | array | 是 | `final_output.document_patch` |
| `changed_sections` | array | 是 | `final_output.changed_sections` |
| `completion_status` | string | 是 | `final_output.completion_status` |
| `confidence` | string | 是 | `final_output.confidence` |
| `confirmed_facts_delta` | array | 是 | `state_output.confirmed_facts_delta` |
| `open_questions_delta` | array | 是 | `state_output.open_questions_delta` |
| `decision_state_delta` | object | 否 | `state_output.decision_state_delta` |
| `decision_state_document` | object | 否 | `state_output.decision_state_document` |
| `decision_trace` | array | 是 | `process_output.decision_trace` |
| `annotations` | array | 是 | `process_output.annotations` |
| `risks` | array | 是 | `process_output.risks` |
| `raw_workflow_trace` | object | 否 | `raw_output.raw_workflow_trace` |

## 5. document_patch 结构

`document_patch` 每项至少包含：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `plan_ref` | 是 | 对应 anchor plan 的 ID |
| `operation` | 是 | 建议使用 `append_or_update` |
| `content` | 是 | 要补入 Lab 临时正文的内容 |
| `write_policy` | 是 | 写入策略 |

如果 Dify 同时返回 `target_anchor_plan`，adapter 应优先使用 Dify 返回的计划；否则 adapter 使用当前活动规格节点生成默认 anchor plan。

## 6. decision_state_delta 结构

对支持 Brainstorm 或决策状态闭环的 Dify 组织器，`decision_state_delta` 推荐结构如下：

```json
{
  "confirmed_facts": [],
  "confirmed_decisions": [],
  "tentative_assumptions": [],
  "open_questions": [],
  "rejected_directions": [],
  "chapter_projections": [],
  "next_focus": ""
}
```

其中数组项推荐结构：

```json
{
  "item_id": "DS-F-001",
  "content": "事实或决策内容",
  "source_turn_id": "turn-0001",
  "target_section": "1 总则 / 编写目的",
  "status": "active"
}
```

## 7. Adapter 映射规则

adapter 必须执行以下映射：

| Dify 输出 | 组织器合同目标 |
| --- | --- |
| `assistant_message` | `interaction_output.assistant_message` |
| `next_question` | `interaction_output.next_question` |
| `quick_options` | `interaction_output.quick_options` |
| `filled_document_text` | `final_output.filled_document_text` |
| `document_patch` | `final_output.document_patch` |
| `changed_sections` | `final_output.changed_sections` |
| `decision_trace` | `process_output.decision_trace` |
| `annotations` | `process_output.annotations` |
| `risks` | `process_output.risks` |
| `confirmed_facts_delta` | `state_output.confirmed_facts_delta` |
| `open_questions_delta` | `state_output.open_questions_delta` |
| `decision_state_delta` | `state_output.decision_state_delta` |
| `raw_workflow_trace` | `raw_output.raw_workflow_trace` |

如果 Dify 输出缺少可选字段，adapter 可以填充空数组或空对象；如果缺少必填字段，adapter 应判定响应不合格。

## 8. 错误和降级

真实 Dify 调用失败时，推荐策略：

- 网络、鉴权、超时失败：返回明确 API 错误，不伪造成功结果。
- Dify 返回非 JSON 或字段缺失：记录原始响应，返回结构校验错误。
- 如果插件 manifest 声明支持本地 fallback，adapter 可降级到本地 `workflow.json`，但必须在 `annotations` 和 `raw_workflow_trace` 中标注。

## 9. 配置项

真实 Dify 接入时不得在代码或文档中写入真实密钥。推荐环境变量：

| 变量 | 含义 |
| --- | --- |
| `DIFY_BASE_URL` | Dify 服务地址 |
| `DIFY_API_KEY` | Dify API Key |
| `DIFY_WORKFLOW_ID` | 工作流或应用标识 |
| `DIFY_RESPONSE_MODE` | `blocking` 或 `streaming` |
| `DIFY_TIMEOUT_SECONDS` | 请求超时 |

## 10. 验收标准

Dify workflow 型组织器完成联调至少满足：

- 插件能在 `/api/requirement-analysis/orchestrators` 中列出。
- 使用该插件创建会话成功。
- 输入一段用户文本后，返回 `assistant_message`、`document_patch`、`next_question`。
- Dify 原始 trace 或 run id 能进入 `raw_output.raw_workflow_trace`。
- 缺少 Dify 配置时，系统行为符合插件声明的 fallback 或错误策略。
