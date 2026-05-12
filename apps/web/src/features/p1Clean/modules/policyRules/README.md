# 策略规则模块

职责：管理策略包版本、规则字段合同、输入输出 Schema、动作映射、RuleExecutionRecord 和规则变更影响面。

边界：
- 输出 `policyPackageVersionId`。
- 不直接接入文件。
- 不直接推进抽取运行。
- 不直接写正式知识图谱。

输入合同：
- `archiveId`

输出合同：
- `policyPackageVersionId`
- 规则合同校验状态
- ImpactSet 摘要

API 边界：
- 只能通过本目录 `api.ts` 调用策略配置与候选重算任务接口。

页面能力：
- 展示当前知识库可用策略包版本与合同状态。
- 冻结当前策略包版本。
- 编辑规则 `input_schema`、`output_schema` 与 `trace_fields`，保存为策略草稿。
- 展示规则动作映射与服务端校验错误。
- 展示 ImpactSet 摘要与 candidate-only 增量重算任务，明确不写正式知识。

测试入口：
- `testEntry.ts`
