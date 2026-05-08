# Brainstorm v1 Dify-shaped Workflow Orchestrator

这个插件通过真实 Dify Workflow API 执行 Brainstorm v1 工作流，保留 Brainstorm v1 的核心理念：

- 先理解用户输入与需求规格章节的关系。
- 再把讨论内容沉淀为结构化决策状态。
- 然后把稳定信息投影到需求规格说明章节正文。
- 最后规划下一轮问题。

运行时必须提供 `DIFY_API_KEY`。插件不会在缺少 Dify 配置时降级为本地执行；缺少 API Key 或 Dify 返回结构不合格时会直接报错。`workflow.json` 仅作为 Dify 工作流结构说明和创建参考，不作为本地 fallback 执行器。

插件级 Dify 工作流整改方案见：

- `DIFY_WORKFLOW_REFACTOR_PLAN.md`
