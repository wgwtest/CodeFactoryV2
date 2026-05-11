# Brainstorm v1 Dify Workflow 改造方案

## 1. 文档定位

本文是 `brainstorm-v1-dify-workflow` 插件的 Dify 工作流改造方案，只约束该插件在 Dify 工作台中的节点、Prompt、分支和输出结构。

本文不替代 P2 系统通用设计文档，也不替代 P2 插件输入输出合同。若改造过程中发现需要修改 P2 通用合同，应另行同步到 `DOC/CODEX_DOC/03_规范与流程/` 下的正式规范文档。

## 2. 放置在插件目录的合理性

将本文放在：

```text
orchestrators/xg/brainstorm-v1-dify-workflow/
```

是合理的，原因如下：

1. **职责归属明确**
   - 本文讨论的是 `brainstorm-v1-dify-workflow` 这个具体插件的 Dify workflow 如何改造。
   - 它不是 P2 通用架构策略，也不是所有组织器共享的设计规范。

2. **符合插件可搬迁原则**
   - 该插件被复制、移动或独立交付时，Dify 工作流搭建和整改说明应随插件一起移动。
   - 否则插件代码和 Dify 配置知识会分散到系统文档中，降低可插拔性。

3. **降低主系统文档污染**
   - Dify 节点 Prompt、分支规则、字段映射细节属于插件实现资产。
   - 主系统文档只应记录稳定合同、接入边界和跨插件通用规则。

4. **便于后续按插件独立验收**
   - 该目录已经包含 `manifest.json`、`adapter.py`、`workflow.json` 和 `ORCHESTRATOR.md`。
   - 新增本方案后，可以形成“插件声明、运行适配、Dify 结构、整改方案”四类资产闭环。

边界规则：

- Dify 节点怎么问、怎么判断、怎么投影，写在本目录。
- P2 API 合同、通用错误处理、插件发现机制，写在正式规范目录。
- 单次测试报告，写在 `DOC/CODEX_DOC/06_测试文档/03_机测记录/`。

## 3. 当前问题摘要

依据 `260508-2109-P2-Brainstorm-v1-Dify插件全面测试报告.md`，当前 Dify workflow 已能完成真实调用，但尚未达到完整验收状态。

已修复的 P2 接入问题：

1. Dify 返回字符串数组形式的 `quick_options` 时，P2 后端已归一化为 `{key,label,recommended}` 对象数组。
2. 页面空选项问题已在 P2 服务端合同出口修复。

仍需在 Dify workflow 中整改的问题：

1. **重复追问**
   - 用户已经补充新的有效事实后，workflow 仍反复追问“编写目的”等旧焦点。

2. **多事实吸收不稳定**
   - 用户一轮输入中同时包含用户角色、下游使用者、使用场景时，workflow 未能稳定关闭或暂挂相关问题。

3. **章节投影过窄**
   - 多轮事实几乎都被投影到 `1 总则 / 编写目的`。
   - 未能按事实语义分发到 `2 项目概述`、`3 功能需求`、`4 非功能需求`、`5 验收准则` 等章节。

4. **停止追问后的成稿能力不足**
   - 用户要求“停止追问并输出草案”时，workflow 只是把该输入作为普通事实处理。
   - 需要进入显式草案编排分支。

5. **未闭合问题收束不足**
   - 多轮后 `open_questions` 数量仍然偏高。
   - workflow 缺少问题关闭、合并、降级为“保留风险”的机制。

## 4. 改造目标

本次 Dify workflow 改造的目标不是让 P2 后端硬编码更多组织器逻辑，而是把 Brainstorm v1 的决策过程真正放回 Dify workflow 内部。

目标行为：

1. 每轮先判断用户输入与上一轮问题的关系。
2. 能吸收用户一轮输入中的多个事实。
3. 能关闭、暂挂或改写已有 open questions。
4. 能根据最高价值缺口提出下一轮一个主问题。
5. 快捷选项必须有明确文字，且最好直接返回对象数组。
6. 正文补丁必须按章节投影，而不是全部写到当前活动节点。
7. 用户要求停止追问时，必须进入“草案编排”分支。
8. 输出必须稳定满足 P2 插件合同。

## 5. 输出合同要求

Dify workflow 最终仍通过 `/v1/workflows/run` 返回：

```json
{
  "data": {
    "outputs": {
      "result_json": "{...JSON string...}"
    }
  }
}
```

`result_json` 必须是 JSON 对象字符串，至少包含：

```json
{
  "assistant_message": "",
  "next_question": "",
  "quick_options": [],
  "filled_document_text": "",
  "document_patch": [],
  "changed_sections": [],
  "completion_status": "partial",
  "confidence": "medium",
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "decision_state_delta": {},
  "decision_trace": [],
  "annotations": [],
  "risks": [],
  "raw_workflow_trace": {}
}
```

### 5.1 quick_options 要求

推荐 Dify 直接返回对象数组：

```json
[
  {
    "key": "A",
    "label": "参谋分析员主导研判，指挥员查看结果",
    "recommended": true
  },
  {
    "key": "B",
    "label": "值班员维护态势，参谋分析员使用分析工具",
    "recommended": false
  }
]
```

不推荐只返回字符串数组。P2 现在会兜底归一化字符串数组，但 Dify 侧仍应主动遵守对象数组合同。

### 5.2 document_patch 要求

每条 patch 必须清楚表达目标章节：

```json
[
  {
    "plan_ref": "BRAINSTORM-DIFY-AP-001",
    "operation": "append_or_update",
    "content": "系统主要用户为参谋分析员，下游查看者为指挥员。",
    "write_policy": "patch_suggestion_only",
    "target_section": "3 功能需求 / 用户与角色",
    "anchor_path": "REQ-3.1"
  }
]
```

若 Dify workflow 无法确认目标章节，应把内容保留在 `decision_state_delta` 中，不应强行写入 `1 总则 / 编写目的`。

### 5.3 decision_state_delta 要求

`decision_state_delta` 应区分以下类型：

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

要求：

1. 已被用户明确回答的问题，不应继续作为同一措辞的 open question 返回。
2. 用户反驳或否定的方向，应进入 `rejected_directions`。
3. 尚不能写入正文但有价值的信息，应进入 `tentative_assumptions` 或 `open_questions`。
4. `chapter_projections` 应说明事实将来投影到哪个章节。

## 6. Dify 节点改造方案

### 6.1 normalize_input

现状：

- 主要读取输入字段。
- 对当前活动节点依赖过强。

改造要求：

1. 解析以下输入：
   - `user_input`
   - `normalized_input_json`
   - `decision_state_json`
   - `previous_interaction_json`
   - `active_spec_node_json`
   - `spec_tree_json`
   - `working_document_json`
   - `write_policy`
2. 派生以下中间字段：
   - `last_question`
   - `last_options`
   - `active_section`
   - `known_facts`
   - `open_question_summaries`
   - `draft_requested`
3. 判断用户是否触发收束：
   - 包含“停止追问”
   - 包含“输出草案”
   - 包含“先成稿”
   - 包含“不要继续问”

输出建议：

```json
{
  "normalized_context": {
    "draft_requested": false,
    "active_section": "",
    "last_question": "",
    "open_question_summaries": [],
    "known_facts": []
  }
}
```

### 6.2 intent_understanding

现状：

- 能识别用户输入大意，但对“回答上一问 / 补充新事实 / 反驳 / 改题 / 要求成稿”的区分不足。

改造要求：

将用户输入分类为：

```text
answer_current_question
answer_option_with_extra_fact
new_fact
correction_or_rejection
topic_shift
draft_request
unclear
```

输出建议：

```json
{
  "intent": "answer_option_with_extra_fact",
  "relation_to_previous_question": "answers_and_extends",
  "extracted_facts": [],
  "extracted_decisions": [],
  "rejected_items": [],
  "needs_clarification": false,
  "draft_requested": false
}
```

要求：

1. 如果用户选择了 A/B/C/D，同时补充事实，必须同时吸收选项和补充事实。
2. 如果用户没有回答上一问，但给了有效新事实，不应简单重复上一问。
3. 如果用户要求成稿，必须设置 `draft_requested=true`。

### 6.3 decision_state_delta

现状：

- 能追加 confirmed facts 和 open questions。
- 问题关闭、重复合并、状态迁移不足。

改造要求：

1. 对每个 `open_question` 判断状态：
   - answered
   - still_open
   - superseded
   - deferred_to_draft_gap
2. 回答过的问题不再重复生成。
3. 对同一语义问题进行去重。
4. 当用户输入覆盖多个章节时，必须拆成多个 confirmed facts。

输出建议：

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
  "question_state_changes": {
    "closed_question_ids": [],
    "deferred_question_ids": [],
    "created_question_ids": []
  }
}
```

### 6.4 branch_draft_or_continue

建议新增条件分支节点。

分支条件：

```text
if draft_requested == true:
    go to draft_compose
else:
    go to document_projection
```

该节点的目的：

- 避免把“停止追问并输出草案”当作普通正文事实。
- 明确区分探索阶段和成稿阶段。

### 6.5 document_projection

现状：

- 章节投影过窄，容易全部落到当前活动节点。

改造要求：

按事实语义映射目标章节：

| 事实类型 | 目标章节 |
| --- | --- |
| 软件名称、领域、编写目的 | `1 总则 / 编写目的` |
| 软件定位、边界、不做范围 | `2 项目概述 / 软件定位` |
| 用户角色、下游使用者、职责 | `3 功能需求 / 用户与角色` |
| 流程、数据接入、分析工具 | `3 功能需求 / 核心业务流程` |
| 异常、失败、补偿 | `3 功能需求 / 异常与补偿` |
| 性能、安全、部署、可靠性 | `4 非功能需求 / 性能与可靠性` |
| 验收链路、验收标准 | `5 验收准则 / 验收准则` |

输出要求：

1. 每条 patch 尽量只写一个章节。
2. 不确定章节时写入 `chapter_projections`，不要强行 patch。
3. `changed_sections` 必须来自实际 patch 目标章节。

### 6.6 draft_compose

建议新增 LLM 或 template-transform 节点。

触发条件：

- 用户明确要求停止追问、输出草案、先成稿。

输入：

- `decision_state_json`
- `working_document_json`
- `confirmed_facts`
- `open_questions`
- `chapter_projections`
- `template_structure_json`

输出：

```json
{
  "draft_sections": [
    {
      "target_section": "1 总则 / 编写目的",
      "content": ""
    },
    {
      "target_section": "2 项目概述 / 软件定位",
      "content": ""
    }
  ],
  "retained_gaps": [],
  "draft_quality_notes": []
}
```

要求：

1. 草案必须按模板章节组织。
2. 未闭合问题以“待确认事项”或 `retained_gaps` 表达。
3. 不允许把“用户要求停止追问”写成需求正文事实。

### 6.7 next_interaction_planning

现状：

- 容易重复追问。
- 对最高价值缺口判断不足。

改造要求：

每轮只产生一个主问题，并给出 2-4 个有内容选项。

选择下一问优先级：

1. 如果用户要求成稿，下一问应询问是否接受草案或继续细化哪个缺口。
2. 如果当前 open question 已回答，切换到最高价值未闭合问题。
3. 若用户提供了新事实但未回答旧问题，应判断旧问题是否仍阻塞。
4. 若事实已足够支撑章节草稿，应优先推进成稿或章节审阅。

输出建议：

```json
{
  "next_question": "",
  "quick_options": [
    {"key": "A", "label": "", "recommended": true}
  ],
  "plan_reason": "",
  "target_spec_nodes": []
}
```

选项要求：

1. 不能返回空字符串。
2. 不能返回只有 `A/B/C/D` 但无解释的选项。
3. 至少一个选项必须是推荐项。
4. 如果用户可以自由补充，提供“自定义补充”选项。

### 6.8 normalize_output

现状：

- 可返回 `result_json`，但字段质量依赖上游节点。

改造要求：

在 Dify 最终节点做一次结构校验：

1. `assistant_message` 非空。
2. `next_question` 非空，除非 `completion_status=completed`。
3. `quick_options` 是对象数组，且每项有 `key` 与 `label`。
4. `document_patch` 每项有 `content`，并尽量有 `target_section`。
5. `decision_state_delta` 至少具备固定 7 个字段。
6. `raw_workflow_trace.nodes` 包含本轮经过的关键节点。

## 7. 验收标准

### 7.1 合同验收

1. Dify 返回的 `result_json` 可被 P2 adapter 正常解析。
2. `quick_options` 在 API 输出中始终为对象数组。
3. 前端不再出现空选项。
4. 缺少必填字段时，P2 能给出清晰错误。

### 7.2 行为验收

使用以下至少 6 轮输入复测：

1. 模糊起始需求。
2. 用户选择一个选项。
3. 用户补充角色和主场景。
4. 用户补充数据接入模式。
5. 用户补充不做范围。
6. 用户要求停止追问并输出草案。

通过条件：

1. 第 3 轮后不应继续机械重复第 2 轮问题。
2. 事实应分散投影到至少 3 个章节。
3. 第 6 轮应生成章节化草案，而不是单段确认语句。
4. `open_questions` 应能标记保留缺口，而不是无限增长。
5. 每轮下一问都应有明确理由和可读选项。

### 7.3 回归命令

P2 侧合同回归：

```bash
uv run pytest apps/api/tests/test_orchestrator_plugin_contracts.py apps/api/tests/test_requirement_analysis_api.py -q
```

真实 Dify 联调：

```text
通过 P2 页面或 API 创建 brainstorm-v1-dify-workflow 会话，按 7.2 输入链路执行。
```

## 8. 实施顺序

1. 在 Dify 工作台复制当前 workflow，形成可回滚副本。
2. 修改 `normalize_input`，增加 `draft_requested`、上一问、open question 摘要等派生字段。
3. 修改 `intent_understanding`，增加输入关系分类。
4. 修改 `decision_state_delta`，增加问题关闭、合并、暂挂逻辑。
5. 新增 `branch_draft_or_continue` 条件节点。
6. 修改 `document_projection`，按章节映射生成 patch。
7. 新增 `draft_compose` 节点。
8. 修改 `next_interaction_planning`，实现最高价值缺口选择和对象化选项输出。
9. 修改 `normalize_output`，做最终结构校验。
10. 用 6 轮链路复测，并把结果归档到 `DOC/CODEX_DOC/06_测试文档/03_机测记录/`。

## 9. 回滚方案

1. Dify 工作台保留改造前 workflow 副本。
2. 若新 workflow 无法稳定返回 `result_json`，先回滚到旧 workflow。
3. P2 侧不需要回滚已完成的 quick options 合同归一化修复；该修复是兼容性增强。

## 10. 后续同步要求

完成 Dify 工作台改造后，应同步更新：

1. 本目录 `workflow.json`
   - 更新节点列表、分支和描述。
2. 本目录 `ORCHESTRATOR.md`
   - 更新运行说明和能力边界。
3. 正式测试报告
   - 新增一次改造后机测记录。
4. 如改造影响 P2 通用合同
   - 再同步 `DOC/CODEX_DOC/03_规范与流程/01_数据规范/03-P2-Dify工作流输入输出字段规范.md`。

## 11. 2026-05-08 实施记录

已在本机 Dify 工作台完成本方案的工作流侧整改并发布：

- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- Published Workflow ID：`3e6c884d-fb5e-4977-a5b2-fb01bd5f3367`
- Provider：`deepseek-chat`
- 调用模式：`blocking`

本轮采用“LLM 理解 + Code 节点合同收敛”的实现方式：

1. `normalize_input` 增加上一问、上一组选项、已知事实、未闭合问题摘要和 `draft_requested` 派生。
2. `document_projection` 改为确定性章节映射，所有 patch 补齐 `target_section` 与 `anchor_path`。
3. `branch_draft_or_continue` 以 Code 节点等价分支落地；收束触发后进入 `draft_compose` 行为。
4. `normalize_output` 对 `quick_options`、`document_patch`、`decision_state_delta` 做最终结构校验。

复测证据已归档：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05测试/260508-2109-P2-Brainstorm-v1-Dify工作流整改复测记录.md`
