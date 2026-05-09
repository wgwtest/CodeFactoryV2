# Brainstorm v1 Dify-shaped Workflow Orchestrator

这个插件通过真实 Dify Workflow API 执行 Brainstorm v1 工作流，保留 Brainstorm v1 的核心理念：

- 先理解用户输入与需求规格章节的关系。
- 再把讨论内容沉淀为结构化决策状态。
- 然后把稳定信息投影到需求规格说明章节正文。
- 最后规划下一轮问题。

## 当前 Dify 工作流

- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- 当前已发布 Workflow ID：`e3d3b39f-07e8-495d-bd90-356bba898ef7`
- 发布日期：`2026-05-08`

本版已按 `DIFY_WORKFLOW_REFACTOR_PLAN.md` 和 `DIFY_WORKFLOW_20TURN_REMEDIATION_PLAN.md` 做工作流侧整改：

- `normalize_input` 派生上一问、上一组选项、已知事实、未闭合问题摘要和 `draft_requested`。
- `document_projection` 按事实语义投影到 `1 总则`、`2 项目概述`、`3 功能需求`、`4 非功能需求`、`5 验收准则` 等章节。
- `branch_intent_route` 等价分支已在 Code 节点中实现，回看请求进入 `review_status`，用户要求停止追问或输出草案时进入 `draft_compose`。
- `next_interaction_planning` 已加入长轮次反重复策略，事实覆盖较充分时转入回看/成稿入口。
- `draft_compose` 会综合已知事实生成总则，并过滤已回答的模板初始问题。
- `normalize_output` 最终校验 `quick_options`、`document_patch`、`decision_state_delta` 的合同结构。

运行时必须提供 `DIFY_API_KEY`。插件不会在缺少 Dify 配置时降级为本地执行；缺少 API Key 或 Dify 返回结构不合格时会直接报错。`workflow.json` 仅作为 Dify 工作流结构说明和创建参考，不作为本地 fallback 执行器。

插件级 Dify 工作流整改方案见：

- `DIFY_WORKFLOW_REFACTOR_PLAN.md`
- `DIFY_WORKFLOW_20TURN_REMEDIATION_PLAN.md`

本轮整改复测证据见：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify工作流整改复测记录.md`
- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify-20轮质量整改复测记录.md`

20 轮深度测试暴露的长轮次质量问题见：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-08-P2-Brainstorm-v1-Dify-20轮深度测试报告.md`
