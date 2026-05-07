# P2 Brainstorm v1 Dify 工作流搭建规范

> 归档说明：本文件作为 `brainstorm-v1-dify-workflow` 在 Dify 工作台中的专项搭建规范。它说明该组织器的理念、节点、输入输出、Prompt 约束和验收标准。
>
> 维护规则：若 `orchestrators/xg/brainstorm-v1-dify-workflow/workflow.json`、adapter 字段映射或 Dify 工作台节点设计发生变化，必须同步回写本文件。

**日期：** 2026-05-07

**关联插件：**

```text
orchestrators/xg/brainstorm-v1-dify-workflow/
```

**插件 ID：**

```text
brainstorm-v1-dify-workflow
```

## 1. 组织器定位

`brainstorm-v1-dify-workflow` 用 Dify workflow 形态实现 Brainstorm v1 的工作理念。它不是简单地把用户输入追加到文档，而是按以下顺序处理：

1. 理解用户输入与需求规格章节的关系。
2. 把讨论内容沉淀为结构化决策状态。
3. 把稳定信息投影为需求规格章节正文补丁。
4. 规划下一轮交互问题。
5. 输出符合 `P2` 组织器插件合同的结构化 JSON。

当前工程中的本地 `workflow.json` 是可运行样板。Dify 工作台中的真实 workflow 应以本文件为准搭建。

## 2. 推荐节点顺序

真实 Dify workflow 推荐包含以下节点：

| 顺序 | 节点 ID | Dify 节点类型 | 职责 |
| --- | --- | --- | --- |
| 1 | `normalize_input` | Start / Code | 读取输入变量，解析 JSON 上下文 |
| 2 | `intent_understanding` | LLM | 判断用户输入、当前章节、上一轮问题之间的关系 |
| 3 | `decision_state_delta` | LLM | 生成 Brainstorm v1 决策状态增量 |
| 4 | `document_projection` | LLM / Code | 将决策状态投影为章节正文补丁 |
| 5 | `next_interaction_planning` | LLM | 规划下一轮问题和快捷选项 |
| 6 | `normalize_output` | Code / End | 组装最终 JSON 输出 |

节点 ID 应尽量保持上述命名，便于 adapter trace、测试和文档对齐。

## 3. 输入变量

必须接收 `03-P2-Dify工作流输入输出字段规范.md` 中定义的公共输入变量。Brainstorm v1 特别依赖：

| 变量 | 用途 |
| --- | --- |
| `user_input` | 本轮事实和补充内容来源 |
| `normalized_input_json` | 判断输入类型和快捷选项关系 |
| `active_spec_node_json` | 决定本轮目标章节 |
| `spec_tree_json` | 判断完成度和下一节点 |
| `working_document_json` | 避免重复写入并支持上下文回看 |
| `decision_state_json` | 延续已确认事实、决策、假设、问题和章节投影 |
| `previous_interaction_json` | 判断本轮是否回答上一轮问题 |
| `input_relation_json` | 影响意图理解和追问策略 |
| `write_policy` | 写入策略，必须带入 `document_patch` |

## 4. 节点输出要求

### 4.1 intent_understanding

输出对象：

```json
{
  "intent_understanding_result": {
    "user_goal_summary": "",
    "input_type": "",
    "relation_to_previous_interaction": "",
    "document_strategy": "decision_state_then_section_projection",
    "target_section_candidates": [],
    "ambiguities": []
  },
  "stage_task_definition": {
    "task_summary": "",
    "target_sections": [],
    "must_output": []
  },
  "confidence": "medium"
}
```

约束：

- 不直接输出最终正文。
- 必须明确当前输入是否可投影到活动章节。
- 若输入无法判断目标章节，应把歧义写入 `ambiguities`。

### 4.2 decision_state_delta

输出对象：

```json
{
  "decision_state_delta": {
    "confirmed_facts": [],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": ""
  },
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "confidence": "medium"
}
```

约束：

- 用户明确说出的事实进入 `confirmed_facts`。
- 组织器根据当前章节做出的工作选择进入 `confirmed_decisions`。
- 不确定但有用的推断进入 `tentative_assumptions`，不得伪装成事实。
- 仍需用户确认的问题进入 `open_questions`。
- 明确否定或排除方向进入 `rejected_directions`。
- 章节落点进入 `chapter_projections`。

### 4.3 document_projection

输出对象：

```json
{
  "target_anchor_plan": [
    {
      "plan_id": "BRAINSTORM-DIFY-AP-001",
      "decision_type": "append_existing_clause",
      "template_clause_id": "REQ-1.1",
      "canonical_clause_heading": "1 总则 / 编写目的",
      "display_heading": "1 总则 / 编写目的",
      "anchor_path": "REQ-1.1",
      "reason": "",
      "confidence": "medium"
    }
  ],
  "document_patch": [
    {
      "plan_ref": "BRAINSTORM-DIFY-AP-001",
      "operation": "append_or_update",
      "content": "",
      "write_policy": "patch_suggestion_only"
    }
  ],
  "filled_document_text": ""
}
```

约束：

- 不新增模板不存在的章节编号。
- 优先使用 `active_spec_node_json` 中的章节作为锚点。
- `document_patch.content` 必须是可进入需求规格说明的正文片段，不是对话解释。
- `assistant_message` 不应混入 `document_patch.content`。

### 4.4 next_interaction_planning

输出对象：

```json
{
  "next_interaction_plan": {
    "planning_strategy": "decision_state_loop",
    "user_message": "",
    "next_question": "",
    "quick_options": [],
    "plan_reason": "",
    "target_spec_nodes": []
  },
  "planning_trace": []
}
```

约束：

- 下一轮问题必须服务于补齐需求规格说明。
- 如果当前章节仍缺关键信息，应继续当前章节。
- 如果当前章节已形成可用正文，可以指向规格树下一个 open 节点。
- 快捷选项应是用户可直接点击的候选事实或选择，不应是操作说明。

### 4.5 normalize_output

最终输出必须是一个 JSON 对象，并满足 `03-P2-Dify工作流输入输出字段规范.md` 的输出字段要求。

## 5. 最终输出示例

```json
{
  "assistant_message": "我已把本轮讨论沉淀为结构化决策状态，并投影到：1 总则 / 编写目的。",
  "next_question": "请先确认软件名称、背景领域和编写目的。",
  "quick_options": [],
  "filled_document_text": "围绕“1 总则 / 编写目的”，本轮已确认：这个系统叫空域运算软件，主要解决空域计算分析需求",
  "document_patch": [
    {
      "plan_ref": "BRAINSTORM-DIFY-AP-001",
      "operation": "append_or_update",
      "content": "围绕“1 总则 / 编写目的”，本轮已确认：这个系统叫空域运算软件，主要解决空域计算分析需求",
      "write_policy": "patch_suggestion_only"
    }
  ],
  "changed_sections": ["1 总则 / 编写目的"],
  "completion_status": "partial",
  "confidence": "medium",
  "confirmed_facts_delta": ["这个系统叫空域运算软件，主要解决空域计算分析需求"],
  "open_questions_delta": ["请先确认软件名称、背景领域和编写目的。"],
  "decision_state_delta": {
    "confirmed_facts": [
      {
        "item_id": "DS-F-001",
        "content": "这个系统叫空域运算软件，主要解决空域计算分析需求",
        "source_turn_id": "turn-0001",
        "target_section": "1 总则 / 编写目的",
        "status": "active"
      }
    ],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": "请先确认软件名称、背景领域和编写目的。"
  },
  "decision_trace": [
    {
      "step": "decision_state_delta",
      "decision": "将用户输入沉淀为 confirmed_facts 与 chapter_projections。"
    }
  ],
  "annotations": [],
  "risks": [],
  "raw_workflow_trace": {
    "workflow_id": "brainstorm-v1-dify-shaped-workflow",
    "run_id": ""
  }
}
```

## 6. Prompt 规则

所有 LLM 节点应遵守：

- 输出 JSON，不输出 Markdown 解释。
- 不编造用户未提供的事实。
- 区分事实、决策、假设、开放问题和否定方向。
- 正文补丁必须贴近需求规格说明风格。
- 追问必须可回答，不能要求用户理解内部实现术语。
- 当模板约束与用户输入冲突时，优先记录风险，不擅自改模板结构。

## 7. Adapter 期望

当前工程 adapter 对该 workflow 的期望：

- 能读取最终 JSON。
- 能拿到 workflow run id 或 trace。
- 能把 `document_patch` 应用到 Lab 临时正文。
- 能把 `decision_state_delta` 和 `decision_state_document` 放入会话状态。
- 当真实 Dify 未配置时，当前本地 `workflow.json` 可继续作为 fallback 样板。

## 8. 验收标准

专项 workflow 完成后至少满足：

- Dify workflow 已发布。
- 输入变量名与本规范一致。
- 输出 JSON 能被 adapter 解析。
- 使用示例输入能生成 `document_patch`。
- 输出中包含 `decision_state_delta.confirmed_facts`。
- 输出中包含 `next_question`。
- 不安装 Dify 时，本地样板插件测试仍通过。
- 接入真实 Dify 后，P2 页面可以选择 `brainstorm-v1-dify-workflow` 并完成一轮会话。
