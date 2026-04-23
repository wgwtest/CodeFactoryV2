# /extract 13 阶段后端执行迁移方案

## 目标

把当前 `/api/archives/{archive_id}/extract` 从“旧 archive 抽取链 + 新 runtime 映射展示”逐步迁移到：

- 新 13 阶段执行链
- 真实阶段对象持久化
- runtime API 优先读取真实阶段快照

本轮不是一次性重写全量引擎，而是采用分阶段替换策略。

## 当前现状

当前系统分成两层：

- 执行层
  - 仍主要走旧 archive 抽取链
  - `ArchiveExtractionService.build_archive(...)`
  - `build_archive_knowledge(...)`
  - `build_document_contribution(...)`
  - `aggregate_document_contributions(...)`
- 展示层
  - 单文档 runtime 已经走统一 13 阶段契约
  - 优先读取真实 `stage snapshot`
  - snapshot 缺失时退回映射层

## 13 阶段目标链

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

## 迁移原则

1. 先做“真实阶段留痕”，再替换旧执行逻辑  
2. 每个阶段优先沉淀：
   - `stage snapshot`
   - `graph nodes / edges`
   - `observer payload`
   - `event stream`
3. runtime API 优先读取真实快照，缺失时再退回映射
4. 先做关键阶段，验证契约正确后再铺开全部 13 个阶段

## 当前已完成

目前已经完成真实执行与持久化的阶段：

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

也就是说，当前已经有：

- 最前端接入阶段
- 一个真实解析阶段
- 一个真实统一对象阶段
- 一个关键中间阶段
- 一个关键末端门禁阶段

这四个阶段已经足以支撑：

- 新 runtime API 的真实阶段优先读取
- 单文档下钻的真实阶段体验
- 后续中间对象层的继续落地

## 当前基础设施

### A. 阶段快照仓库

- `DocumentRuntimeRepository`
- 存储路径：
  - `{archive_id}-document-runtime/{document_id}/{stage_id}.json`

支持：

- `save_stage_snapshot(...)`
- `load_stage_snapshot(...)`
- `delete_stage_snapshot(...)`

### B. runtime API 读取策略

`ArchiveDocumentRuntimeService` 的读取顺序：

1. 先读 `DocumentRuntimeRepository`
2. 有真实 snapshot 时直接返回
3. 没有时退回旧映射逻辑

## 本轮已落地阶段说明

### Asset Intake

- 入口：
  - `build_archive(...)`
  - `formalize_document(...)`
  - `import_document(...)`
- 真实节点：
  - `Source File`
  - `Source Directory`
  - `Asset Intake Task`
  - `File Digest`
  - `Intake Result`

### Parser Execution

- 入口：
  - `build_archive(...)`
  - `formalize_document(...)`
  - `import_document(...)`
- 真实节点：
  - `Parser Task`
  - `Parser Engine`
  - `Parsed Pages`
  - `Parsed Blocks`
  - `Structure Summary`
  - 若干 `parsed_segment`

### Unified Document Object

- 入口：
  - `build_archive(...)`
  - `formalize_document(...)`
  - `import_document(...)`
- 真实节点：
  - `Unified Document`
  - `Normalization Decision`
  - `Unified Sections`
  - `Unified Paragraphs`
  - 若干 `Unified Section / Unified Paragraph`

### Evidence Pack

- 入口：
  - `build_archive(...)`
  - `formalize_document(...)`
  - `import_document(...)`
- 真实节点：
  - `Retrieval Query`
  - `Evidence Pack`
  - `Rerank Result`
  - `Knowledge Generation Input`
  - 若干 `Evidence Unit`

### Quality Gate

- 入口：
  - `build_archive(...)`
  - `formalize_document(...)`
  - `import_document(...)`
- 真实节点：
  - `Rule Hit`
  - `Gate Decision`
  - `Knowledge Item`
  - `Manual Review`
  - `Blocked Result`
  - `Publish Target`

## 下一批建议推进阶段

推荐下一批按这个顺序推进：

1. `evidence_constructor`
2. `evidence_graph_chunk_layer`
3. `canonical_knowledge`
4. `parser_router`

### 为什么是这 4 个

#### 1. evidence_constructor

- 把统一文档拆成证据单元
- 是证据图和 chunk 的前置层

#### 2. evidence_graph_chunk_layer

- 把证据单元组织成真正的图与 chunk
- 是 `evidence_pack` 去掉 contribution 重建的关键

#### 3. canonical_knowledge

- 把候选层和门禁层之间的规范对象做实
- 是 `quality_gate` 去掉派生成分的关键

#### 4. parser_router

- 重要，但不阻塞中间对象链路
- 可以在 `parser_execution` 做实后再补

## 暂缓阶段

当前暂缓到再下一轮：

- `concept_candidate_review`
- `relation_review_family_normalization`
- `definition_summary_conflict_consolidation`
- `indexes_snapshots_apis`

原因：

- 前三个依赖证据链和 canonical 链先做实
- 最后一个属于发布输出层，不应早于 canonical 和 gate 的原生化

## NAS 测试数据的角色

当前已经做成知识库的 NAS 测试数据，可以继续作为这条迁移链的轻量原始材料：

- 有现成文档
- 有现成 contribution
- 有现成公开知识
- 能反向验证新阶段对象与旧产物的一致性

这意味着：

- 不需要等完整新引擎搭好才能推进
- 可以先用现有 NAS 测试库持续验证每个阶段的真实化

## 当前建议

下一步直接进入：

1. `evidence_constructor`
2. `evidence_graph_chunk_layer`

等这两段做实后，再推进：

3. `canonical_knowledge`
4. `parser_router`

这样既不偏离最初蓝图，也能保证每一步都有明确输入、明确输出和可验证的真实阶段快照。

## 关联文档

- [2026-04-21-extract-stage-detailed-design.md](./2026-04-21-extract-stage-detailed-design.md)
- [2026-04-21-parser-execution-stage-design.md](./2026-04-21-parser-execution-stage-design.md)
- [2026-04-21-single-document-runtime-contract-design.md](./2026-04-21-single-document-runtime-contract-design.md)
## Update 2026-04-21: evidence_graph_chunk_layer completed

The real execution chain now includes these persisted stages:

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

`evidence_graph_chunk_layer` is no longer part of the “next batch”; it now runs during:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

and persists a stage snapshot consumed by the runtime API.

Design reference:

- [2026-04-21-evidence-graph-chunk-layer-stage-design.md](./2026-04-21-evidence-graph-chunk-layer-stage-design.md)

## Updated next batch

The recommended next stages are now:

1. `canonical_knowledge`
2. `parser_router`

Candidate review, relation normalization, definition/conflict consolidation, and publish-facing
stages still remain downstream of canonical object realization.
## Update 2026-04-21: canonical_knowledge is now part of the real stage chain

The migration baseline now includes these real persisted stages:

- `asset_intake`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

This means the current chain now has a real normalized object layer before
governance, instead of jumping directly from evidence-pack-level derived data
into quality-gate evaluation.

### Immediate implications

- single-document runtime can prefer a persisted canonical stage snapshot
- governance-oriented runtime views can anchor on canonical objects rather than
  only on derived contribution-level items
- the next migration focus should move to:
  - `parser_router`
  - `concept_candidate_review`
  - `relation_review_family_normalization`
  - `definition_summary_conflict_consolidation`
  - `indexes_snapshots_apis`

This preserves the original target flow:

`Asset Intake -> Parser Router -> Parser Execution -> Unified Document Object -> Evidence Constructor -> Evidence Graph / Chunk Layer -> Evidence Pack -> Concept Candidate Review -> Relation Review / Family Normalization -> Definition / Summary / Conflict Consolidation -> Canonical Knowledge -> Quality Policy Evaluation / Governance Gate -> Indexes / Snapshots / APIs`

## Update 2026-04-21: parser_router completed

The migration baseline now includes these real persisted stages:

- `asset_intake`
- `parser_router`
- `parser_execution`
- `unified_document_object`
- `evidence_constructor`
- `evidence_graph_chunk_layer`
- `evidence_pack`
- `canonical_knowledge`
- `quality_policy_evaluation_governance_gate`

`parser_router` is no longer a deferred stage. The runtime contract now records:

- file type classification
- routing task
- selected parser
- fallback parser candidates
- routing decision

and persists those objects during:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

This keeps the implementation aligned with the original 13-stage design by
making parser selection observable before parser execution begins.

## Update 2026-04-21: concept_candidate_review completed

The migration baseline now includes these real persisted stages:

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

`concept_candidate_review` is no longer only a derived runtime view. The
runtime chain now persists:

- evidence-pack input
- concept candidate set
- category groups
- alias groups
- candidate nodes derived from document entities / events / processes
- category and alias edges that can be inspected in the observer

This preserves the original stage order:

`... -> Evidence Pack -> Concept Candidate Review -> Canonical Knowledge -> Quality Policy Evaluation / Governance Gate -> ...`

Design reference:

- [2026-04-21-concept-candidate-review-stage-design.md](./2026-04-21-concept-candidate-review-stage-design.md)

## Updated next batch

With `concept_candidate_review` completed, the remaining recommended next
stages are:

1. `relation_review_family_normalization`
2. `definition_summary_conflict_consolidation`
3. `indexes_snapshots_apis`

## Update 2026-04-21: relation_review_family_normalization completed

The migration baseline now includes these real persisted stages:

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

`relation_review_family_normalization` is no longer only a derived runtime
view. The runtime chain now persists:

- evidence-pack input
- relation candidate set
- family normalization object
- family group nodes
- alias collision nodes
- source/target family edges
- conflict edges linked to alias collisions

This preserves the original target flow:

`... -> Evidence Pack -> Concept Candidate Review -> Relation Review / Family Normalization -> Definition / Summary / Conflict Consolidation -> Canonical Knowledge -> Quality Policy Evaluation / Governance Gate -> ...`

Design reference:

- [2026-04-21-relation-review-family-normalization-stage-design.md](./2026-04-21-relation-review-family-normalization-stage-design.md)

## Updated next batch

With `relation_review_family_normalization` completed, the remaining
recommended next stages are:

1. `definition_summary_conflict_consolidation`
2. `indexes_snapshots_apis`

## Update 2026-04-21: definition_summary_conflict_consolidation completed

The migration baseline now includes these real persisted stages:

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

`definition_summary_conflict_consolidation` is no longer only a derived runtime
view. The runtime chain now persists:

- relation-review input
- definition candidate set
- summary candidate set
- conflict candidate set
- consolidation decision group
- definition candidate nodes
- summary candidate nodes
- conflict candidate nodes

This preserves the original target flow:

`... -> Relation Review / Family Normalization -> Definition / Summary / Conflict Consolidation -> Canonical Knowledge -> Quality Policy Evaluation / Governance Gate -> ...`

Design reference:

- [2026-04-21-definition-summary-conflict-consolidation-stage-design.md](./2026-04-21-definition-summary-conflict-consolidation-stage-design.md)

## Updated next batch

With `definition_summary_conflict_consolidation` completed, the only remaining
recommended real stage to implement is:

1. `indexes_snapshots_apis`

## Update 2026-04-21: indexes_snapshots_apis is now a real persisted stage

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
- `indexes_snapshots_apis`

`indexes_snapshots_apis` is no longer only a derived runtime view. The runtime
chain now persists:

- publication snapshot node
- search / graph index node
- API payload node
- `indexed_as` relation
- `served_by` relation

This preserves the original target flow:

`... -> Canonical Knowledge -> Quality Policy Evaluation / Governance Gate -> Indexes / Snapshots / APIs`

Design reference:

- [2026-04-21-indexes-snapshots-apis-stage-design.md](./2026-04-21-indexes-snapshots-apis-stage-design.md)

## Resulting migration state

All 13 stages from the original extraction blueprint now have real persisted
runtime snapshots.
