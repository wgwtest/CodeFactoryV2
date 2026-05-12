# 抽取运行模块

职责：执行抽取任务并展示实时状态、事件流、运行图谱和运行快照。

边界：
- 输入 `archiveId`、`documentSetId`、`policyPackageVersionId`。
- 输出 `runtimeSnapshotId`。
- 不编辑策略规则。
- 不直接发布正式知识。

测试入口：
- `testEntry.ts`
