# Brainstorm v1 Dify-shaped Workflow Orchestrator

这个插件通过真实 Dify Workflow API 执行 Brainstorm v1 工作流，保留 Brainstorm v1 的核心理念：

- 先理解用户输入与需求规格章节的关系。
- 再把讨论内容沉淀为结构化决策状态。
- 然后把稳定信息投影到需求规格说明章节正文。
- 最后规划下一轮问题。

## 当前 Dify 工作流

- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- 当前已发布 Workflow ID：`9f82e359-07e2-4bbd-ae88-8ca0bb7272ef`
- 发布日期：`2026-05-11`
- 发布版本：`2026-05-10 13:54:03`
- Draft hash：`c82ff6a61f2ff7b8453c48b775e15c9c2d2293158542c405766b2f28543581bc`

本版已按 `DIFY_WORKFLOW_REFACTOR_PLAN.md` 和 `DIFY_WORKFLOW_20TURN_REMEDIATION_PLAN.md` 做工作流侧整改：

- `normalize_input` 派生上一问、上一组选项、已知事实、未闭合问题摘要和 `draft_requested`。
- `document_projection` 按事实语义投影到当前 81433 模板锚点，覆盖 `1 总则`、`2 项目概述`、`3 工程需求`、`4 运行环境要求`、`5 数据与信息要求`、`6 质量、安全与约束要求`、`7 验收准则`。
- `document_projection` 对接口、功能模块、性能、安装操作、运行环境、数据、质量安全和验收分别投影；部署分析归工程功能需求，边界/不做范围归软件定位，内网部署归运行环境，权限审计归安全权限，追溯归数据质量或质量约束。
- `branch_intent_route` 等价分支已在 Code 节点中实现，回看请求进入 `review_status`，用户要求停止追问或输出草案时进入 `draft_compose`。
- `next_interaction_planning` 已加入长轮次反重复策略，事实覆盖较充分时转入回看/成稿入口。
- `draft_compose` 会综合已知事实生成总则，并过滤已回答的模板初始问题；收束草案使用 `replace` patch 覆盖章节当前展示内容，避免旧正文与草案重复堆叠。
- `draft_compose` 补全结果复核、性能约束和验收链条，避免收束草案在 `REQ-3.6`、`REQ-5.1`、`REQ-6.2` 上只保留空占位。
- `review_status` 和 `draft_compose` 会过滤旧完成度树遗留的“组织器策略问题”噪声，保留真实待确认项。
- 收束草案将结构化事实渲染为可审阅章节段落，而不是只输出单行事实碎片。
- `normalize_output` 最终校验 `quick_options`、`document_patch`、`decision_state_delta` 的合同结构。

运行时必须提供 `DIFY_API_KEY`。插件不会在缺少 Dify 配置时降级为本地执行；缺少 API Key 或 Dify 返回结构不合格时会直接报错。`workflow.json` 仅作为 Dify 工作流结构说明和创建参考，不作为本地 fallback 执行器。

插件级 Dify 工作流整改方案见：

- `DIFY_WORKFLOW_REFACTOR_PLAN.md`
- `DIFY_WORKFLOW_20TURN_REMEDIATION_PLAN.md`

本轮整改复测证据见：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05测试/260510-1318-P2-组织器多轮整改第2轮测试记录.md`
- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05测试/260508-2109-P2-Brainstorm-v1-Dify工作流整改复测记录.md`
- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05测试/260508-0025-P2-Brainstorm-v1-Dify-20轮质量整改复测记录.md`

20 轮深度测试暴露的长轮次质量问题见：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05测试/260508-0025-P2-Brainstorm-v1-Dify-20轮深度测试报告.md`
