# Unified Document Object 真实阶段执行设计

## 文档目的

这份文档专门说明 `Unified Document Object` 阶段如何在当前系统里落成**真实阶段执行与持久化**，并说明它与已落地阶段、以及后续要推进的中间对象阶段之间的关系。

当前系统的目标仍然严格对齐 13 阶段蓝图：

1. `asset_intake`
2. `parser_router`
3. `parser_execution`
4. `unified_document_object`
5. `evidence_constructor`
6. `evidence_graph_chunk_layer`
7. `evidence_pack`
8. `concept_candidate_review`
9. `relation_review_family_normalization`
10. `definition_summary_conflict_consolidation`
11. `canonical_knowledge`
12. `quality_policy_evaluation_governance_gate`
13. `indexes_snapshots_apis`

本次只把第 4 阶段 `unified_document_object` 做成真实阶段对象，不改变整体顺序。

## 当前已真实落地的阶段

到目前为止，已真实执行与持久化的阶段是：

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

它们的共性是：

- 会在抽取主链里被主动写入 stage snapshot
- 单文档 runtime 接口优先读取这些真实 snapshot
- 不存在 snapshot 时，runtime 层才退回派生映射

## Unified Document Object 的阶段定位

`Unified Document Object` 对应蓝图中的第 4 阶段，回答的问题是：

- 解析结果如何收敛为稳定的统一文档对象
- 当前文档形成了多少统一章节、多少统一段落
- 哪些统一对象会成为后续证据构造的输入
- 规范化决策是基于哪一版解析产物生成的

它不负责：

- 解释“为什么选了某个解析器”，那是 `parser_router`
- 记录“解析器产出了多少页和块”，那是 `parser_execution`
- 生成证据单元和锚点，那是 `evidence_constructor`

## 真实执行入口

当前这三个入口都会写入真实的 `unified_document_object` 阶段快照：

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

执行方式分两类：

### 1. build_archive

对 artifact manifest 里的每个文档，如果存在 `source_file_path`，会：

1. 使用 `ParsingService(formal_extraction_mode=True).parse_file(...)`
2. 拿到真实 `ParsedDocument`
3. 先写入 `parser_execution`
4. 再复用同一份 `ParsedDocument` 调用 `build_unified_document_object_snapshot(...)`
5. 落盘到 document runtime repository

这样可以避免为统一文档对象阶段再单独重复解析一次。

### 2. formalize_document / import_document

这两条链路在构建 `SourceDocument` 时已经持有解析结果，所以不会重新读取文件，而是：

1. 把 `SourceDocument` 中已有的 `parser_name / segment_count / segments`
2. 转成一个 `ParsedDocument`
3. 先写入 `parser_execution`
4. 再写入 `unified_document_object`

这样能让上传链、正式并入链和整库抽取链共享同一套阶段契约。

## 当前真实输入

`build_unified_document_object_snapshot(...)` 当前吃到的输入是：

- `archive_id`
- `document_id`
- `document_title`
- `file_type`
- `ParsedDocument`

其中 `ParsedDocument` 至少包含：

- `parser_name`
- `parser_version`
- `segments`
- `metadata`

在当前 NAS 轻量数据场景里，最关键的是 `segments`：

- `heading`
- `content`
- `anchor`
- `block_type`

这些字段足以先构造第一版统一文档对象，而不用等完整 parser router / layout object 全部落地。

## 当前真实输出

当前真实持久化的是一个 `RuntimeStageSnapshot`，阶段 ID 固定为：

- `unified_document_object`

### 真实节点

当前必写入的核心节点：

- `Unified Document`
- `Normalization Decision`
- `Unified Sections`
- `Unified Paragraphs`

另外还会补入：

- 最多 4 个 `Unified Section`
- 最多 6 个 `Unified Paragraph`
- 没有解析片段时补 `Normalization Warning`

### 真实边

当前必写入的核心边：

- `normalized_to`
- `contains`（文档 -> 章节集合）
- `contains`（文档 -> 段落集合）

另外还会补入：

- `contains`（章节集合 -> 章节）
- `contains`（段落集合 -> 段落）
- `contains`（章节 -> 段落）
- 没有解析片段时补 `warned_by`

## 当前观察窗语义

### 阶段视角

阶段视角回答：

- 当前文档是否已经形成统一文档对象
- 当前有多少章节、多少段落
- 当前规范化过程用的是哪一个 parser 输出

当前固定展示：

- 实时流：
  - parser output 正在归并
  - 统一对象 ready / warning
- 结构化摘要：
  - `document_title`
  - `section_count`
  - `paragraph_count`
  - `parser_name`
  - `parser_version`

### 节点视角

当前重点支持的节点视角：

- `Unified Document`
- `Normalization Decision`
- `Unified Sections`
- 若干 `Unified Section`
- 若干 `Unified Paragraph`

节点视角回答：

- 这个统一对象是什么
- 它来自哪一类解析产物
- 它当前包含多少子对象
- 它能否继续进入证据构造

### 边视角

当前重点支持的边视角：

- `normalized_to`
- `contains`

边视角回答：

- 这条关系是如何把规范化决策落成统一文档对象的
- 章节和段落是如何被组织起来的

## 当前局限

当前实现仍然是第一版，局限包括：

- 章节划分仍主要依赖 `heading` 去重，而不是完整结构恢复
- 段落对象目前只持久化前 6 个样例节点，不是全量段落树
- 还没有落独立的 `Unified Table` / `Unified Figure`
- 还没有把 parser execution 的页级对象和 unified 对象之间做更细的映射边

这些局限不会影响当前目标：先把统一文档对象做成真实阶段对象，并为下一步 `evidence_constructor` 提供稳定输入。

## 与后续阶段的关系

`Unified Document Object` 做实以后，后续推进顺序更自然：

1. `evidence_constructor`
   - 从统一段落对象构造证据单元、锚点和 span
2. `evidence_graph_chunk_layer`
   - 从证据单元组织 chunk 和图拓扑
3. `canonical_knowledge`
   - 等中间对象链稳定后再做规范知识对象的真实化

所以这一步的意义不是“让界面多一层展示”，而是：

**把解析结果和证据构造之间，补上一个真实存在的统一对象层。**
