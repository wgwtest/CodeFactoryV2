# 知识成果查看模块

## 边界

- 拥有 `/p1/archives/:archiveId/results`。
- 面向终端使用者查看已经抽取出的知识对象、关系、证据、来源文档和当前入库状态。
- 不启动抽取、不编辑策略、不执行治理确认、不暴露系统间接口。

## 输入

- `archiveId`
- `publicationSnapshotId`

## 读取接口

- `getArchiveSummary`
- `getArchiveGraph`
- `getArchiveEntities`
- `getArchiveEvents`
- `getArchiveProcesses`
- `getArchiveItemDetail`
- `getArchivePublication`

## 验收

- 用户进入单知识库后能从顶部导航进入“知识成果”。
- 页面能明确标识当前展示的是抽取工作态、发布候选态还是正式入库态。
- 页面能查看知识对象、关系边、证据摘录、来源文档和对象详情。
