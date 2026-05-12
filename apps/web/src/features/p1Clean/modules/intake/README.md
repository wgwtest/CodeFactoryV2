# 资料接入模块

职责：围绕一个 `archiveId` 选择资料来源、扫描文件、解析预检，并生成可供抽取运行使用的 `documentSetId`。

边界：
- 可以调用文档列表、文档导入、抽取入队 API。
- 不编辑策略规则。
- 不读取抽取运行内部事件流。
- 不写发布候选或正式知识。

输入合同：
- `archiveId`
- 可选 `policyPackageVersionId`

输出合同：
- `documentSetId`
- `documents[]`：`document_id`、`title`、`file_name`、`file_type`、`source_path`、`parse_status`、`parse_error`、`segment_count`、`anchor_count`、`can_enter_runtime`。
- 文档集合摘要：文档数、解析完成数、解析失败数、待解析数、可进入运行数、阻断数。
- 解析预检摘要：格式可用性、结构可用性、是否可进入抽取运行。

API 适配：
- 页面只从 `api.ts` 调用 `getIntakeSnapshot`、`importArchiveDocument`、`extractKnowledgeArchive`。
- `viewModel.ts` 负责从 W1 intake 合同推导文档集合摘要和解析预检摘要。

测试入口：
- `testEntry.ts`
- `apps/web/src/test/p1CleanIntakePage.test.tsx`
