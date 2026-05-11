# P2 Brainstorm v1 Dify 工作流搭建规范

> 归档说明：本文件作为 `brainstorm-v1-dify-workflow` 在 Dify 工作台中的专项搭建规范。它说明该组织器的理念、节点、输入输出、Prompt 约束和验收标准。
>
> 维护规则：若 `orchestrators/xg/brainstorm-v1-dify-workflow/workflow.json`、adapter 字段映射或 Dify 工作台节点设计发生变化，必须同步回写本文件。

**日期：** 2026-05-07

**最近整改：** 2026-05-10，已发布到 Dify workflow `9f82e359-07e2-4bbd-ae88-8ca0bb7272ef`。

**最近发布信息：**

| 项 | 内容 |
| --- | --- |
| Dify App ID | `e5444ba7-7134-4f0d-9258-fbd5f162e4f1` |
| Published Workflow ID | `9f82e359-07e2-4bbd-ae88-8ca0bb7272ef` |
| Draft hash | `c82ff6a61f2ff7b8453c48b775e15c9c2d2293158542c405766b2f28543581bc` |
| Version | `2026-05-10 13:54:03` |
| Marked name | `P2第3轮草案与回看修复` |
| 主要变更 | 过滤旧完成度树遗留的“组织器策略问题”噪声；增强收束草案章节段落可读性；保留真实待确认项；继续保持当前 81433 模板锚点映射、部署分析功能归类、边界优先软件定位、混合非功能拆分和收束草案 `replace` patch。 |

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
| 1 | `normalize_input` | Start / Code | 读取输入变量，解析 JSON 上下文，派生上一问、上一组选项、已知事实、未闭合问题摘要和 `draft_requested` |
| 2 | `intent_understanding` | LLM | 判断用户输入、当前章节、上一轮问题、成稿请求之间的关系 |
| 3 | `decision_state_delta` | LLM | 生成 Brainstorm v1 候选决策状态增量 |
| 4 | `branch_draft_or_continue` | Code branch | 用户要求停止追问或输出草案时进入草案分支，否则继续章节投影 |
| 5 | `document_projection` | Code | 按事实语义映射章节，生成正文补丁并补齐 `target_section`、`anchor_path` |
| 6 | `draft_compose` | Code | 在收束分支中生成章节化草案，保留未闭合问题 |
| 7 | `next_interaction_planning` | LLM | 规划候选下一轮问题和快捷选项 |
| 8 | `normalize_output` | Code / End | 组装最终 JSON，并校验 quick options、patch、decision state 合同 |

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

`normalize_input` 必须从这些输入中派生：

| 派生字段 | 用途 |
| --- | --- |
| `last_question` | 判断是否回答上一问，避免旧问题机械重复 |
| `last_options` | 支持用户只输入 `A/B/C/D` 时吸收上一轮选项事实 |
| `known_facts` | 草案生成和重复问题收束依据 |
| `open_question_summaries` | 问题关闭、暂挂、草案缺口保留依据 |
| `draft_requested` | 识别“停止追问 / 输出草案 / 先成稿 / 不要继续问”等收束意图 |

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
      "write_policy": "patch_suggestion_only",
      "target_section": "3 功能需求 / 用户与角色",
      "anchor_path": "REQ-3.1"
    }
  ],
  "filled_document_text": ""
}
```

约束：

- 不新增模板不存在的章节编号。
- 不再把所有事实强行写入当前活动章节；必须优先按事实语义映射目标章节。
- 每条 `document_patch` 必须包含 `content`，并尽量包含 `target_section` 与 `anchor_path`。
- `document_patch.content` 必须是可进入需求规格说明的正文片段，不是对话解释。
- `assistant_message` 不应混入 `document_patch.content`。

章节映射规则：

| 事实类型 | 目标章节 | 锚点 |
| --- | --- | --- |
| 软件名称、领域、编写目的 | `1 总则 / 编写目的` | `REQ-1.1` |
| 软件定位、边界、不做范围 | `2 项目概述 / 软件定位` | `REQ-2.1` |
| 用户角色、下游使用者、职责 | `3 功能需求 / 用户与角色` | `REQ-3.1` |
| 核心流程、工具使用主线 | `3 功能需求 / 核心业务流程` | `REQ-3.2` |
| 功能域、主要界面、页面列表、交互入口 | `3 功能需求 / 功能分解总览` | `REQ-3.3` |
| 核心功能项、分析工具、功能行为、部署分析 | `3 功能需求 / 核心功能项说明` | `REQ-3.4` |
| 协同模式、任务接力、批注、结果共享 | `3 功能需求 / 结果输出与共享` | `REQ-3.6` |
| 异常、失败、补偿 | `3 功能需求 / 异常与补偿` | `REQ-3.7` |
| 输入数据、数据接入、底图、DEM、矢量、栅格 | `4 数据需求 / 输入数据` | `REQ-4.1` |
| 输出数据、报表、导出文件 | `4 数据需求 / 输出数据与报表` | `REQ-4.2` |
| 性能、刷新、并发、可靠性 | `5 非功能需求 / 性能与可靠性` | `REQ-5.1` |
| 安全、权限、认证、审计 | `5 非功能需求 / 安全与权限` | `REQ-5.2` |
| 部署环境、内网、专网、离线运行 | `5 非功能需求 / 部署与运行环境` | `REQ-5.3` |
| 精度口径、质量约束、适用限制、结果追溯 | `5 非功能需求 / 精度与质量约束` | `REQ-5.4` |
| 验收链路、验收标准 | `6 验收准则 / 验收准则` | `REQ-6.2` |

投影优先级约束：

- “不做、排除、不承诺、不支持”等边界事实优先进入 `2 项目概述 / 软件定位`，即使同一句中出现“协同、共享、精度”等词。
- “部署分析、部署影响分析、覆盖、冲突、影响分析”属于功能行为，优先进入 `3 功能需求 / 核心功能项说明`；只有“内网部署、专网部署、离线部署、运行环境、部署环境”等运行环境事实进入 `5 非功能需求 / 部署与运行环境`。
- “内网部署、角色权限、操作审计、结果可追溯”这类混合非功能枚举应拆成多个记录，分别投影到部署、安全和质量约束章节。

### 4.4 branch_draft_or_continue 与 draft_compose

触发条件：

- 用户输入包含“停止追问”
- 用户输入包含“输出草案”
- 用户输入包含“先成稿”
- 用户输入包含“不要继续问”
- 用户输入包含其他明确收束成稿表达

触发后不应把这句话当作正文事实写入需求规格说明，而应：

1. 基于已确认事实生成章节化草案。
2. 把未闭合问题压缩为“待确认事项”或 `retained_gaps`。
3. `document_patch.operation` 使用 `replace`，把本次草案作为该章节当前展示版本，避免旧正文和草案 bullet 重复堆叠。
4. 草案必须保留结果复核、性能约束和验收链条，不得把 `REQ-3.6`、`REQ-5.1`、`REQ-6.2` 降级为空占位。
5. 下一问转为交付说明；P2 侧应物化为 `draft_delivery`，`options=[]`，不再继续追问。
6. `raw_workflow_trace.nodes` 中记录 `branch_draft_or_continue` 与 `draft_compose`。

### 4.5 next_interaction_planning

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
- 快捷选项必须是对象数组，且每项包含 `key`、`label`、`recommended`。
- 至少一个选项必须为推荐项。
- 如果用户可以自由补充，应提供“自定义补充”类选项。

### 4.6 normalize_output

最终输出必须是一个 JSON 对象，并满足 `03-P2-Dify工作流输入输出字段规范.md` 的输出字段要求。

最终节点必须校验：

- `assistant_message` 非空。
- `next_question` 非空，除非后续进入明确 completed 状态。
- `quick_options` 为对象数组，每项有 `key` 和 `label`。
- `document_patch` 每项有 `content`、`target_section`、`anchor_path`。
- `decision_state_delta` 固定包含 `confirmed_facts`、`confirmed_decisions`、`tentative_assumptions`、`open_questions`、`rejected_directions`、`chapter_projections`、`next_focus`。
- `raw_workflow_trace.nodes` 包含关键节点和分支信息。

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
- 缺少 `DIFY_API_KEY` 时直接报错，不执行本地 fallback。

## 8. 验收标准

专项 workflow 完成后至少满足：

- Dify workflow 已发布。
- 输入变量名与本规范一致。
- 输出 JSON 能被 adapter 解析。
- 使用示例输入能生成 `document_patch`。
- 输出中包含 `decision_state_delta.confirmed_facts`。
- 输出中包含 `next_question`。
- 接入真实 Dify 后，P2 页面可以选择 `brainstorm-v1-dify-workflow` 并完成一轮会话。
- 多事实输入后，不再机械重复已被绕开的旧问题。
- 6 轮链路后，正文补丁至少分散到 3 个章节。
- “停止追问并输出草案”必须进入草案分支，生成章节化草案。
- `open_questions` 不应无限增长，草案阶段应收束为保留缺口。
- 草案阶段的 patch 必须使用 `replace`；复测时关键章节不得出现“旧正文 + 草案 bullet”重复堆叠。
- 部署分析不得落入部署环境章节；边界排除事实不得落入协同共享章节；混合非功能事实不得丢失部署、安全和追溯信息。
- 草案必须覆盖结果复核、可接受性能和验收任务链；复测时 `REQ-3.6` 应保留业务专家复核或成果导出复核，`REQ-5.1` 应保留可接受时间或流畅性，`REQ-6.2` 应保留分析工具使用、成果导出复核、权限日志等验收链条。
