# Brainstorm v1 Dify Workflow 20轮质量整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 在 Dify 工作台执行本计划时，应逐项修改节点、发布副本、真实联调，并把复测记录归档到 `DOC/CODEX_DOC/06_测试文档/03_机测记录/`。步骤使用 checkbox (`- [ ]`) 语法跟踪。

**Goal:** 修复 `brainstorm-v1-dify-workflow` 在 20 轮真实 Dify 深测中暴露的长轮次决策质量问题。

**Architecture:** P2 平台继续只消费插件合同输出，不按插件名称写分支逻辑。Brainstorm v1 的阶段判断、问题闭合、章节投影、草案编排和回看总结都留在 Dify workflow 内部完成。

**Tech Stack:** Dify Workflow、DeepSeek Chat、P2 orchestrator plugin contract、P2 requirement analysis working document materializer。

---

## 1. 文档定位

本文是 `brainstorm-v1-dify-workflow` 插件的第二轮 Dify 工作流整改计划，依据以下 20 轮真实联调报告编写：

```text
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify-20轮深度测试报告.md
```

本文放在插件目录内是有意为之：

- 它描述的是该插件在 Dify 工作台中的节点、Prompt、分支和输出归一化修改。
- 它不是 P2 平台通用设计，不修改插件发现、插件装载、平台物化层或前端页面。
- 它应随 `brainstorm-v1-dify-workflow` 插件一起迁移，便于后续复制、审查和重建 Dify 工作流。

本次不修改 81433 需求规格模板结构。章节落点优先通过 `target_section` 和 Dify 映射规则修正；只有后续多个组织器都需要更细模板项时，才另行进入模板升级议题。

## 2. 当前问题

20 轮深测显示链路层已可用：

- 20/20 轮真实 Dify 调用成功。
- `quick_options` 合同稳定，无空选项。
- Dify 原始 `document_patch` 与 P2 物化 patch 数一致。
- 强制收束可进入 `draft_compose`。
- 最终 working document 可形成多章节块。

剩余问题集中在 Dify workflow 的决策质量：

1. **下一问重复严重**
   - `核心数据接入和主要分析流程是什么？` 出现 3 次。
   - `这些分析能力有哪些明确不做的范围、异常处理或验收口径？` 出现 7 次。
   - `是否继续补充核心流程、边界范围、非功能要求或验收准则？` 出现 8 次。

2. **回看类意图未被识别**
   - 用户要求“回看哪些关键决策已闭合/未闭合”时，workflow 退回到通用“继续补充事实”路径。

3. **open_questions 生命周期不干净**
   - 兜底追问会残留到最终状态。
   - 已被事实覆盖的问题没有稳定关闭或替换。

4. **章节投影仍有漂移**
   - `主要界面列表` 被落到非功能章节。
   - `精度口径`、`导出形式` 的落点过粗。
   - 协同模式的正向能力没有稳定写入功能需求。

5. **最终草案总则仍可能空白**
   - `1 总则 / 编写目的` 在事实已足够时仍输出 `待确认。`。

## 3. 整改原则

1. **不在 P2 平台写插件名分支**
   - 平台只按合同字段处理 `document_patch`、`decision_state_delta`、`quick_options` 等通用结构。
   - 不允许出现 `if orchestrator_id == "brainstorm-v1-dify-workflow"` 这类路径。

2. **Dify 内部负责 Brainstorm v1 阶段逻辑**
   - 用户意图识别、下一问选择、回看总结、草案编排、章节映射都属于 Dify workflow 内部职责。

3. **允许增加 Dify 分支节点，但必须有明确理由**
   - 本次建议新增 `review_status` 路径，因为“回看闭合/未闭合”既不是普通事实补充，也不是要求成稿。
   - 若不单独分支，workflow 容易把回看请求误判为“缺少事实”，导致继续追问。

4. **先改工作流规则，不改模板结构**
   - `主要界面列表` 固定投影到功能需求下的稳定子主题。
   - 本次不要求 81433 模板新增“显示/界面”子项。

## 4. 目标工作流结构

建议将 Dify workflow 调整为以下逻辑路径：

```text
normalize_input
  -> intent_understanding
  -> branch_intent_route
       -> review_status
       -> draft_compose
       -> correction_apply
       -> decision_state_delta
            -> document_projection
            -> next_interaction_planning
  -> normalize_output
```

分支说明：

| 分支 | 触发意图 | 主要职责 |
| --- | --- | --- |
| `review_status` | `review_status` | 汇总已闭合决策、未闭合问题、建议下一焦点；默认不写正文 patch |
| `draft_compose` | `draft_requested` | 基于已知事实生成章节化草案，并保留缺口 |
| `correction_apply` | `correction` | 处理用户否定、修正、撤回和替换事实 |
| `decision_state_delta` | `fact_supplement` / `option_answer` | 吸收事实、关闭问题、更新状态 |

## 5. 节点整改任务

### Task 1: `intent_understanding` 增加稳定意图分类

**Files / Assets:**
- Modify in Dify: `intent_understanding` LLM/Code 节点 Prompt
- Reference: `workflow.json` 中该节点说明，发布后同步更新

- [ ] **Step 1: 将用户输入分类限定为固定枚举**

输出字段必须包含：

```json
{
  "intent": "fact_supplement",
  "relation_to_previous_question": "answers_and_extends",
  "extracted_facts": [],
  "extracted_decisions": [],
  "rejected_items": [],
  "selected_option_keys": [],
  "review_requested": false,
  "draft_requested": false,
  "correction_requested": false
}
```

`intent` 只能取以下值：

| intent | 判定规则 |
| --- | --- |
| `fact_supplement` | 用户补充角色、场景、流程、边界、非功能、验收等事实 |
| `review_status` | 用户要求回看、总结、检查哪些已闭合、哪些未闭合 |
| `draft_requested` | 用户要求停止追问、输出草案、先成稿、不要继续问 |
| `correction` | 用户否定、修正、撤回、替换上一轮事实或方向 |
| `option_answer` | 用户选择 A/B/C/D 或引用上一组选项 |

- [ ] **Step 2: 处理“选项 + 补充事实”的混合输入**

如果用户输入类似：

```text
选 A，但主要用户其实是参谋分析员，下游查看者是指挥员。
```

输出必须同时保留：

```json
{
  "intent": "option_answer",
  "selected_option_keys": ["A"],
  "extracted_facts": [
    "主要用户为参谋分析员。",
    "下游查看者为指挥员。"
  ],
  "relation_to_previous_question": "answers_and_extends"
}
```

- [ ] **Step 3: 复测意图分类**

用以下输入检查分类：

```text
请回看一下，哪些关键决策已经闭合，哪些还没闭合，不要急着写全文。
```

期望：

```json
{
  "intent": "review_status",
  "review_requested": true,
  "draft_requested": false
}
```

### Task 2: 新增 `review_status` 分支

**Files / Assets:**
- Modify in Dify: 新增 `branch_intent_route` 条件节点
- Modify in Dify: 新增 `review_status` LLM/Code 节点
- Reference after publish: `workflow.json`

- [ ] **Step 1: 增加分支条件**

分支规则：

```text
if intent == "review_status":
    go to review_status
elif intent == "draft_requested":
    go to draft_compose
elif intent == "correction":
    go to correction_apply
else:
    go to decision_state_delta
```

- [ ] **Step 2: 定义 `review_status` 输出**

`review_status` 不应要求用户继续补事实，而应返回状态摘要：

```json
{
  "assistant_message": "已闭合：...；仍未闭合：...；建议下一步优先确认：...",
  "next_question": "接下来优先处理哪个未闭合项？",
  "quick_options": [
    {"key": "A", "label": "补齐验收口径", "recommended": true},
    {"key": "B", "label": "补齐非功能约束", "recommended": false},
    {"key": "C", "label": "直接输出当前草案", "recommended": false}
  ],
  "document_patch": [],
  "decision_state_delta": {
    "confirmed_facts": [],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": "review_followup"
  },
  "raw_workflow_trace": {
    "branch_taken": "review_status"
  }
}
```

- [ ] **Step 3: 复测第 18 轮场景**

输入：

```text
请回看一下，哪些关键决策已经闭合，哪些还没闭合，不要急着写全文。
```

通过条件：

- `raw_workflow_trace.branch_taken == "review_status"`。
- `assistant_message` 明确列出已闭合和未闭合事项。
- `next_question` 不再是“请继续补充一个可以写入需求规格说明的事实”。
- `document_patch` 可以为空，不应把回看请求写入正文。

### Task 3: `decision_state_delta` 增加问题生命周期

**Files / Assets:**
- Modify in Dify: `decision_state_delta` 节点 Prompt / Code

- [ ] **Step 1: 为 open question 增加状态迁移**

每轮对已有问题判断以下状态：

| 状态 | 含义 | 输出要求 |
| --- | --- | --- |
| `answered` | 用户本轮事实已回答该问题 | 从有效 open questions 中移除 |
| `still_open` | 仍阻塞后续成稿 | 保留，但避免重复措辞 |
| `superseded` | 被更具体问题替代 | 移除旧问题，新增具体问题 |
| `deferred_to_draft_gap` | 不阻塞当前草案 | 移入保留缺口，不再反复追问 |
| `stale_fallback` | 通用兜底问题残留 | 在 `normalize_output` 前清理 |

- [ ] **Step 2: 输出问题变更摘要**

建议在 `decision_state_delta` 或 `raw_workflow_trace` 中输出：

```json
{
  "question_state_changes": {
    "closed_question_ids": [],
    "deferred_question_ids": [],
    "superseded_question_ids": [],
    "removed_stale_question_ids": [],
    "created_question_ids": []
  }
}
```

- [ ] **Step 3: 清理通用兜底问题**

以下问题不得进入最终状态，除非当前轮真的没有任何有效上下文：

```text
请继续补充一个可以写入需求规格说明的事实，例如用户、场景、流程、边界或验收口径。
```

通过条件：

- 20 轮最终 `open_questions` 不再保留上述通用兜底问题。
- 已被用户回答的问题不以相同语义反复出现。

### Task 4: `document_projection` 细化章节映射

**Files / Assets:**
- Modify in Dify: `document_projection` 节点 Prompt / Code

- [ ] **Step 1: 增加稳定子主题映射表**

| 事实类型 | 目标章节 | anchor_path 建议 | 说明 |
| --- | --- | --- | --- |
| 软件名称、领域、编写目的 | `1 总则 / 编写目的` | `REQ-1.1` | 草案阶段必须能根据已知事实概括，不应长期 `待确认` |
| 软件定位、不做范围、系统边界 | `2 项目概述 / 软件定位` | `REQ-2.1` | 包含“不做自动推荐”等边界 |
| 用户、角色、职责、下游查看者 | `3 功能需求 / 用户与角色` | `REQ-3.1` | 区分主用户和消费方 |
| 核心流程、数据接入、分析任务 | `3 功能需求 / 核心业务流程` | `REQ-3.2` | 包含导入、计算、分析、结果生成 |
| 主要界面、页面列表、交互入口 | `3 功能需求 / 主要界面列表` | `REQ-3.UI` | 本次固定落到功能需求，不改 81433 模板 |
| 协同模式、任务接力、批注、结果共享 | `3 功能需求 / 协同与共享` | `REQ-3.COLLAB` | 正向能力要写入功能需求，不能只保留负向边界 |
| 异常、失败、补偿、重算 | `3 功能需求 / 异常与补偿` | `REQ-3.ERR` | 包含数据缺失、坐标系不一致、计算失败 |
| 精度口径、性能、可靠性、安全、部署 | `4 非功能需求 / 性能与可靠性` | `REQ-4.1` | 精度口径本轮先归入非功能质量约束 |
| 导出格式、导出流程、报告生成 | `3 功能需求 / 核心业务流程` | `REQ-3.2` | 若用户强调验收标准，再同步补到验收准则 |
| 导出验收、任务链验收、判定标准 | `5 验收准则 / 验收准则` | `REQ-5.1` | 写清可验证条件 |

- [ ] **Step 2: 处理一轮多事实拆分**

如果输入同时包含：

```text
主要界面包括态势总览、GIS分析、部署影响分析和报告导出；精度口径按数据源精度展示，不做超精度承诺。
```

期望至少生成两条 patch：

```json
[
  {
    "operation": "append_or_update",
    "target_section": "3 功能需求 / 主要界面列表",
    "anchor_path": "REQ-3.UI",
    "content": "主要界面包括态势总览、GIS 分析、部署影响分析和报告导出。"
  },
  {
    "operation": "append_or_update",
    "target_section": "4 非功能需求 / 性能与可靠性",
    "anchor_path": "REQ-4.1",
    "content": "精度口径按数据源精度展示，系统不做超出原始数据精度的承诺。"
  }
]
```

- [ ] **Step 3: 复测章节漂移**

通过条件：

- `主要界面列表` 不再落入 `4 非功能需求 / 性能与可靠性`。
- `精度口径` 不再落入 `3 功能需求 / 核心业务流程`。
- 协同模式正向要求能形成 `3 功能需求` patch。

### Task 5: `next_interaction_planning` 增加反重复策略

**Files / Assets:**
- Modify in Dify: `next_interaction_planning` 节点 Prompt / Code

- [ ] **Step 1: 引入近期问题窗口**

节点输入应读取最近至少 6 轮的：

```json
{
  "recent_next_questions": [],
  "recent_next_focus": [],
  "open_questions": [],
  "confirmed_facts": []
}
```

- [ ] **Step 2: 按语义焦点去重**

不要只按完全相同文本去重。以下三类应视作同一语义焦点：

```text
核心数据接入和主要分析流程是什么？
请补充核心流程和数据接入。
是否继续补充核心流程、边界范围、非功能要求或验收准则？
```

如果同一语义焦点在最近 6 轮出现超过 2 次：

- 若它已被部分回答，改问更具体的缺口。
- 若它不阻塞草案，标记为 `deferred_to_draft_gap`。
- 若它仍阻塞，说明阻塞原因，并只问一次精确问题。

- [ ] **Step 3: 下一问优先级**

按以下顺序选下一问：

1. 用户刚要求回看：询问优先补哪个未闭合项，或是否成稿。
2. 用户刚要求成稿：询问是否接受草案，或选择一个缺口继续细化。
3. 当前章节缺少验收口径：优先问可验证标准。
4. 当前事实已足够：引导审阅草案，而不是继续宽泛追问。
5. 只有确实缺基础事实时，才问用户、场景、流程、边界这类宽问题。

- [ ] **Step 4: 复测重复问题**

通过条件：

- 20 轮内同一语义焦点的下一问不超过 2 次。
- 不再出现 7 次或 8 次重复宽泛追问。

### Task 6: `draft_compose` 补强总则与完整草案

**Files / Assets:**
- Modify in Dify: `draft_compose` 节点 Prompt / Code

- [ ] **Step 1: 增加总则最低生成规则**

如果已知事实包含软件名称、领域、核心能力或使用场景中的任意两类，`1 总则 / 编写目的` 不得输出 `待确认。`。

示例输入事实：

```json
[
  "系统是态势分析系统。",
  "主要能力包括态势展示、GIS 分析、通视量算、坡度分析和部署影响分析。",
  "主要用于实时态势展示和事前研判。"
]
```

期望总则内容：

```text
本文用于明确态势分析系统的需求范围、核心能力和验收口径，为后续设计、开发、测试和交付提供依据。系统面向实时态势展示与事前研判场景，覆盖 GIS 分析、通视量算、坡度分析和部署影响分析等能力。
```

- [ ] **Step 2: 保留缺口但不阻塞草案**

未闭合问题应写入 `retained_gaps` 或下一问，不应导致章节主体退化为 `待确认。`。

- [ ] **Step 3: 复测最终草案**

通过条件：

- 最终 `1 总则 / 编写目的` 非空，且不是 `待确认。`。
- 协同模式、界面列表、精度口径等中后段事实能被吸收进正文。

### Task 7: `normalize_output` 增加最终质量闸

**Files / Assets:**
- Modify in Dify: `normalize_output` Code 节点

- [ ] **Step 1: 合同结构校验**

最终 `result_json` 必须满足：

```json
{
  "assistant_message": "非空",
  "next_question": "非空，除非 completion_status=completed",
  "quick_options": [
    {"key": "A", "label": "非空", "recommended": true}
  ],
  "document_patch": [],
  "changed_sections": [],
  "completion_status": "partial",
  "confidence": "medium",
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "decision_state_delta": {
    "confirmed_facts": [],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": ""
  },
  "raw_workflow_trace": {
    "branch_taken": "",
    "intent": "",
    "question_state_changes": {}
  }
}
```

- [ ] **Step 2: 清理 stale fallback**

如果 `open_questions_delta` 或 `decision_state_delta.open_questions` 包含通用兜底问题，且本轮已有有效事实、回看响应或草案输出，则移除该问题。

- [ ] **Step 3: 输出节点路径**

`raw_workflow_trace` 至少包含：

```json
{
  "intent": "review_status",
  "branch_taken": "review_status",
  "projection_rules_applied": [],
  "question_state_changes": {}
}
```

## 6. 复测方案

### 6.1 P2 合同回归

在当前 worktree 运行：

```bash
uv run pytest apps/api/tests/test_orchestrator_plugin_contracts.py apps/api/tests/test_requirement_analysis_api.py apps/api/tests/test_orchestrator_plugin_discovery.py apps/api/tests/test_orchestrator_architecture_guards.py apps/api/tests/test_orchestrator_runtime.py -q
```

通过条件：

- 所有测试通过。
- 架构守卫仍确认平台没有按插件 ID 分支。

### 6.2 真实 Dify 20 轮复测

复用 20 轮深测链路：

```text
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify-20轮深度测试报告.md
```

通过条件：

| 检查项 | 通过标准 |
| --- | --- |
| 真实 Dify 调用 | 20/20 返回 200 |
| 快捷选项 | 20/20 `quick_options` 为非空对象数组 |
| patch 物化 | 每轮 Dify raw patch 数与 P2 materialized patch 数一致 |
| 回看分支 | 第 18 轮进入 `review_status`，返回闭合/未闭合摘要 |
| 重复追问 | 同一语义焦点下一问不超过 2 次 |
| open_questions | 最终无通用兜底问题残留 |
| 章节投影 | 主要界面、精度口径、协同模式落点符合映射表 |
| 最终总则 | `1 总则 / 编写目的` 非空且不是 `待确认。` |
| 草案收束 | 第 20 轮进入 `draft_compose` 并形成多章节草案 |

### 6.3 复测记录归档

复测后新增正式记录：

```text
DOC/CODEX_DOC/06_测试文档/03_机测记录/YYYY-MM-DD-P2-Brainstorm-v1-Dify-20轮质量整改复测记录.md
```

记录至少包含：

- Dify App ID / Workflow ID / 发布时间。
- P2 会话 ID。
- 20 轮摘要表。
- 第 18 轮 `review_status` 输出摘录。
- 最终 working document 章节列表。
- 未通过项和下一轮整改建议。

## 7. 实施顺序

1. 在 Dify 工作台复制当前已发布 workflow，创建可回滚副本。
2. 修改 `intent_understanding`，增加固定意图枚举。
3. 新增 `branch_intent_route` 和 `review_status`。
4. 修改 `decision_state_delta`，增加问题生命周期处理。
5. 修改 `document_projection`，补充界面、协同、精度、导出映射。
6. 修改 `next_interaction_planning`，加入反重复策略。
7. 修改 `draft_compose`，补强总则生成与缺口保留。
8. 修改 `normalize_output`，增加质量闸和 trace。
9. 发布 Dify workflow。
10. 同步更新本目录 `workflow.json` 和 `ORCHESTRATOR.md` 中的工作流版本信息。
11. 执行 P2 合同回归和真实 Dify 20 轮复测。
12. 归档复测记录。

## 8. 回滚策略

1. Dify 工作台保留整改前 workflow 副本。
2. 新 workflow 若无法稳定返回 `result_json`，先切回旧 workflow。
3. P2 平台无需因本计划回滚；本计划不修改平台代码。
4. 若新映射导致章节过细，可只回滚 `document_projection` 映射表，不影响 `review_status` 和反重复策略。

## 9. 自检清单

- [x] 本计划没有要求 P2 平台按插件名称分支。
- [x] 本计划没有要求修改 81433 模板结构。
- [x] `review_status` 增加理由明确：处理回看/闭合/未闭合意图。
- [x] `主要界面列表` 固定投影到 `3 功能需求 / 主要界面列表`。
- [x] `精度口径` 固定投影到 `4 非功能需求 / 性能与可靠性`。
- [x] `协同模式` 正向要求固定投影到 `3 功能需求 / 协同与共享`。
- [x] `导出形式` 根据语义投影到功能流程，必要时同步补验收准则。
- [x] 20 轮复测通过标准明确。

## 10. 实施结果

实施日期：`2026-05-08`

### 10.1 已发布版本

- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- Published Workflow ID：`e3d3b39f-07e8-495d-bd90-356bba898ef7`
- P2 复测会话 ID：`38130bb7-d72a-419f-818c-6dfe959e3893`
- 复测结果文件：`.run-logs/p2-dify-20turn-remediation-result.json`

### 10.2 已完成整改点

1. `review_status` 路由已生效，第 18 轮回看请求进入 `review_status`，不写正文 patch。
2. `draft_requested` 优先级高于 `review_status` 关键词，第 20 轮含“未闭合”的强制成稿请求进入 `draft_compose`。
3. “补充剩余未闭合项”按事实补充处理，第 19 轮写入 `3 功能需求 / 核心业务流程`。
4. 章节投影已覆盖主要界面、协同、异常、精度、安全、验收等细分落点。
5. 事实覆盖较充分后，下一问转入“回看闭合项或直接输出草案”，避免长轮次反复追问异常/验收等细节。
6. 草案生成会综合已知事实补齐 `1 总则 / 编写目的`，并过滤已回答的模板初始问题。
7. `normalize_output` 清理通用兜底问题，最终 `open_questions` 为 0。
8. 插件 adapter 在 `draft_compose` 分支用 Dify 返回的待确认项替换旧 open questions，避免旧模板问题继续残留。

### 10.3 最终 20 轮复测摘要

| 检查项 | 结果 |
| --- | --- |
| 20/20 轮真实 Dify 调用成功 | 通过 |
| `quick_options` 均为对象数组 | 通过 |
| patch 均带 `target_section` / `anchor_path` | 通过 |
| 第 18 轮进入 `review_status` | 通过 |
| 第 20 轮进入 `draft_compose` | 通过 |
| 同一语义焦点下一问不超过 2 次（排除回看/成稿入口） | 通过 |
| 最终无 stale fallback open question | 通过 |
| `主要界面列表` 投影正确 | 通过 |
| `精度口径` 投影正确 | 通过 |
| `协同模式` 投影正确 | 通过 |
| 最终总则非空且不是 `待确认。` | 通过 |
| 最终草案包含关键术语 | 通过 |

最终统计：

- `confirmed_facts`：27
- `open_questions`：0
- `working_blocks`：9

正式复测记录见：

```text
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify-20轮质量整改复测记录.md
```
