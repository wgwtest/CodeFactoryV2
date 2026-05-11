# Next Interaction Planning User Prompt

请根据 review 结果和当前文档整体状态，生成下一步交互规划。

输出重点：

- `next_interaction_plan.planning_strategy`：继续当前问题、推进下一节点、整体复核或等待自由输入。
- `next_interaction_plan.interaction_mode`：本轮后续交互模式；需要继续问用户时为 `ask_user`，已经交付草案且不应追问时为 `draft_delivery` 或 `deliverable`。
- `next_interaction_plan.should_ask_user`：是否需要在本轮结尾继续追问用户。强制收束或草案交付场景必须为 `false`。
- `next_interaction_plan.user_message`：先向用户解释本轮写入和回看结论。
- `next_interaction_plan.next_question`：下一轮主问题。
- `next_interaction_plan.quick_options`：如有必要，提供不超过 3 个纵向可展示的选项。
- `next_interaction_plan.plan_reason`：为什么这样规划下一步。
- `next_interaction_plan.review_acknowledgement`：如实承接 review 的结论，不能忽略阻断发现。

如果 `should_ask_user=false`：

- `next_question` 必须为空。
- `quick_options` 必须为空。
- `user_message` 必须说明已交付什么、哪些内容仍列为待确认事项。
