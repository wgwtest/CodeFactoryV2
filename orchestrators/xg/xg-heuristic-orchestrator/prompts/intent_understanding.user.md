# Intent Understanding User Prompt

请根据阶段上下文识别本轮用户输入意图，并输出结构化的意图理解结果。

输出重点：

- `intent_understanding_result`：用户目标摘要、输入类型、与上一轮交互的关系、选项处理、目标章节候选、文档策略、写作任务候选、review 关注点候选。
- `target_document_structure`：本轮建议命中的目标章节、锚点和当前主要缺口。
- `stage_task_definition`：后续 write / review 阶段要遵循的正式任务定义。
- `stage_quality_constraints`：本轮至少要写到什么程度、必须覆盖哪些维度。

如果用户输入同时包含选项和补充事实，不要只保留选项结论；必须把补充事实进入任务定义。
