# 发布输出模块

职责：生成发布候选快照、展示治理确认状态、区分候选态和正式入库态。

边界：
- 输入 `archiveId`、`runtimeSnapshotId`。
- 输出 `publicationSnapshotId`。
- 不提供系统间正式知识供应接口。
- 不回写抽取运行状态。

测试入口：
- `testEntry.ts`
