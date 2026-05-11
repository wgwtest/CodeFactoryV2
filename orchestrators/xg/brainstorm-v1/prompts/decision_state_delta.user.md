# Decision State Delta User Prompt

请基于阶段上下文生成本轮需求分析结构化状态增量。

输出重点：

- `organizer_interpretation`：简要说明你如何理解本轮用户输入与当前会话状态的关系。
- `decision_state_delta.confirmed_facts`：用户本轮明确给出的事实。
- `decision_state_delta.confirmed_decisions`：用户本轮明确确认的产品、范围、角色、流程或约束决策。
- `decision_state_delta.tentative_assumptions`：当前只能暂按该方向推进、但还没被用户确认的假设。
- `decision_state_delta.open_questions`：本轮新增的、仍需要后续澄清的问题；不要重复历史问题。
- `decision_state_delta.closed_question_refs`：本轮已被用户回答的历史问题引用。
- `decision_state_delta.deferred_question_refs`：本轮决定延期到待确认事项或后续阶段的问题引用。
- `decision_state_delta.superseded_question_refs`：已被新问题替代的历史问题引用。
- `decision_state_delta.rejected_directions`：用户本轮否定、排除或收窄掉的方向。
- `decision_state_delta.chapter_projections`：这些状态未来可能投影到的需求规格章节或条款。
- `decision_state_delta.next_focus`：给下一步交互规划阶段看的候选关注点。

如果为了临时正文投影视图需要，可同时输出 `template_shape_assessment`、`target_anchor_plan` 和 `document_patch`，但它们不能替代 `decision_state_delta`。正文投影要服从结构化状态，不要为了填章节而制造用户没有确认的内容。

当输出 `document_patch` 时：

- 每个 document_patch 必须通过 plan_ref 引用 target_anchor_plan.plan_id。
- 每个 document_patch 必须携带 template_clause_id、display_heading 和 anchor_path。
- target_anchor_plan.template_clause_id 必须来自 ChapterConfigurationContext.canonical_clause_map。
- 不要使用 draft-001、section-1、草案正文 等无法定位到模板条款的自由 plan_ref。

`assistant_message` 只说明本轮结构化状态发生了什么变化，不要抢先生成最终下一轮问题。

如果本轮是收束成稿：

- `organizer_interpretation.intent` 使用 `draft_delivery` 或等价值。
- `assistant_message` 说明“已基于当前结构化状态生成草案候选”，不要继续提问。
- `document_patch` 应覆盖总则、项目概述、功能需求、数据与接口、非功能、验收与待确认事项等主要章节；信息不足的章节使用“待确认”表述。
- 收束成稿模式下必须控制 provider JSON 尺寸：document_patch 最多输出 6 条，每条 content 控制在 500 字以内；可以把相邻章节合并为摘要 patch，不要在一个 JSON 字符串里输出整份长文档。
- `open_questions_delta` 为空；未闭合问题放入待确认事项 patch。
- 草案正文必须按来源分级写作：已确认事实用确定语气；暂定假设必须标注“暂定”；未闭合问题进入待确认事项；被否定方向进入范围边界或不包含范围。
- 不得把用户没有说过、结构化状态没有确认的内容写成确定需求。特别注意不要自行补出领域标签、部署形态、实时能力、AI/预测能力、指挥责任、硬件控制、测绘级精度、自动决策等结论。
- 如果某章节只有模板位置但没有足够事实，请写“本章节待确认：……”并列出缺口，不要编造完整段落。
