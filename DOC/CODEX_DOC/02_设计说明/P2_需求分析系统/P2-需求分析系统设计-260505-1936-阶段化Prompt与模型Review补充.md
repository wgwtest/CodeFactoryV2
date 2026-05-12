# P2-需求分析系统设计-260505-阶段化Prompt与模型Review补充

> 本文件是 `P2-需求分析系统设计.md` 的独立补充方案，目标是把当前 `P2 XG 需求分析组织器 Lab` 中基础 Prompt、阶段化 Prompt、Review Prompt、阶段输出 schema 与结果采纳策略的设计口径补充完整。
>
> 本文件当前只作为设计补充方案，不直接修改主设计文档。待评审通过后，再将稳定结论归并到主设计文档的第 6 章和第 10 章。

**日期：** 2026-05-05

## 1. 问题定义

### 1.1 当前 Prompt 设计的主要问题

当前 `P2` 需求分析 Lab 已经具备：

- 组织器描述包；
- 轮次阶段计划；
- `write -> apply -> review -> decide` 的执行闭环；
- 模型调用日志；
- 临时正文与回看对象。

但当前 Prompt 设计仍然存在四个根本问题：

1. Prompt 来源分散在组织器包、组织器宿主和模型提供方适配代码三处，没有形成单一可审查边界。
2. `write` 阶段的基础 Prompt 仍然承担过多职责，混合了理解、补写、回看约束和下一轮设计要求。
3. `review` 阶段在当前实现中仍是服务端规则复核，不是真正的模型 Review，因此 Review Prompt 尚不存在清晰设计实体。
4. 输出 schema 和结果采用策略主要写在 Python 代码里，不利于组织器替换、阶段对比和 Prompt 调优。

### 1.2 当前实现的 Prompt 来源拆解

当前 `write` 阶段的基础 Prompt 由以下三层共同组成：

| 层 | 当前存储位置 | 当前作用 | 当前问题 |
| --- | --- | --- | --- |
| 组织器描述文本 | `orchestrators/xg/xg-heuristic-orchestrator/ORCHESTRATOR.md`、`policy.md`、`prompt.md` | 声明组织器定位、风格和约束 | `prompt.md` 信息量偏弱，无法单独承载阶段策略 |
| 组织器宿主硬编码提示 | `apps/api/app/orchestrators/runner_host.py` | 拼接上下文、补充通用约束、生成 `assembled_prompt` | 将阶段职责和业务规则硬编码到宿主，降低了可替换性 |
| 模型提供方适配硬编码 | `apps/api/app/requirement_analysis/deepseek_client.py` | 写死 system message、write 阶段输出 schema、额外上下文字段 | Prompt 与 schema 强耦合在 DeepSeek 适配器里，无法按阶段演进 |

这意味着当前所谓“基础 Prompt”并不是单一对象，而是：

```text
组织器包文本
  + 宿主拼装逻辑
  + 提供方适配层硬编码 system prompt
  + 提供方适配层硬编码输出 schema
```

该形态可以工作，但不适合作为长期设计。

### 1.3 本补充的目标

本补充方案希望把 Prompt 相关设计从“能运行的临时实现”升级为“可解释、可替换、可审计、可调优”的目标态。

本补充的目标包括：

- 明确基础 Prompt 当前是否合理，以及为什么不够合理；
- 给出阶段化 Prompt 的目标结构；
- 给出 Review Prompt 的目标输入、输出、调用和兜底设计；
- 给出阶段输出 schema 的存储和解析方案；
- 给出阶段结果采用策略（Adoption Policy）的设计方案；
- 给出这些设计内容应归并回主设计文档的章节位置。

## 2. 设计结论

### 2.1 基础 Prompt 的设计判断

当前基础 Prompt 只能算“临时可运行”，不能算“目标态合理设计”。

理由如下：

1. 基础 Prompt 没有形成单一资产，难以版本化评审。
2. `write` 阶段同时承担理解、补写、回看约束和下一轮推进要求，容易造成模型过早进入下一题。
3. Prompt 策略与输出 schema 没有按阶段拆分，难以定位问题来自理解、补写、回看还是后处理。
4. 当前 `review` 阶段没有对应的模型 Prompt 资产，无法形成真正的双阶段 Prompt 体系。

因此，本补充明确要求：

```text
当前单段基础 Prompt 不是目标态设计，
必须迁移为“按阶段组织的 Prompt / Schema / Adoption Policy 组合”。
```

### 2.2 Prompt 相关设计必须分成四个对象

后续设计中，不能只讨论“Prompt”，而必须分成四个独立对象：

| 对象 | 含义 | 责任 |
| --- | --- | --- |
| 阶段 Prompt | 每个阶段发给模型的提示内容 | 规定该阶段应该做什么，不应该做什么 |
| 阶段输出 Schema | 每个阶段必须返回的结构 | 规定候选结果的 JSON 契约 |
| 阶段结果采用策略 | 服务端如何采纳、修正、丢弃或兜底阶段结果 | 规定模型输出如何进入会话状态机 |
| Prompt Bundle 组装规则 | 宿主如何把策略文本、上下文和 schema 拼成真正请求 | 规定运行时怎样构造模型调用输入 |

四者缺一不可。否则系统仍然会退化为“单段总提示词 + 后端隐式猜测如何使用”。

### 2.3 目标态必须采用阶段化 Prompt

目标态 Prompt 设计必须与轮次执行设计对齐，而不是独立漂浮。

对于 `XG` 启发式组织器，目标态应至少支持两个阶段：

1. `write` 阶段：
   - 理解用户输入；
   - 生成候选事实；
   - 生成候选正文 patch；
   - 生成候选下一轮建议；
   - 不直接关闭节点；
   - 不直接替正式文档写入。

2. `review_after_apply` 阶段：
   - 基于应用后的临时正文；
   - 审查当前目标是否已经形成可接受表达；
   - 判断还缺什么；
   - 判断是否继续当前目标、推进下一节点或进入整体复核；
   - 生成可选 rewrite 建议；
   - 不直接写会话权威状态。

如果未来扩展第三阶段，则可以增加：

3. `design_next_interaction` 阶段：
   - 专门生成下一轮问题或快捷选项候选；
   - 与 `review` 阶段分离。

## 3. 目标文件结构设计

### 3.1 组织器包目录结构升级

当前 `prompt.md` 单文件模式应升级为按阶段组织的目录形态。

建议结构如下：

```text
orchestrators/xg/xg-heuristic-orchestrator/
  manifest.json
  ORCHESTRATOR.md
  policy.md
  spec_strategy.json
  artifact_rules.json
  prompts/
    base_contract.md
    write.system.md
    write.user.md
    review_after_apply.system.md
    review_after_apply.user.md
  schemas/
    write.output.schema.json
    review_after_apply.output.schema.json
  adoption/
    write.adoption.json
    review_after_apply.adoption.json
```

### 3.2 各类文件的职责

| 文件类型 | 责任 | 不应承担的责任 |
| --- | --- | --- |
| `ORCHESTRATOR.md` | 声明组织器定位、适用范围、总体原则 | 不写具体阶段 Prompt 正文 |
| `policy.md` | 声明组织器风格约束，例如启发式、允许改题、只服务于 XG | 不直接定义阶段输出字段 |
| `spec_strategy.json` | 声明阶段顺序、执行模式、输入来源、兜底策略 | 不承载大段自然语言提示词 |
| `prompts/*.md` | 声明阶段 Prompt 正文 | 不负责决定最终采纳逻辑 |
| `schemas/*.json` | 声明阶段输出 schema | 不负责解释业务策略 |
| `adoption/*.json` | 声明服务端对字段的采纳、忽略和兜底规则 | 不负责构造模型请求 |

## 4. Write Prompt 设计

### 4.1 `write` 阶段的任务边界

`write` 阶段只负责“理解和补写”，不负责“最终收束”。

它必须完成：

- 判断用户本轮输入的真实意图；
- 判断输入与上一轮留题的关系；
- 生成新增确认事实；
- 生成候选正文 patch；
- 给出候选下一轮建议。

它不得完成：

- 最终关闭规格节点；
- 基于尚未应用的 patch 自我宣布“已经足够”；
- 直接决定下一轮必须进入哪个节点；
- 写正式需求规格说明文档。

### 4.2 `write` Prompt 的组成

`write` 阶段的 Prompt 应由以下层组成：

| 层 | 内容 |
| --- | --- |
| `base_contract_prompt` | 只能输出 JSON，不得直接写正式文档，不得控制冻结状态 |
| `orchestrator_policy_prompt` | 启发式、允许改题、只服务于 XG 模板 |
| `write_stage_prompt` | 当前阶段只做理解与补写 |
| `template_context` | 当前模板节点、标题、问题、目标条款 |
| `runtime_context` | 用户输入、上轮留题、消息摘要、事实、问题、临时正文摘录 |
| `output_schema` | `write.output.schema.json` |

### 4.3 `write` 输出 schema

建议 `write.output.schema.json` 至少包含：

```json
{
  "organizer_interpretation": {
    "summary": "string",
    "intent": "supplement_requirement|ask_question|correct_direction|challenge|continue",
    "confidence": "low|medium|high"
  },
  "assistant_message": "string",
  "next_suggestion": {
    "kind": "topic",
    "content": "string",
    "reason": "string",
    "related_spec_node_ids": []
  },
  "quick_options": [],
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "document_patch": [],
  "annotations": [],
  "risks": [],
  "confidence": "low|medium|high"
}
```

### 4.4 `write` 结果采用策略

`write` 阶段输出不能直接等于轮次最终结果。

建议采用策略如下：

- `organizer_interpretation`：允许采纳并在必要时由服务端补充说明。
- `assistant_message`：可用于当前轮回答，但允许后续服务端拼接审计结果。
- `confirmed_facts_delta`：只采纳经过最小校验的新增事实。
- `document_patch`：必须经过目标章节补齐、结构校验和临时正文应用。
- `next_suggestion`：只作为候选，最终 `next_interaction` 由服务端决策。
- `quick_options`：只在服务端认为确有必要时显示。

## 5. Review Prompt 设计

### 5.1 Review 阶段的目标

Review Prompt 的目标不是“重新写一遍答案”，而是：

- 审查应用后的临时正文；
- 判断当前目标是否已经形成可接受表达；
- 判断缺的是什么；
- 判断下一步应该继续当前目标还是推进；
- 生成可选 rewrite 建议。

### 5.2 Review 阶段输入对象

Review 阶段必须看到的是“应用后的结果”，而不是 `write` 阶段的自我声明。

建议输入至少包括：

| 输入对象 | 说明 |
| --- | --- |
| `working_document_after_apply` | 应用 patch 后的临时正文快照 |
| `working_document_update` | 本轮应用的 block / fragment 摘要 |
| `review_target_paths` | 当前重点审查的正文锚点 |
| `current_spec_node` | 当前目标节点 |
| `current_target_question` | 当前目标仍需解决的问题 |
| `recent_revision_fragments` | 最近命中的修订片段 |
| `confirmed_facts` | 当前已确认事实 |
| `open_questions` | 当前仍待确认问题 |

### 5.3 Review Prompt 的组成

Review Prompt 也必须按层组织：

| 层 | 内容 |
| --- | --- |
| `base_contract_prompt` | 只输出 JSON，不直接落库 |
| `orchestrator_policy_prompt` | 启发式组织器总体约束 |
| `review_stage_prompt` | 当前阶段只做正文充分性回看 |
| `working_document_context` | 应用后的正文快照和目标片段 |
| `review_goal` | 本轮 review 希望回答什么问题 |
| `output_schema` | `review_after_apply.output.schema.json` |

### 5.4 `review_after_apply` 输出 schema

建议 schema 至少包含：

```json
{
  "target_review": {
    "status": "acceptable|insufficient|contradictory",
    "reason": "string",
    "covered_points": [],
    "missing_aspects": [],
    "evidence_block_ids": [],
    "evidence_fragment_ids": []
  },
  "global_review": {
    "status": "continue_same_target|move_next_node|whole_document_review",
    "summary": "string",
    "remaining_gaps": []
  },
  "rewrite_advice": [],
  "review_annotations": [],
  "confidence": "low|medium|high"
}
```

### 5.5 Review 结果采用策略

Review 阶段只负责“判断和建议”，不直接重写最终轮次结果。

建议采用策略如下：

- `target_review`：直接进入 `post_update_review` 主体。
- `global_review`：直接进入闭环判断输入。
- `rewrite_advice`：只作为可选重写建议，不直接覆盖已应用正文。
- `review_annotations`：进入 `TurnStageAudit` 或过程注记。
- `confidence`：仅作为审计参考，不决定关闭节点。

### 5.6 Review 兜底策略

即使引入模型 Review，也必须保留规则回看兜底。

建议策略：

| 场景 | 处理方式 |
| --- | --- |
| 模型 Review 成功 | 使用模型 Review 结果进入闭环判断 |
| 模型 Review 返回结构不合法 | 记录失败日志，回退 `server_review` |
| 模型 Review 请求失败 | 记录失败日志，回退 `server_review` |
| 模型 Review 与规则回看冲突 | 保留两者摘要，优先采用保守结论 |

## 6. Prompt Bundle 组装设计

### 6.1 Prompt Bundle 必须阶段化

当前 `assembled_prompt` 是单段总拼装，目标态应升级为阶段化 Prompt Bundle。

建议结构：

```json
{
  "stage_id": "write",
  "base_contract_text": "...",
  "policy_text": "...",
  "stage_prompt_text": "...",
  "context_json": "...",
  "schema_json": "...",
  "assembled_prompt": "..."
}
```

Review 阶段则改为：

```json
{
  "stage_id": "review_after_apply",
  "base_contract_text": "...",
  "policy_text": "...",
  "stage_prompt_text": "...",
  "working_document_json": "...",
  "review_target_paths": [],
  "review_goal": "...",
  "schema_json": "...",
  "assembled_prompt": "..."
}
```

### 6.2 Prompt Bundle 组装职责

目标态应把 Prompt Bundle 组装责任限定在组织器宿主，而不是散落在 Provider 适配器中。

建议新增或明确以下宿主职责：

- 解析阶段引用的 Prompt 文件；
- 解析阶段 schema 文件；
- 解析阶段 adoption policy；
- 读取当前阶段允许读取的上下文；
- 生成阶段专属 `assembled_prompt`；
- 把组装结果写入调用日志。

## 7. 与当前实现的差异

### 7.1 当前实现中需要被替换的部分

当前实现中，以下内容属于临时实现，应在后续重构时迁移：

| 当前位置 | 当前内容 | 目标迁移方向 |
| --- | --- | --- |
| `runner_host.py` | 硬编码通用 Prompt 拼接段落 | 迁移为可配置的 `base_contract.md` + 宿主拼装规则 |
| `deepseek_client.py` | 硬编码 system message | 迁移为阶段化 `*.system.md` |
| `deepseek_client.py` | 硬编码 write 阶段 schema | 迁移为 `schemas/write.output.schema.json` |
| `turn_stage_executor.py` | `server_review` 规则复核占位 | 迁移为可选模型 Review + 规则兜底 |
| `xg-heuristic-orchestrator/prompt.md` | 单文件弱 Prompt | 迁移为 `prompts/` 子目录 |

### 7.2 当前实现中可以保留的部分

以下结构可以保留，但职责要重新明确：

- `spec_strategy.json` 的阶段化定义；
- `TurnStagePlanner` 的阶段计划概念；
- `TurnStageExecutor` 的阶段执行边界；
- `ProviderCallLog` 的四层日志结构；
- `post_update_review`、`decision_trace` 和 `TurnStageAudit` 的审计边界。

## 8. 归并回主设计文档的建议位置

本补充评审通过后，建议归并到主设计文档如下位置：

### 8.1 第 6 章回填位置

| 主文档位置 | 建议补充内容 |
| --- | --- |
| `6.6.5.1 轮次内模型调用策略` | 明确 `write` 与 `review_after_apply` 的模型调用顺序、职责边界和失败兜底 |
| `6.6.7.6 组织器运行子模块` | 补 `StagePromptResolver`、`StageSchemaResolver`、`StageAdoptionPolicyResolver`、`StagePromptBundleBuilder` 等职责 |
| `6.6.7.7 模型提供方子模块` | 补 Provider 只负责请求发送和结果适配，不负责定义 Prompt 策略 |
| `6.6.8 组织器与模型调用设计` | 补 Prompt Bundle 组装、Review Prompt、阶段 schema、结果采用策略 |

### 8.2 第 10 章回填位置

| 主文档位置 | 建议补充内容 |
| --- | --- |
| `10.3 组织器描述包形态` | 增加 `prompts/`、`schemas/`、`adoption/` 目录设计 |
| `10.8 提示词组织策略` | 从原则性描述升级为“基础 Prompt + 阶段 Prompt + Review Prompt + 输出 schema + Adoption Policy”的完整设计 |

## 9. 评审重点

本补充方案评审时，应重点确认以下问题：

1. 基础 Prompt 是否接受“阶段化迁移”的总方向。
2. `review` 阶段是否接受“模型 Review + 规则兜底”的模式。
3. 输出 schema 是否接受按阶段独立文件存储。
4. 结果采用策略是否接受从 Python 硬编码逐步迁移到组织器包资产。
5. 主设计文档的回填位置是否接受以 `6.6` 和 `10.8` 为核心。

## 10. 本补充的最终判断

本补充的最终判断只有三条：

1. 当前基础 Prompt 设计不够合理，只能作为过渡实现。
2. `P2` 要接入真正的大模型 Review，必须先把 Prompt、Schema、Adoption Policy 设计成阶段化资产。
3. Prompt 设计不能只停留在第 10 章原则层，必须同时回填到 `6.6` 的后端运行设计中，才能做到设计与实现一致。
