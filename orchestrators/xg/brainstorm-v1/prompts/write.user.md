# Write Stage User Prompt

请基于阶段上下文生成本轮需求规格补写候选。

输出重点：

- organizer_interpretation：说明你如何理解用户输入。
- template_shape_assessment：说明当前模板属于哪种形态，以及本轮允许的写入方式。
- target_anchor_plan：说明本轮每个正文 patch 应挂靠到哪个模板条款或合法子主题。
- confirmed_facts_delta：本轮新增确认事实。
- document_patch：可写入临时正文的候选片段，必须通过 `plan_ref` 引用 `target_anchor_plan.plan_id`。
- 如果是在修正已有段落，document_patch 要给出 replace 或 delete，而不是把新旧说法并列堆积。
- next_suggestion：候选下一轮建议，允许为空。
- quick_options：只有需要选择时才生成。

assistant_message 要先说明本轮实际补充了什么内容，再给出下一步建议，不能匆忙跳到下一题。
