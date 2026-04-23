# /extract 已落地阶段与下一批推进阶段详细设计

## 文档目的

这份文档回答两个问题：

1. 当前 `/extract` 主链里，哪些阶段已经变成了真实执行与持久化对象，它们分别是怎么设计的。
2. 接下来准备推进的阶段有哪些，为什么按这个顺序推进，以及它们是否偏离了最初确认的 13 阶段蓝图。

这份文档只描述后端阶段执行设计，不讨论前端页面细节。

## 与最初 13 阶段蓝图的关系

当前仍然严格对齐这 13 个阶段：

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

当前没有新增额外阶段，也没有改变顺序。我们只是按“先把关键阶段做成真实对象，再逐步替换旧抽取链”的方式分批落地。

## 当前已真实落地的阶段

截至目前，已经从“runtime 映射展示”升级成“真实阶段执行与持久化”的有 6 个：

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

它们的共同特征是：

- 会在 `/extract`、`formalize_document(...)`、`import_document(...)` 的执行过程中写入真实 `stage snapshot`
- 单文档 runtime API 会优先读取这些真实 snapshot
- 如果真实 snapshot 不存在，才退回旧映射逻辑

## 已落地阶段详细设计

### 1. Asset Intake

#### 阶段定位

对应蓝图中的 `Asset Intake`。回答的问题是：

- 这篇文档从哪里来
- 如何进入当前知识库素材域
- 是否完成了归属、摘要、纳入状态和接入结果判定

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

- `archive_id`
- `archive_name`
- `document_id`
- `document_title`
- `document_path`
- `source_dir`
- `source_file_path`
- `file_type`
- `source_archive`
- `source_digest`
- `included_in_archive`
- `mode`
- `intake_timestamp`

#### 当前真实输出

阶段快照 ID：

- `asset_intake`

当前核心节点：

- `Source File`
- `Source Directory`
- `Asset Intake Task`
- `File Digest`
- `Intake Result`

当前核心边：

- `located_in`
- `submitted_to`
- `hashed_to`
- `results_in`

#### 当前观察窗语义

- 阶段视角
  - 输入文件
  - 源目录
  - 文件类型
  - digest
  - 是否纳入 archive
- 节点视角
  - `Source File`
  - `Intake Result`
- 边视角
  - `results_in`

#### 当前局限

- 还没有独立的 `Source Version`
- 还没有单独的接入失败队列对象
- 还没有把素材目录成员关系建成更完整的多节点模型

### 2. Parser Execution

#### 阶段定位

对应蓝图中的 `Parser Execution`。回答的问题是：

- 当前文档实际使用了哪个解析器
- 解析任务产出了多少页、多少结构片段
- 结构片段类型分布是什么
- 哪些解析结果会进入下一阶段的统一文档对象

它不负责解释“为什么选了这个解析器”，那是 `parser_router` 的职责。

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

统一输入是 `ParsedDocument`，具体包括：

- `parser_name`
- `parser_version`
- `segments`
- `metadata`

其中：

- `build_archive(...)` 会从真实源文件重新调用 `ParsingService.parse_file(...)` 获取 `ParsedDocument`
- `formalize_document(...)` 和 `import_document(...)` 会从现有 `SourceDocument` 派生出 `ParsedDocument`

#### 当前真实输出

阶段快照 ID：

- `parser_execution`

当前核心节点：

- `Parser Task`
- `Parser Engine`
- `Parsed Pages`
- `Parsed Blocks`
- `Structure Summary`
- 最多前 6 个 `parsed_segment`
- 可选 `Parsing Warning`

当前核心边：

- `executed_by`
- `parsed_to`
- `extracts`
- `contains`

#### 当前观察窗语义

- 阶段视角
  - 当前解析器
  - parser version
  - page count
  - segment count
  - structure distribution
- 节点视角
  - `Parser Engine`
  - `Parsed Blocks`
- 边视角
  - `parsed_to`

#### 当前局限

- 还没有全量页级对象落盘
- 还没有表格/图像对象独立建模
- `build_archive(...)` 路径会重复跑一次解析，后面可以与 builder 结果复用
- `parser_router` 仍未真实化

更多细节见：

- [2026-04-21-parser-execution-stage-design.md](./2026-04-21-parser-execution-stage-design.md)

### 3. Unified Document Object

#### 阶段定位

对应蓝图中的 `Unified Document Object`。回答的问题是：

- 解析结果如何收敛为稳定的统一文档对象
- 当前文档形成了多少统一章节、多少统一段落
- 哪些统一对象会成为后续证据构造的输入

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

统一输入是 `ParsedDocument`，重点字段包括：

- `parser_name`
- `parser_version`
- `segments`
- `metadata`

#### 当前真实输出

阶段快照 ID：

- `unified_document_object`

当前核心节点：

- `Unified Document`
- `Normalization Decision`
- `Unified Sections`
- `Unified Paragraphs`
- 若干 `Unified Section / Unified Paragraph`

当前核心边：

- `normalized_to`
- `contains`

#### 当前观察窗语义

- 阶段视角
  - 统一对象是否 ready
  - 章节/段落数量
  - 规范化来源 parser
- 节点视角
  - `Unified Document`
  - `Normalization Decision`
  - `Unified Sections`
- 边视角
  - `normalized_to`
  - `contains`

#### 当前局限

- 章节划分仍主要依赖 `heading` 去重
- 当前只持久化样例级章节与段落节点，不是全量树
- 还没有独立的 `Unified Table` / `Unified Figure`

### 4. Evidence Constructor

#### 阶段定位

对应蓝图中的 `Evidence Constructor`。回答的问题是：

- 统一文档对象如何被拆成可追溯证据单元
- 每个证据单元绑定到了哪些段落、锚点与跨度
- 后续 `Evidence Graph / Chunk Layer` 能消费哪些真实对象，而不是只依赖 contribution evidence excerpt

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

当前输入由两部分组成：

- `ParsedDocument`
- `contribution`

也就是说，这个阶段现在已经是“真实持久化阶段”，但证据对象的原始来源仍然会参考旧 contribution 中的 evidence excerpt，再把它们挂回真实 parser segment。

#### 当前真实输出

阶段快照 ID：

- `evidence_constructor`

当前核心节点：

- `Evidence Constructor`
- `Evidence Units`
- `Evidence Anchors`
- `Evidence Spans`
- `Source Paragraphs`
- 若干 `Evidence Unit / Anchor / Span / Source Paragraph`

当前核心边：

- `results_in`
- `anchored_at`
- `spans`
- `evidence_from`
- `contains`

#### 当前观察窗语义

- 阶段视角
  - 当前 evidence unit / anchor / span 数量
  - parser 与 segment 来源
- 节点视角
  - `Evidence Unit`
  - `Evidence Anchor`
  - `Source Paragraph`
- 边视角
  - `results_in`
  - `anchored_at`
  - `evidence_from`

#### 当前局限

- 证据单元仍主要由 contribution evidence excerpt 驱动
- evidence 与 parser segment 仍使用启发式匹配
- 还没有独立持久化 `Evidence Span` 对象仓

### 5. Evidence Pack

#### 阶段定位

对应蓝图中的 `Evidence Pack`。回答的问题是：

- 当前文档在进入候选知识生成前，真实被送入任务上下文的证据包是什么
- 证据如何被选择、重排、汇总
- 哪些证据对象最终支持后续概念/关系/定义生成

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

当前仍然基于已生成的 `contribution` 重建：

- `document`
- `entities`
- `events`
- `processes`
- `relations`
- `extraction`
- `evidence`

也就是说，它现在是“真实阶段持久化”，但输入仍然来自旧 contribution 层，而不是未来的独立 `Evidence Graph / Chunk Layer` 持久化对象。

#### 当前真实输出

阶段快照 ID：

- `evidence_pack`

当前核心节点：

- `Retrieval Query`
- `Evidence Pack`
- `Rerank Result`
- `Knowledge Generation Input`
- 若干 `Evidence Unit`

当前核心边：

- `selected_into`
- `reranked_to`
- `supports`

#### 当前观察窗语义

- 阶段视角
  - 证据包条数
  - candidate / relation count
  - chunking 是否启用
  - llm provider / model
- 节点视角
  - `Evidence Pack`
  - `Evidence Unit`
- 边视角
  - `selected_into`

#### 当前局限

- 还没有真实 `Chunk`
- 还没有真实 `Evidence Graph`
- `Retrieval Query` 和 `Rerank Result` 仍不是独立执行任务对象
- 当前“证据入包”仍然是 contribution-evidence 重建，不是原生证据引擎

### 6. Quality Policy Evaluation / Governance Gate

#### 阶段定位

对应蓝图中的 `Quality Policy Evaluation / Governance Gate`。回答的问题是：

- 规范知识对象如何进入质量门禁
- 命中了哪些规则
- 为什么形成告警、阻断或人工复核
- 为什么最终进入发布目标，或者停在阻断结果

#### 当前真实执行入口

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### 当前真实输入

优先使用公开知识与发布信息：

- 当前 archive 的公开知识
- 当前文档对应的知识项
- publication overview
- latest published payload

如果这些不存在，则自动退回 contribution-only 模式。

#### 当前真实输出

阶段快照 ID：

- `quality_policy_evaluation_governance_gate`

当前核心节点：

- `Rule Hit`
- `Gate Decision`
- `Knowledge Item`
- `Manual Review`
- `Blocked Result`
- `Publish Target`

当前核心边：

- `results_in`
- `evaluated_by`
- `reviewed_by`
- `blocked_by`
- `publishes_to`

#### 当前观察窗语义

- 阶段视角
  - 当前门禁状态
  - knowledge item count
  - evidence count
  - pending review count
  - current publication version
- 节点视角
  - `Rule Hit`
  - `Gate Decision`
  - `Blocked Result / Publish Target`
- 边视角
  - `results_in`
  - `blocked_by`
  - `publishes_to`

#### 当前局限

- 还没有完全接到真实 `Canonical Knowledge` 对象层
- 规则命中仍是基于当前工作态知识项重建，不是未来的原生规则执行图
- `Publish Target` 仍偏结果映射，不是完整发布流水对象

## 下一批建议推进的阶段

下一批建议优先推进这 3 个阶段：

1. `evidence_graph_chunk_layer`
2. `canonical_knowledge`
3. `parser_router`

### 推荐顺序

推荐顺序不是任意排的，而是由依赖关系决定：

1. `evidence_graph_chunk_layer`
   - 把证据单元组织成 chunk 与图谱
   - 是 `Evidence Pack` 去掉 contribution 重建的关键前提

2. `canonical_knowledge`
   - 当前 `Quality Gate` 还带有派生成分
   - 只有 canonical 做实，门禁才会真正吃到原生规范对象

3. `parser_router`
   - 它很重要，但比起中间对象层更偏“选择解释”
   - 可以在 `parser_execution` 之后补做，不会阻塞证据与 canonical 这条主线

## 暂不优先推进的阶段

暂不建议在下一批优先推进：

- `concept_candidate_review`
- `relation_review_family_normalization`
- `definition_summary_conflict_consolidation`
- `indexes_snapshots_apis`

原因是：

- 前三个阶段都依赖上游证据对象层稳定
- `indexes_snapshots_apis` 更偏最终输出层，当前还不如先把中间过程做实

## 与 NAS 测试数据的关系

当前已经做成知识库的 NAS 测试数据，适合作为这条迁移链的轻量原始材料：

- 它已经能提供稳定的文档、知识项和 contribution
- 能帮助验证 `parser_execution -> unified_document_object -> evidence_constructor -> evidence_graph_chunk_layer` 这条新链
- 不需要等完整新引擎全部重写完，才能开始验证真实阶段对象

## 当前建议

如果继续推进，我建议按这个顺序：

1. `Parser Execution` 已落地，保持不动
2. `Unified Document Object` 已落地，作为后续阶段输入
3. 继续实现 `Evidence Constructor`
4. 再实现 `Evidence Graph / Chunk Layer`
5. 之后实现 `Canonical Knowledge`
6. 最后回头补 `Parser Router`

这样既不会偏离你最初的 13 阶段设计，也能保证每一步都有稳定输入与可验证输出。
## Update 2026-04-21: evidence_graph_chunk_layer is now a real persisted stage

The following stages are now implemented as real execution stages with persisted runtime snapshots:

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

### Evidence Graph / Chunk Layer

This stage now persists a real runtime snapshot between `evidence_constructor` and `evidence_pack`.

It materializes:

- `Chunk Planning`
- `Evidence Unit Set`
- `Chunk Group`
- `Evidence Graph Layer`
- `Boundary Adjustments`
- chunk nodes
- adjacency links between chunks

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-evidence-graph-chunk-layer-stage-design.md](./2026-04-21-evidence-graph-chunk-layer-stage-design.md)

### Updated next stages

With `evidence_graph_chunk_layer` completed, the recommended next batch becomes:

1. `canonical_knowledge`
2. `parser_router`

The larger candidate/relation/definition stages should still follow after canonical objects are
realized as persisted runtime entities.

## Update 2026-04-21: canonical_knowledge is now a real persisted stage

The following stages are now implemented as real execution stages with
persisted runtime snapshots:

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

### Canonical Knowledge

This stage now persists a real runtime snapshot between `evidence_pack` and
`quality_policy_evaluation_governance_gate`.

It materializes:

- `Canonical Item Set`
- `Canonical Relation Set`
- `Merge Decisions`
- `Dropped Candidates`
- canonical item nodes
- canonical relation edges

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-canonical-knowledge-stage-design.md](./2026-04-21-canonical-knowledge-stage-design.md)

### Updated next stages

With `canonical_knowledge` completed, the recommended next batch becomes:

1. `parser_router`
2. `concept_candidate_review`
3. `relation_review_family_normalization`
4. `definition_summary_conflict_consolidation`
5. `indexes_snapshots_apis`

This keeps the implementation aligned with the original 13-stage extraction
blueprint rather than introducing a parallel pipeline.

## Update 2026-04-21: parser_router is now a real persisted stage

The following stages are now implemented as real execution stages with
persisted runtime snapshots:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

### Parser Router

This stage now persists a real runtime snapshot between `asset_intake` and
`parser_execution`.

It materializes:

- `Source File`
- `Routing Task`
- `Document Type`
- `Selected Parser`
- `Routing Decision`
- fallback `Parser Candidate` nodes
- optional `Routing Warning`

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-parser-router-stage-design.md](./2026-04-21-parser-router-stage-design.md)

### Updated next stages

With `parser_router` completed, the recommended next batch becomes:

1. `concept_candidate_review`
2. `relation_review_family_normalization`
3. `definition_summary_conflict_consolidation`
4. `indexes_snapshots_apis`

## Update 2026-04-21: concept_candidate_review is now a real persisted stage

The following stages are now implemented as real execution stages with
persisted runtime snapshots:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `concept_candidate_review`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

### Concept Candidate Review

This stage now persists a real runtime snapshot between `evidence_pack` and
`canonical_knowledge`.

It materializes:

- `Evidence Pack Input`
- `Concept Candidate Set`
- `Category Groups`
- `Alias Groups`
- candidate nodes derived from document `entities / events / processes`
- category nodes
- alias nodes
- optional warning node when no concept candidates are materialized

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-concept-candidate-review-stage-design.md](./2026-04-21-concept-candidate-review-stage-design.md)

### Updated next stages

With `concept_candidate_review` completed, the recommended next batch becomes:

1. `relation_review_family_normalization`
2. `definition_summary_conflict_consolidation`
3. `indexes_snapshots_apis`

## Update 2026-04-21: relation_review_family_normalization is now a real persisted stage

The following stages are now implemented as real execution stages with
persisted runtime snapshots:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `concept_candidate_review`
- `relation_review_family_normalization`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

### Relation Review / Family Normalization

This stage now persists a real runtime snapshot between
`concept_candidate_review` and `canonical_knowledge`.

It materializes:

- `Evidence Pack Input`
- `Relation Candidate Set`
- `Family Normalization`
- `Family Groups`
- `Alias Collisions`
- relation candidate nodes derived from document relations
- family group nodes derived from item names and aliases
- alias collision nodes when one alias maps to multiple family groups
- source/target family edges and conflict edges

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-relation-review-family-normalization-stage-design.md](./2026-04-21-relation-review-family-normalization-stage-design.md)

### Updated next stages

With `relation_review_family_normalization` completed, the recommended next
batch becomes:

1. `definition_summary_conflict_consolidation`
2. `indexes_snapshots_apis`

## Update 2026-04-21: definition_summary_conflict_consolidation is now a real persisted stage

The following stages are now implemented as real execution stages with
persisted runtime snapshots:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `concept_candidate_review`
- `relation_review_family_normalization`
- `definition_summary_conflict_consolidation`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

### Definition / Summary / Conflict Consolidation

This stage now persists a real runtime snapshot between
`relation_review_family_normalization` and `canonical_knowledge`.

It materializes:

- `Relation Review Input`
- `Definition Candidate Set`
- `Summary Candidate Set`
- `Conflict Candidate Set`
- `Consolidation Decisions`
- definition candidate nodes
- summary candidate nodes
- conflict candidate nodes
- optional warning node when no definitions or summaries are materialized

Execution entry points:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Design reference:

- [2026-04-21-definition-summary-conflict-consolidation-stage-design.md](./2026-04-21-definition-summary-conflict-consolidation-stage-design.md)

### Updated next stages

With `definition_summary_conflict_consolidation` completed, the remaining
recommended next stage is:

1. `indexes_snapshots_apis`

### 13. Indexes / Snapshots / APIs

#### Stage purpose

`indexes_snapshots_apis` is the terminal publication surface of the extraction
chain. It answers:

- whether the current document has reached a published snapshot
- which publication version is active
- whether index-layer materialization exists
- whether an API payload is ready to serve the published output

#### Current real execution entry points

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

#### Current real input

The real stage currently consumes:

- `document`
- `current_version`
- `document_published`

Where publication state is resolved from:

- `ArchiveKnowledgeService.get_publication_overview(...)`
- `JsonPublishedKnowledgeRepository.load_latest(...)`

#### Current real output

Persisted stage snapshot id:

- `indexes_snapshots_apis`

Core nodes:

- `Publication Snapshot`
- `Search / Graph Index`
- `API Payload`

Core edges:

- `indexed_as`
- `served_by`

#### Observer semantics

- Stage view
  - document publication state
  - active version label
  - snapshot/index/API readiness
- Node view
  - `Publication Snapshot`
  - `Search / Graph Index`
  - `API Payload`
- Edge view
  - `indexed_as`
  - `served_by`

#### Current limitations

- the stage still represents index materialization at a logical level rather
  than as separate backend-specific write jobs
- search index and graph index are still collapsed into one logical node
- per-backend acknowledgements are not yet persisted

#### Design reference

- [2026-04-21-indexes-snapshots-apis-stage-design.md](./2026-04-21-indexes-snapshots-apis-stage-design.md)

## Current real-stage coverage summary

The following stages are now real persisted execution stages:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `concept_candidate_review`
- `relation_review_family_normalization`
- `definition_summary_conflict_consolidation`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`
- `indexes_snapshots_apis`
