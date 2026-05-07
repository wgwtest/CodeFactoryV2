# Brainstorm v1 Dify-shaped Workflow Orchestrator

这个插件用本地 `workflow.json` 表达 Dify 工作流形态，保留 Brainstorm v1 的核心理念：

- 先理解用户输入与需求规格章节的关系。
- 再把讨论内容沉淀为结构化决策状态。
- 然后把稳定信息投影到需求规格说明章节正文。
- 最后规划下一轮问题。

当前版本不依赖本地 Dify 安装，也不调用真实 Dify 服务。后续接入真实 Dify 时，adapter 内部的本地执行器可以替换为远端 Workflow API 调用，宿主插件合同保持不变。
