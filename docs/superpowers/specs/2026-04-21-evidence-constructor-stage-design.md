# Evidence Constructor 阶段详细设计

## 阶段定位

对应你最初确认的 13 阶段蓝图中的 `Evidence Constructor`。这个阶段回答的问题是：

- 统一文档对象如何被拆成可追溯的证据单元
- 每个证据单元绑定到了哪些段落与锚点
- 后续 `Evidence Graph / Chunk Layer` 能消费哪些真实对象，而不是只读 contribution 里的 evidence excerpt

它位于：

- 上游：`Unified Document Object`
- 下游：`Evidence Graph / Chunk Layer`

## 当前真实执行入口

本轮已经接入真实执行与持久化的入口：

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

也就是说：

- 旧 archive 抽取主链继续执行
- 但在执行过程中，系统会额外写入真实的 `evidence_constructor` 阶段快照
- runtime API 会优先返回这个真实快照，而不是只用映射逻辑补图

## 当前真实输入

当前 `Evidence Constructor` 的真实输入由两部分组成：

1. `ParsedDocument`
   - `parser_name`
   - `parser_version`
   - `segments`
   - 每个 segment 的：
     - `heading`
     - `content`
     - `anchor`
     - `block_type`

2. `contribution`
   - `document`
   - `entities`
   - `events`
   - `processes`
   - 各 item 下的 `evidence`

当前实现不是直接消费未来的原生 `Unified Paragraph` 表或对象仓，而是：

- 先使用真实 `ParsedDocument`
- 再从已存在的 contribution evidence 中提取证据条目
- 按匹配规则把 evidence 条目挂回 parser segment / anchor

这保证了本轮不需要推翻旧抽取链，也能先让 `Evidence Constructor` 真实落盘。

## 当前真实输出

阶段快照 ID：

- `evidence_constructor`

当前核心节点：

- `Evidence Constructor`
- `Evidence Units`
- `Evidence Anchors`
- `Evidence Spans`
- `Source Paragraphs`
- 若干 `Evidence Unit`
- 若干 `Evidence Anchor`
- 若干 `Evidence Span`
- 若干 `Source Paragraph`
- 可选 `Evidence Warning`

当前核心边：

- `results_in`
- `anchored_at`
- `spans`
- `evidence_from`
- `contains`
- 可选 `warned_by`

## 图谱语义

### 主路径

当前主路径固定为：

1. `Evidence Constructor`
2. `Evidence Units`
3. `Evidence Anchors`
4. `Evidence Spans`

它表达的是：

- 构造任务启动
- 产生证据单元集合
- 证据单元被绑定到具体锚点
- 证据文本跨度被组织成可追溯 span

### 辅助对象

为了让运行中的图谱更接近真实状态，当前实现还补了：

- `Source Paragraphs`
- 若干 `Source Paragraph`
- `Evidence Unit -> Source Paragraph`
- `Evidence Unit -> Evidence Anchor`
- `Evidence Unit -> Evidence Span`

这样在前端单文档下钻里，`Evidence Constructor` 不再只是一个摘要节点，而是可以呈现：

- 哪些证据对象是从哪些段落来的
- 每条证据如何被锚定
- 每条证据对应的文本跨度是什么

## 当前观察窗语义

### 阶段视角

阶段观察窗会展示：

- 当前证据单元数
- 当前锚点数
- 当前 span 数
- parser 名称
- segment 数
- 来源对象总数
- 实时流：
  - 开始构造
  - 构造完成 / 无法构造

### 节点视角

当前优先支持：

- `Evidence Units`
- `Evidence Anchors`
- 前 3 个 `Evidence Unit`

点击后可看到：

- 证据来源 item
- 证据 excerpt
- source kind
- anchor 信息
- 当前对象状态流

### 边视角

当前优先支持：

- `results_in`
- 第一条 `anchored_at`

点击后可看到：

- 关系类型
- 证据数量
- 边建立的语义说明

## 当前局限

这条切片已经是真实阶段执行与持久化，但仍有几处是“过渡态实现”：

1. `Evidence Unit` 仍然主要从 contribution 里的 evidence excerpt 重建
   - 不是未来完全原生的证据对象仓

2. evidence 与 parser segment 的匹配目前是启发式
   - 优先按 excerpt 和 segment content 匹配
   - 匹配不到时按位置兜底

3. 还没有独立的 `Evidence Span` 原生存储
   - 当前 span 是随 snapshot 一起生成的 runtime 对象

## 对后续阶段的意义

这一步落地后，后续阶段就不必直接从 contribution 的 evidence excerpt 起步，而可以逐步改成：

- `Evidence Graph / Chunk Layer` 直接吃真实 evidence unit / anchor / span
- `Evidence Pack` 以后改成从真实 evidence graph / chunk 挑证据，而不是现在这种 contribution 重建

所以 `Evidence Constructor` 是中间对象链条里非常关键的一环，它的真实化会直接抬高后续三个阶段的可信度：

- `Evidence Graph / Chunk Layer`
- `Evidence Pack`
- `Canonical Knowledge`
