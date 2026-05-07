# Decision State Delta User Prompt

请基于阶段上下文生成本轮需求分析结构化状态增量。

输出重点：

- `organizer_interpretation`：简要说明你如何理解本轮用户输入与当前会话状态的关系。
- `decision_state_delta.confirmed_facts`：用户本轮明确给出的事实。
- `decision_state_delta.confirmed_decisions`：用户本轮明确确认的产品、范围、角色、流程或约束决策。
- `decision_state_delta.tentative_assumptions`：当前只能暂按该方向推进、但还没被用户确认的假设。
- `decision_state_delta.open_questions`：仍需要后续澄清的问题。
- `decision_state_delta.rejected_directions`：用户本轮否定、排除或收窄掉的方向。
- `decision_state_delta.chapter_projections`：这些状态未来可能投影到的需求规格章节或条款。
- `decision_state_delta.next_focus`：给下一步交互规划阶段看的候选关注点。

如果为了临时正文投影视图需要，可同时输出 `template_shape_assessment`、`target_anchor_plan` 和 `document_patch`，但它们不能替代 `decision_state_delta`。正文投影要服从结构化状态，不要为了填章节而制造用户没有确认的内容。

`assistant_message` 只说明本轮结构化状态发生了什么变化，不要抢先生成最终下一轮问题。
