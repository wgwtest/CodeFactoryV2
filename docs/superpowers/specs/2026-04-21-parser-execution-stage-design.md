# Parser Execution 真实阶段执行设计

## 文档目的

这份文档专门说明 `Parser Execution` 阶段如何在当前系统里落成**真实阶段执行与持久化**，并说明它与已经落地的三个阶段、以及后续要推进的中间阶段之间的关系。

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

本次只把第 3 阶段 `parser_execution` 做成真实阶段对象，不改变整体顺序。

## 当前已真实落地的阶段

到目前为止，已真实执行与持久化的阶段是：

- `asset_intake`
- `parser_execution`
- `evidence_pack`
- `quality_policy_evaluation_governance_gate`

它们的共性是：

- 会在抽取主链里被主动写入 stage snapshot
- 单文档 runtime 接口优先读取这些真实 snapshot
- 不存在 snapshot 时，runtime 层才退回派生映射

## Parser Execution 的阶段定位

`Parser Execution` 对应蓝图中的第 3 阶段，回答的问题是：

- 当前文档实际使用了哪个解析引擎
- 解析任务产出了多少页、多少结构片段
- 结构片段的类型分布是什么
- 哪些结构片段会成为后续统一文档对象的来源

它不是“解析路由”阶段：

- `parser_router` 负责解释“为什么选这个解析器”
- `parser_execution` 负责记录“这个解析器真正产出了什么”

## 真实执行入口

当前这三个入口都会写入真实的 `parser_execution` 阶段快照：

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

执行方式分两类：

### 1. build_archive

对 artifact manifest 里的每个文档，如果存在 `source_file_path`，就会：

1. 使用 `ParsingService(formal_extraction_mode=True).parse_file(...)`
2. 拿到真实 `ParsedDocument`
3. 调用 `build_parser_execution_snapshot(...)`
4. 落盘到 document runtime repository

这是对已有 NAS 测试知识库最直接的真实数据复用方式。

### 2. formalize_document / import_document

这两条链路在构建 `SourceDocument` 时已经持有解析结果，所以不会再重复从文件重跑解析，而是：

1. 把 `SourceDocument` 中已有的 `parser_name / segment_count / segments`
2. 转成一个 `ParsedDocument`
3. 调用 `build_parser_execution_snapshot(...)`
4. 落盘到 document runtime repository

这样能避免测试里因为上传伪造文件内容而导致再次解析失败，也能减少重复工作。

## 当前真实输入

`build_parser_execution_snapshot(...)` 当前吃到的输入是：

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

对于 `formalize_document / import_document`，当前会补一个派生的 `parser_version="derived"`，表示它来自当前内存中的解析产物，而不是重新走独立解析任务。

## 当前真实输出

当前真实持久化的是一个 `RuntimeStageSnapshot`，阶段 ID 固定为：

- `parser_execution`

### 真实节点

当前必写入的核心节点：

- `Parser Task`
- `Parser Engine`
- `Parsed Pages`
- `Parsed Blocks`
- `Structure Summary`

如果解析出了结构片段，还会额外写入最多前 6 个：

- `parsed_segment`

如果没有产出结构片段，会额外写入：

- `Parsing Warning`

### 真实边

当前必写入的核心边：

- `executed_by`
- `parsed_to`
- `extracts`
- `contains`

如果有片段节点，还会补：

- `Structure Summary -> parsed_segment_i`

## 观察窗语义

### 阶段视角

当前展示：

- 当前解析器
- parser version
- page count
- segment count
- block type distribution
- 阶段实时流

### 节点视角

当前提供两类真实节点观察窗：

- `Parser Engine`
- `Parsed Blocks`

其中 `Parsed Blocks` 会展示：

- 片段总数
- 页数
- 最多前三条样例片段

### 边视角

当前提供一条真实边观察窗：

- `parsed_to`

用于表达：

- 解析任务如何生成页级解析对象
- 当前页/片段统计

## 当前局限

`Parser Execution` 虽然已经变成真实阶段，但仍然有边界：

1. 还没有独立持久化页级对象
   - 现在是 `Parsed Pages` 组节点
   - 不是逐页 `Parsed Page` 节点全量落盘

2. 还没有独立持久化表格/图像对象
   - 当前图谱以 `Parsed Blocks` 和 `parsed_segment` 为主

3. `build_archive` 路径下会重复跑一次解析
   - 这是为了优先把真实阶段对象建立起来
   - 后面可以再复用 builder 链里的解析结果，减少重复工作

4. `parser_router` 仍未真实化
   - 现在只是真实化了解析执行，不是真实化了解析选择原因

## 为什么下一批还是按原顺序推进

在 `Parser Execution` 做实之后，下一批建议仍然是：

1. `unified_document_object`
2. `evidence_constructor`
3. `evidence_graph_chunk_layer`
4. `canonical_knowledge`

原因是：

- `parser_execution` 的真实输出正好是 `unified_document_object` 的稳定输入
- `unified_document_object -> evidence_constructor -> evidence_graph_chunk_layer`
  这条链是后面 `evidence_pack` 真正去掉派生重建的必要前提
- `canonical_knowledge` 做实后，`quality_gate` 才能从“真实 gate snapshot + 部分派生 item”继续升级成“完全真实的 canonical 输入”

而 `parser_router` 仍然建议放在再下一轮：

- 它更偏策略和选择解释
- 不像 `parser_execution` 这样能直接落稳定对象

## 与 NAS 测试知识库的关系

这次 `build_archive(...)` 路径优先支持从已有知识库文档源路径重新构建 `parser_execution` snapshot，本质上就是把你现在已经做成知识库的 NAS 测试数据，作为轻量原始材料来反向建立真实阶段对象。

这一步的意义是：

- 不需要等待全新引擎完全重写
- 可以直接拿现有 NAS 测试库验证 `parser_execution` 的真实阶段对象
- 能为后续 `unified_document_object / evidence_constructor / evidence_graph_chunk_layer` 提供连续可用的输入
