# P2 Brainstorming Turn 引擎与状态机设计

**日期：** 2026-05-01

**文档状态：** Lab 实现验证中，Current Turn 协议升级为执行闭环视角

## 1. 设计背景

`P2 Brainstorming Lab` 的早期实现把 `Turn` 理解为：

```text
系统选择一个需求规格节点 -> 系统提问 -> 用户回答 -> 系统关闭该节点 -> 系统继续提下一题
```

实测后确认，这个模型会把 Brainstorming 退化成问卷或向导。用户被迫回答系统预设问题，系统也容易机械地顺着完成度树追问，而不是围绕用户本轮真正提出的问题、描述、判断或质疑进行理解、补充和状态回看。

新的设计基线是：

```text
Turn = 用户输入触发的一次需求规格补充执行闭环
```

系统可以在上一轮结尾留下交互对象，但它不是强制起点。用户可以回答、选择、部分回答、改题、反驳、补充，或者完全忽略该交互对象。

## 2. 核心定义

### 2.1 Brainstorming Turn

一个 `BrainstormTurn` 从用户输入开始。

最小闭环：

```text
上轮系统留题（可选）
-> 用户输入
-> 输入承接判断
-> 规格补充执行
-> 补充后状态回看
-> 本轮处理闭环
-> 下一轮交互设计（可选）
```

关键约束：

- Turn 的起点是 `user_input`，不是系统问题。
- 上轮系统留题只是上下文，不是强制问题。
- 系统必须先基于用户输入补充需求规格，再回看当前补充是否足够。
- 下一轮交互设计必须发生在补充执行和状态回看之后，不能为了运行流程而机械出题。

### 2.2 上轮系统留题

`previous_interaction` 表示上一轮系统留给用户的交互对象。

它不是单纯“建议话题”。它可能是：

- `none`：没有留题，等待用户自由输入。
- `open_question`：开放问题，例如“谁使用这个系统？”
- `choice_question`：选择题，例如“系统更偏向 A/B/C 哪一种？”
- `suggestion`：建议方向，例如“下一轮可以补充系统边界。”
- `free_continue`：允许用户自由补充或继续。

示例：

```json
{
  "interaction_id": "interaction-0003",
  "type": "choice_question",
  "prompt": "软件定位是什么？请说明它面向哪个领域、解决什么问题，以及第一阶段不做什么。",
  "options": [
    { "key": "A", "label": "计算分析工具", "recommended": true },
    { "key": "B", "label": "协同规划平台", "recommended": false },
    { "key": "C", "label": "二者兼有但先做分析", "recommended": false }
  ],
  "target_spec_node_ids": ["SPEC-REQ-2.1"],
  "reason": "项目概述中的软件定位仍缺少可写入材料。"
}
```

首轮可以为：

```json
{
  "type": "none",
  "prompt": "无，用户自由发起。",
  "options": [],
  "target_spec_node_ids": [],
  "reason": "首轮没有上轮系统留题。"
}
```

快捷选项是 `previous_interaction.options` 的一部分。系统如果在上一轮展示了 `A/B/C`，则必须把这些选项及其完整标签保存为下一轮可判定上下文。用户下一轮输入 `A`、`A，计算分析工具`，或通过界面点击 `A` 选项时，应优先按“用户选择了上轮选项”判定，不能只拿 `A` 的短文本做关键词相似度判断。

### 2.3 本轮用户输入

`user_input` 是 Turn 的主事实源。

它可以是：

- 自由描述
- 提问
- 反驳
- 判断
- 选择项输入
- 简短命令
- 补充约束
- 对系统上一轮回答的纠正

当用户输入是快捷选项时，归一化结果必须同时保留原始输入、选项 key 和匹配到的完整选项标签。

### 2.4 输入承接判断

`input_relation` 描述用户输入和 `previous_interaction` 的关系。

建议枚举：

| 枚举 | 含义 |
| --- | --- |
| `none` | 没有上轮系统留题 |
| `answered` | 用户回答了上轮开放问题 |
| `selected_option` | 用户选择了上轮选项 |
| `partially_answered` | 用户部分回答，但仍有缺口 |
| `topic_shift` | 用户主动改题 |
| `challenge` | 用户反驳或质疑上轮留题 |
| `supplement` | 用户补充上一轮内容 |
| `unrelated` | 用户输入与上轮留题无关 |

这个字段的目的不是限制用户，而是解释“本轮为什么这样处理”。

### 2.5 规格补充执行

`spec_execution` 是 Current Turn 的核心。

它必须说明系统基于用户输入做了什么，而不是只说“我理解了”或“我回应了”。至少包含：

- 系统理解摘要。
- 识别出的确认事实。
- 建议写入的需求规格正文片段。
- 影响的规格节点。
- 本轮状态变化。

现有的 `organizer_interpretation`、`affected_spec_nodes`、`confirmed_facts_delta`、`document_patch`、`annotations` 应归并到这个视角展示。

### 2.6 补充后状态回看

`post_update_review` 表示系统补充规格之后的回看分析。

它必须在生成下一轮交互之前产生，回答：

- 上轮系统留题是否已经被充分处理？
- 本轮补充的规格内容是否足够关闭相关节点？
- 如果不足，是继续围绕当前节点追问，还是进入其他节点？
- 当前整体需求规格完成度还缺哪些关键材料？

这一步用于避免系统“刚收到回答就机械进入下一题”。

### 2.7 本轮处理闭环

`closure_decision` 判断的是本轮执行是否闭环，不是泛泛地“是否回应用户诉求”。

它至少要说明：

- 用户输入是否已经被吸收。
- 规格补充是否已经形成。
- 上轮留题是否已经处理。
- 是否需要继续追问同一个问题。
- 下一步策略是什么。

### 2.8 下一轮交互设计

`next_interaction` 表示系统在完成补充执行和状态回看后，为下一轮留下的交互对象。

它可能是：

- 继续追问当前规格节点。
- 进入下一个规格节点。
- 给出轻量 A/B/C 选项。
- 不给题，等待用户自由输入。
- 建议整体复核。

它不是流程必然推进器，也不是强制用户回答的题。

## 3. Turn 输出协议

`BrainstormTurn` 主协议使用以下结构：

```json
{
  "turn_id": "turn-0004",
  "session_id": "bs-001",
  "previous_interaction": {
    "interaction_id": "interaction-0003",
    "type": "choice_question",
    "prompt": "软件定位是什么？请说明它面向哪个领域、解决什么问题，以及第一阶段不做什么。",
    "options": [
      { "key": "A", "label": "计算分析工具", "recommended": true },
      { "key": "B", "label": "协同规划平台", "recommended": false }
    ],
    "target_spec_node_ids": ["SPEC-REQ-2.1"],
    "reason": "项目概述中的软件定位仍缺少可写入材料。"
  },
  "user_input": "A",
  "normalized_input": {
    "input_type": "quick_option_answer",
    "matched_option": "A",
    "matched_option_label": "计算分析工具",
    "semantic": "计算分析工具"
  },
  "input_relation": {
    "relation": "selected_option",
    "reason": "用户选择了上轮选项 A：计算分析工具。"
  },
  "spec_execution": {
    "interpretation": {
      "summary": "用户确认软件定位为计算分析工具。",
      "intent": "confirm_direction",
      "confidence": "high"
    },
    "assistant_message": "基于你的输入，本轮补充了软件定位：系统按计算分析工具处理。",
    "confirmed_facts": ["软件定位为计算分析工具。"],
    "affected_spec_nodes": [
      {
        "node_id": "SPEC-REQ-2.1",
        "title": "REQ-2.1 软件定位",
        "target_section": "2 项目概述 / 软件定位",
        "effect": "update",
        "reason": "用户确认软件定位。"
      }
    ],
    "document_patch": [
      {
        "section": "2 项目概述 / 软件定位",
        "operation": "append_or_update",
        "content": "本软件定位为空域领域的计算分析工具。",
        "write_policy": "patch_suggestion_only"
      }
    ],
    "state_changes": {
      "closed_question_ids": ["Q-002"],
      "created_question_ids": ["Q-003"],
      "closed_spec_node_ids": ["SPEC-REQ-2.1"],
      "next_active_spec_node_id": "SPEC-REQ-3.1"
    },
    "annotations": ["该修补建议仅进入 Lab 过程区，不直接写入正式需求规格草稿。"],
    "risks": []
  },
  "post_update_review": {
    "summary": "软件定位已有可写入材料，当前节点可以关闭；用户角色章节仍缺少材料。",
    "previous_interaction_resolved": true,
    "current_spec_node_sufficient": true,
    "needs_followup_on_same_topic": false,
    "remaining_gaps": ["需要确认主要用户角色、职责和管理员是否存在。"]
  },
  "closure_decision": {
    "status": "closed",
    "reason": "本轮输入已被吸收，并形成软件定位章节的正文建议；无需继续追问同一题。",
    "next_action": "propose_next_interaction"
  },
  "next_interaction": {
    "interaction_id": "interaction-0004",
    "type": "choice_question",
    "prompt": "谁使用这个系统？请说明主要用户角色、职责和是否存在协作者或管理员。",
    "options": [
      { "key": "A", "label": "领域专家直接使用", "recommended": true },
      { "key": "B", "label": "管理员配置后专家使用", "recommended": false },
      { "key": "C", "label": "多角色协同使用", "recommended": false }
    ],
    "target_spec_node_ids": ["SPEC-REQ-3.1"],
    "reason": "软件定位已补充，下一处关键缺口是用户与角色。"
  },
  "decision_trace": [
    "读取上轮系统留题：软件定位 choice_question。",
    "用户输入 A 命中上轮选项：计算分析工具。",
    "先执行规格补充：更新 2 项目概述 / 软件定位。",
    "补充后回看：软件定位节点可以关闭，用户与角色仍缺材料。",
    "本轮处理闭环：closed，下一步进入用户与角色。"
  ]
}
```

Lab 阶段不保留历史协议界面兼容分支。缺少上述主协议字段时，前端必须显示协议错误。

## 4. 状态机

### 4.1 会话级状态

```text
SessionCreated
  -> WaitingUserInput
  -> TurnRunning
  -> TurnReady
  -> WaitingUserInput
  -> Completed | Archived
```

说明：

- `WaitingUserInput` 可以有 `next_interaction`，也可以没有。
- `TurnRunning` 由用户输入触发，不由系统留题触发。
- `TurnReady` 表示本轮已形成结构化输出，但界面不应自动切到当前 Turn。

### 4.2 Turn 内部状态

```text
ReceiveUserInput
  -> LoadSessionContext
  -> LoadPreviousInteraction
  -> NormalizeUserInput
  -> ClassifyInputRelation
  -> ExecuteSpecSupplement
  -> ReviewPostUpdateState
  -> DecideTurnClosure
  -> DesignNextInteraction
  -> PersistTurn
```

关键变化：

- `LoadPreviousInteraction` 读取的是上轮系统留题，包括题面、选项和目标章节。
- `ClassifyInputRelation` 判断用户是否回答、选择、改题或反驳上轮留题。
- `ExecuteSpecSupplement` 必须先于状态回看和下一轮出题。
- `ReviewPostUpdateState` 负责判断当前补充是否足够、整体还缺什么。
- `DesignNextInteraction` 可以为空，不能为了推进流程而机械生成下一题。

## 5. 与需求规格完成度树的关系

需求规格完成度树仍然存在，但它不是 Turn 的前置控制器。

它的职责是：

- 显示需求规格文档哪些章节已经有材料。
- 帮助组织器发现薄弱章节。
- 为 `next_interaction` 提供候选方向。
- 为 `spec_execution.affected_spec_nodes` 提供映射目标。

它不能做：

- 强制用户按树上第一个 open 节点回答。
- 把 Turn 定义为“关闭当前 active 节点”。
- 用完成度树替代用户本轮输入的真实意图。

正确关系：

```text
用户输入是 Turn 起点
需求规格完成度树是分析参考和输出投影目标
next_interaction 是建议留题，不是约束
```

## 6. 当前 Turn 视图设计

`当前 Turn` 应是本轮沟通执行闭环视图，而不是模板节点问答视图。

推荐展示顺序：

1. `上轮系统留题`
   - 显示留题类型：开放问题 / 选择题 / 建议方向 / 无。
   - 显示题面、选项、目标规格节点和留题原因。
2. `本轮用户输入`
   - 原文显示用户输入。
   - 若命中选项，显示匹配到的完整选项。
3. `输入承接判断`
   - 显示用户是否回答、选择、部分回答、改题、反驳或补充上轮留题。
4. `规格补充执行`
   - 显示系统理解、确认事实、正文建议、影响节点和状态变化。
   - 这是 Current Turn 的核心，不应被下一轮出题抢占。
5. `补充后状态回看`
   - 显示上轮留题是否被处理、当前节点是否足够、是否需要继续追问、整体缺口是什么。
6. `本轮处理闭环`
   - 显示本轮执行闭环状态、原因和下一步策略。
7. `下一轮交互设计`
   - 显示下一轮是否留题、留什么题、是否给选项、为什么这样设计。
8. `决策依据`
   - 显示组织器的判断链。

## 7. 插件化边界

`Brainstorming Turn 引擎` 应作为可插拔组织器模块存在。

### 7.1 稳定输入

```text
BrainstormSession
用户输入
上轮系统留题
上轮快捷选项
历史消息
需求规格模板
需求规格完成度树
知识包上下文
草稿和过程产物
```

### 7.2 稳定输出

```text
BrainstormTurn
previous_interaction
user_input
input_relation
spec_execution
post_update_review
closure_decision
next_interaction
decision_trace
provider_logs
```

### 7.3 协议升级策略

Lab 阶段不保留历史协议界面兼容分支。

规则：

- `BrainstormTurn` 一旦按新版协议确定，前端按新版字段直接渲染。
- 缺少新版审计字段是接口协议错误，应在页面上明确显示协议错误。
- 本地测试数据和页面测试不得构造缺字段 Turn 来验证兼容展示。
- 后端不再向 Turn 对外返回旧主协议字段，例如 `previous_suggestion`、`previous_user_focus`、`input_relation_to_previous_suggestion`、`organizer_interpretation`、`affected_spec_nodes`、`closure_assessment`、`current_user_focus`、`next_suggestion`。
- 需要迁移历史会话时，应由数据迁移或清理策略单独处理，不能污染当前 Lab 交互界面。

### 7.4 可替换点

后续可替换为：

- 自建 Brainstorming Turn 引擎。
- 固定向导式组织器。
- 表单驱动组织器。
- 外部成熟 brainstorming 引擎。
- 规则优先 + 模型解释型组织器。

替换组织器时，不应影响：

- 正式需求规格文档。
- 模板对象。
- 知识绑定。
- 草稿保存。
- 检查与冻结。
- P2 到 P3 输出。

## 8. 验收关注点

后续实现应至少验证：

1. 首轮没有上轮系统留题时，用户自由输入也能产生 Turn。
2. 用户选择上轮 A/B/C 时，系统能按完整选项语义处理。
3. 用户忽略上轮留题并改题时，系统不会强制关闭旧留题相关节点。
4. 用户反驳上轮留题时，系统能记录 `challenge` 并修正状态。
5. 一个 Turn 可以影响多个规格节点。
6. 一个 Turn 可以不影响任何规格节点，只形成解释或注记。
7. Turn 结束时可以没有下一轮留题。
8. `当前 Turn` 能解释“补充执行 -> 状态回看 -> 闭环判断 -> 下一轮设计”的顺序。
9. 需求规格完成度树只作为覆盖度视图，不作为强制问卷流程。

## 9. 结论

`Brainstorming Turn 引擎` 的核心不是“系统问、用户答”，而是“用户输入驱动、系统补充规格、回看状态、再决定是否留下一轮交互对象”。

这个设计使自建 Brainstorming 能力具备独立边界，后续可以与外部更成熟的 brainstorming 引擎进行同维度比较：

- 谁能更好理解用户自由输入。
- 谁能更好判断用户是否承接上轮系统留题。
- 谁能更好把沟通内容补充到标准需求规格文档。
- 谁能更好在补充后判断是否继续追问或进入下一题。
