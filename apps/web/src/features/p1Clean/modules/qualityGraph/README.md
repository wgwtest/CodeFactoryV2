# 质量图谱模块

职责：衡量知识概念质量、关系质量、证据覆盖、规则命中和图谱可解释性。

边界：
- 输入 `archiveId`、`runtimeSnapshotId`、`policyPackageVersionId`。
- 输出质量决策，不直接生成发布候选。
- 不编辑资料或策略。

测试入口：
- `testEntry.ts`
