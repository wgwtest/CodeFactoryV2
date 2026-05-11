# P2 Brainstorming Lab 模板目标树与 Turn 审计自检记录

**时间：** 2026-05-01 20:35

## 1. 本轮修复目标

针对实测截图中暴露的问题，本轮修复三项：

1. 需求规格完成度树不再使用代码手写的两层浅表清单，改为从需求规格模板 `sections / clauses` 生成。
2. Provider 提问不再允许和 `active_spec_node_id` 脱节，服务端强制把 `document_patch`、`next_question` 和快捷选项对齐到目标节点。
3. `当前 Turn` Tab 从普通输入输出查看页升级为决策审计页，展示本轮为什么问、是否闭环、为什么进入下一节点。

## 2. 已覆盖行为

- 创建 Lab 会话后，`active_spec_node_id` 为 `SPEC-REQ-1.1`。
- 完成度树根为 `需求规格说明完成度树（81433号）`。
- 叶子节点来自模板条款，例如 `REQ-3.1 用户与角色`。
- 第一轮回答关闭 `SPEC-REQ-1.1` 后，下一节点进入 `SPEC-REQ-2.1`。
- 第二轮回答关闭 `SPEC-REQ-2.1` 后，下一问进入 `REQ-3.1 用户与角色`，并给出用户角色相关快捷选项。
- `BrainstormTurn` 返回 `active_spec_node`、`decision_basis`、`closure_decision`、`next_node_decision`。
- 前端 `当前 Turn` Tab 展示当前目标节点、本轮决策依据、闭环判断和下一节点选择。

## 3. 验证命令

```bash
uv run pytest apps/api/tests/test_brainstorm_api.py -q
corepack pnpm --dir apps/web test src/test/BrainstormLabPage.test.tsx
```

## 4. 当前结论

上述两项测试已通过。后续仍需在真实 DeepSeek 调用中继续观察模型摘要质量，但章节跳转权已经收回到 `Brainstorming Service`，不再完全依赖模型自由决定下一问。
