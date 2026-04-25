# 单文档处理状态图规格

## 文档目的

本文档用于定义“抽取运行中心 / 单文档下钻视图”的主视觉模型。

这张图不再被定义为普通流程图，而被定义为：

**单文档处理状态图**

英文内部名统一为：

**Document Processing State Graph**

它的目标不是只说明“当前停在哪个阶段”，而是让用户直观看到：

1. 原文档被解析成了哪些结构对象
2. 这些结构对象如何进一步生成证据、切块和证据包
3. 候选知识、规范知识和规则判断如何被逐步形成
4. 当前阶段有哪些节点正在实时变化
5. 哪些规则正在命中、哪些对象被阻断、哪些对象等待人工复核
6. 为什么最终进入 canonical、被阻断、或进入发布候选

## 设计定位

单文档处理状态图需要同时承担 5 个任务：

1. 展示单文档主流程
2. 展示当前阶段下的详细微流程
3. 展示中间对象之间的关系
4. 展示动态状态变化与流输出联动
5. 展示判断、治理和门禁如何作用到最终知识结果

因此它不是“更细的流程链”，而是：

**以单文档为中心、以处理中间对象为节点、以状态变化为核心的动态图。**

## 设计原则

### 1. 主流程链只负责定位，不负责承载全部细节

页面顶部的主流程链用于回答：

- 现在停在哪
- 已经过了哪些阶段
- 还没进入哪些阶段

它不负责完整展示所有微处理细节。

### 2. 当前阶段必须展开成详细子图

当前高亮阶段下，必须展开成“详细微流程图”。

例如：

- 当前在 `Evidence`，就展开 `Evidence Unit / Evidence Span / Anchor / Chunk / Evidence Pack` 子图
- 当前在 `Quality Gate`，就展开 `Canonical / Rule Hit / Risk / Gate Decision` 子图

### 3. 图与流输出联动

右侧“阶段观察窗”中的流输出，不应与图分离。

流输出提到的对象、规则、阻断点，应在图中同步高亮。

### 4. 节点建模要尽量完整，页面展示按上下文裁剪

模型层应尽量完整建模。

但具体到页面实例时：

- 只实例化实际出现的节点
- 当前阶段相关节点优先展开
- 非当前阶段节点可以折叠成组
- 大量重复节点可被聚合成摘要节点

### 5. 单文档页必须比其他两层更细

全局并行运行视图看编排。

单知识库运行视图看流转。

单文档下钻视图才进入本文档定义的详细动态图。

### 6. 不是一张图，而是一组“阶段图谱”

单文档下钻视图不应该只有一张通用图谱。

正确做法是：

- 每个主阶段都有自己独立的一套图谱内容与关系语义
- 默认显示当前运行阶段对应的图谱
- 点击已完成阶段后，切换到对应阶段的图谱
- 各阶段图谱共享一套交互语言，但不共享同一套内容结构

因此，单文档页的主视图应该被理解为：

**按阶段切换的一组动态图谱**

而不是：

**一张被反复复用的通用图谱**

### 7. 节点和边都必须可点击

在单文档下钻视图里，点击交互不应只发生在阶段节点上。

必须支持：

- 点击图中的节点
- 点击图中的边
- 点击聚合节点
- 点击风险节点

点击后，右侧观察窗应切换为该对象的上下文，而不是继续停留在泛化阶段说明。

### 8. 右侧观察窗必须支持三种上下文模式

右侧观察窗不应只是一种“阶段观察窗”。

它至少要支持三种模式：

1. `阶段模式`
   - 默认模式
   - 当用户只切阶段但未选中图中对象时显示

2. `节点模式`
   - 点击某个节点后显示
   - 展示该节点的实时处理流、状态、输入输出、风险、关联对象

3. `边模式`
   - 点击某条边后显示
   - 展示这条关系是如何形成、当前状态、涉及对象、命中规则与解释

因此，右侧区域更准确的叫法应为：

**对象观察窗**

其中“阶段观察窗”只是它的默认模式之一。

## 总体视图骨架

单文档页采用 `顶部定位 + 上部概要链 + 中部状态图 + 右侧观察窗 + 底部辅助带` 的布局。

```text
+------------------------------------------------------------------------------------------------------------------+
| 顶部：文档身份 / 当前阶段 / 当前状态 / 返回动作                                                                    |
+------------------------------------------------------------------------------------------------------------------+
| 上部：文档概要主流程链                                                                                            |
+------------------------------------------------------------------------------------------------------------------+
| 中部左：单文档处理状态图                                                                                          |
| 中部右：阶段观察窗（流输出优先）                                                                                  |
+------------------------------------------------------------------------------------------------------------------+
| 底部：证据入口 / 规则入口 / 产物入口 / 关联对象入口                                                               |
+------------------------------------------------------------------------------------------------------------------+
```

## 主流程阶段骨架

单文档页顶部的概要链建议固定为：

1. Asset Intake
2. Parser
3. Unified Document
4. Evidence
5. Evidence Pack
6. Knowledge Review
7. Canonical Knowledge
8. Quality Gate
9. Publish

其中 `Knowledge Review` 是一个概要簇，其内部可进一步展开为：

- Concept Review
- Relation / Family Review
- Definition / Conflict Review

## 阶段图谱全集

单文档页不应只支持几个代表阶段。

它应覆盖**完整处理链上的全部阶段图谱**，并允许按阶段切换查看。

这些阶段图谱共享交互语言，但图谱中的节点种类、边类型、聚焦对象和默认联动逻辑各不相同。

### 顶层阶段全集

单文档页至少应覆盖下面这 13 个顶层阶段图谱：

1. Asset Intake
2. Parser Router
3. Parser Execution
4. Unified Document Object
5. Evidence Constructor
6. Evidence Graph / Chunk Layer
7. Evidence Pack
8. Concept Candidate Review
9. Relation Review / Family Normalization
10. Definition / Summary / Conflict Consolidation
11. Canonical Knowledge
12. Quality Policy Evaluation / Governance Gate
13. Indexes / Snapshots / APIs

### 二级子阶段图谱

如果某个顶层阶段本身包含明显独立的处理子流程，也应允许进一步切入二级子阶段图谱。

第一批应支持的二级子阶段至少包括：

- Parser Execution
  - OCR
  - Layout Detection
  - Structure Reconstruction

- Evidence Constructor
  - Evidence Span Extraction
  - Evidence Anchor Binding
  - Evidence Quality Check

- Evidence Graph / Chunk Layer
  - Chunk Planning
  - Chunk Boundary Adjustment
  - Evidence Graph Linking

- Evidence Pack
  - Retrieval
  - Rerank
  - Pack Build

- Concept Candidate Review
  - Candidate Proposal
  - Candidate Support Binding
  - Candidate Risk Detection

- Relation Review / Family Normalization
  - Relation Proposal
  - Family Grouping
  - Family Normalization Decision

- Definition / Summary / Conflict Consolidation
  - Definition Proposal
  - Summary Proposal
  - Conflict Consolidation

- Quality Policy Evaluation / Governance Gate
  - Rule Evaluation
  - Warning / Block Formation
  - Manual Review Trigger
  - Gate Decision

- Indexes / Snapshots / APIs
  - Publish Candidate
  - Snapshot Build
  - API Exposure

### 1. Asset Intake 图谱

回答：

- 这篇文档如何进入知识库
- 来源、归属、接入校验如何形成
- 是否在接入阶段就被拦截

重点节点：

- Source File
- Source Version
- Source Folder
- Source Archive Membership
- Intake Task
- Intake Validation
- Intake Warning / Intake Failure

重点边：

- `belongs_to_folder`
- `belongs_to_archive`
- `validated_by`

### 2. Parser Router 图谱

回答：

- 为什么当前文档进入了哪条解析路径
- 当前解析器选择依据是什么
- 是否存在路由不确定性或人工兜底

重点节点：

- Parser Routing Decision
- Parser Capability Match
- Source File
- Source Metadata
- Intake Validation
- Intake Warning

重点边：

- `matched_by`
- `routed_to`

### 3. Parser Execution 图谱

回答：

- 路由如何选择解析器
- 解析中形成了哪些结构对象
- 哪些解析结果存在缺损或告警

重点节点：

- Parser Routing Decision
- Parser Capability Match
- Parser Task
- OCR Task
- Layout Detection Task
- Structure Reconstruction Task
- Parsed Page / Block / Table / Figure
- Parser Warning / Parser Failure

重点边：

- `routed_to`
- `matched_by`
- `parsed_to`
- `ocr_to`
- `layout_detected_to`
- `reconstructed_to`

### 4. Unified Document Object 图谱

回答：

- 原始解析对象如何被统一成标准结构
- 锚点、段、块、章节是如何建立的
- 哪些结构在标准化时丢失或告警

重点节点：

- Parsed Block
- Unified Document
- Unified Section
- Unified Block
- Unified Segment
- Unified Anchor
- Unified Reference Link
- Normalization Warning

重点边：

- `normalized_to`
- `anchored_by`
- `linked_reference_to`

### 5. Evidence Constructor 图谱

回答：

- 证据是如何从统一文档中被抽取出来的
- 哪些证据单元、锚点、上下文被建立
- 哪些证据冲突、缺口和重复被发现

重点节点：

- Evidence Extraction Task
- Evidence Scope
- Evidence Unit
- Evidence Span
- Evidence Anchor
- Evidence Window
- Evidence Context
- Evidence Citation
- Evidence Quality Check
- Evidence Warning / Conflict / Gap / Duplicate

重点边：

- `extracts_to`
- `evidence_from`
- `spans_to`
- `anchored_to`
- `contextualized_by`
- `cites`
- `quality_checked_by`
- `conflicts_with`
- `duplicates`

### 6. Evidence Graph / Chunk Layer 图谱

回答：

- 证据单元如何被切分、连接、桥接成可组合结构
- 哪些 chunk 边界被修正
- 哪些证据图连接正在形成

重点节点：

- Chunk Planning Task
- Chunk Policy
- Chunk Proposal
- Chunk
- Chunk Boundary / Adjustment
- Chunk Bridge
- Chunk Group
- Chunk Coverage Check
- Chunk Warning / Failure
- Evidence Graph Node / Edge / Cluster / Gap

重点边：

- `planned_by`
- `proposed_by`
- `split_to`
- `adjusted_by`
- `bridged_by`
- `grouped_to`
- `graph_links_to`

### 7. Evidence Pack 图谱

回答：

- 切块是如何发生的
- 证据图和证据包如何被构建
- 检索与 rerank 如何影响进入后续任务的证据

重点节点：

- Chunk Planning Task
- Chunk Policy
- Chunk Proposal
- Chunk
- Chunk Boundary / Adjustment
- Chunk Bridge
- Chunk Group
- Evidence Graph Node / Edge / Cluster / Gap
- Retrieval Task / Candidate
- Rerank Task
- Evidence Pack Build Task
- Evidence Pack
- Evidence Pack Segment
- Evidence Pack Quality Check
- Evidence Pack Warning

重点边：

- `planned_by`
- `proposed_by`
- `split_to`
- `adjusted_by`
- `bridged_by`
- `grouped_to`
- `graph_links_to`
- `retrieved_as`
- `reranked_to`
- `packed_to`
- `quality_checked_to`

### 8. Concept Candidate Review 图谱

回答：

- 证据包如何提出概念候选
- 哪些概念候选被保留、降级、丢弃
- 候选的支持关系和风险如何形成

重点节点：

- Concept Review Task
- Concept / Entity / Event / Process Candidate
- Candidate Support Set
- Candidate Risk
- Candidate Warning
- Candidate Drop Decision

重点边：

- `reviews_to`
- `proposes`
- `supports`
- `categorizes_as`
- `scopes_as`
- `drops_by`

### 9. Relation Review / Family Normalization 图谱

回答：

- 关系候选如何提出
- 家族归一如何发生
- 哪些关系和 family grouping 仍有冲突

重点节点：

- Relation Review Task
- Relation Candidate
- Family Candidate
- Alias Candidate
- Name Variant Candidate
- Family Normalization Decision
- Candidate Warning

重点边：

- `reviews_to`
- `proposes`
- `aliases_as`
- `variants_as`
- `family_normalizes_to`
- `conflicts_as`

### 10. Definition / Summary / Conflict Consolidation 图谱

回答：

- 定义、摘要、冲突整合如何形成
- 哪些定义候选被保留或挡住
- 冲突整合如何影响后续 canonical

重点节点：

- Definition Review Task
- Conflict Consolidation Task
- Definition Candidate
- Summary Candidate
- Conflict Candidate
- Candidate Support Set
- Candidate Warning
- Candidate Drop Decision

重点边：

- `reviews_to`
- `defines`
- `summarizes`
- `conflicts_as`
- `supports`
- `drops_by`

### 11. Canonical Knowledge 图谱

回答：

- 候选如何被归并成规范知识
- 别名、证据集合、来源链、风险画像如何绑定到 canonical
- 哪些归并冲突仍未解决

重点节点：

- Merge Task
- Merge Proposal
- Merge Cluster
- Merge Conflict
- Normalization Decision
- Family Normalization Decision
- Canonical Item / Entity / Event / Process / Relation / Definition / Summary
- Canonical Alias Set
- Canonical Evidence Set
- Canonical Provenance
- Canonical Risk Profile

重点边：

- `clustered_to`
- `merges_to`
- `normalizes_to`
- `family_normalizes_to`
- `forms_canonical`
- `retains_alias_set`
- `retains_evidence_set`
- `records_provenance`
- `profiles_risk`

### 12. Quality Policy Evaluation / Governance Gate 图谱

回答：

- 哪些规则组参与了判断
- 哪些对象被告警、阻断、转人工复核
- Gate Decision 是如何形成的

重点节点：

- Quality Evaluation Task
- Rule Group
- Rule Hit / Pass / Warning / Block
- Warning
- Block
- Manual Review
- Review Queue Entry
- Governance Comment
- Approval / Rejection / Merge / Edit Decision
- Gate Proposal
- Gate Decision
- Gate Reason Bundle
- Governance Audit Entry

重点边：

- `evaluated_by`
- `grouped_in_rule`
- `passes_by`
- `warned_by`
- `blocked_by`
- `reviewed_by`
- `queued_for_review`
- `commented_by`
- `approved_by`
- `rejected_by`
- `edited_by`
- `gated_by`
- `reasoned_by`
- `audited_as`

### 13. Indexes / Snapshots / APIs 图谱

回答：

- 哪些对象进入发布候选
- 哪些对象最终发布、暂缓或阻断
- 如何形成快照、追溯和对外可见结果

重点节点：

- Publish Candidate
- Publish Warning
- Published Result
- Published Snapshot Node
- API Exposure Node
- Blocked Result
- Deferred Result
- Trace Record
- Audit Record
- Diff Record

重点边：

- `publishes_to`
- `snapshotted_as`
- `exposed_to_api`
- `retained_as_blocked`
- `deferred_as`
- `traced_to`
- `diffed_to`

## 可直接画图的阶段清单

本节不是再解释“阶段回答什么”，而是把 13 个阶段继续收成可以直接用于线框绘制、真实前端建模和图谱交互定义的清单。

每个阶段都固定拆成 3 组：

- `必画核心节点`
- `必画核心边`
- `必做动态变化`

这里的“必画”不是指页面任何时刻都必须把这些对象全部平铺出来，而是指：

1. 该阶段图谱如果被展开，至少要有这些节点和边的表达方式
2. 即使某些节点被折叠、聚合、弱化，也必须在模型层和交互层存在
3. 如果某个阶段缺少这些对象，用户将无法真正看懂“这一阶段正在发生什么”

### 1. Asset Intake 阶段清单

#### 必画核心节点

- `Source File`
- `Source Version`
- `Source Folder`
- `Source Archive Membership`
- `Intake Task`
- `Intake Validation`
- `Intake Warning`
- `Intake Failure`

#### 必画核心边

- `belongs_to_folder`
- `belongs_to_archive`
- `validated_by`
- `warned_by`
- `failed_by`

#### 必做动态变化

- `Intake Task`：`queued -> running -> ready / failed`
- `Intake Validation`：从未生成到生成
- `Intake Warning / Intake Failure`：按接入结果实时追加
- `Source Archive Membership`：接入成功后建立归属关系

### 2. Parser Router 阶段清单

#### 必画核心节点

- `Source File`
- `Source Metadata`
- `Parser Routing Decision`
- `Parser Capability Match`
- `Intake Validation`
- `Intake Warning`

#### 必画核心边

- `matched_by`
- `routed_to`
- `warned_by`

#### 必做动态变化

- `Parser Capability Match`：候选解析器命中变化
- `Parser Routing Decision`：从待定到已选定
- `routed_to`：最终路由边建立或改写
- 兜底解析路径触发时生成 `Intake Warning`

### 3. Parser Execution 阶段清单

#### 必画核心节点

- `Parser Routing Decision`
- `Parser Task`
- `OCR Task`
- `Layout Detection Task`
- `Structure Reconstruction Task`
- `Parsed Page`
- `Parsed Block`
- `Parsed Table`
- `Parsed Figure`
- `Parser Warning`
- `Parser Failure`

#### 必画核心边

- `routed_to`
- `parsed_to`
- `ocr_to`
- `layout_detected_to`
- `reconstructed_to`
- `warned_by`
- `failed_by`

#### 必做动态变化

- 页级或块级解析对象持续生成
- `Parser Task / OCR Task / Layout Detection Task` 状态推进
- 新的 `Parsed Page / Parsed Block` 被追加进图
- `Parser Warning / Parser Failure` 在运行中实时挂入

### 4. Unified Document Object 阶段清单

#### 必画核心节点

- `Parsed Block`
- `Unified Document`
- `Unified Section`
- `Unified Block`
- `Unified Segment`
- `Unified Anchor`
- `Unified Reference Link`
- `Normalization Warning`

#### 必画核心边

- `normalized_to`
- `anchored_by`
- `linked_reference_to`
- `warned_by`

#### 必做动态变化

- `Unified Section / Unified Block / Unified Segment` 持续生成
- `normalized_to` 关系持续追加
- 锚点和引用链实时补全
- 标准化失败或结构缺损时追加 `Normalization Warning`

### 5. Evidence Constructor 阶段清单

#### 必画核心节点

- `Evidence Extraction Task`
- `Evidence Scope`
- `Evidence Unit`
- `Evidence Span`
- `Evidence Anchor`
- `Evidence Window`
- `Evidence Context`
- `Evidence Citation`
- `Evidence Quality Check`
- `Evidence Warning`
- `Evidence Conflict`
- `Evidence Gap`
- `Evidence Duplicate`

#### 必画核心边

- `extracts_to`
- `evidence_from`
- `spans_to`
- `anchored_to`
- `contextualized_by`
- `cites`
- `quality_checked_by`
- `conflicts_with`
- `duplicates`

#### 必做动态变化

- 新 `Evidence Unit` 连续生成
- `Evidence Span / Anchor / Citation` 持续补齐
- 证据不足、冲突、重复等风险节点动态出现
- 质量检查通过后更新 `Evidence Quality Check` 状态

### 6. Evidence Graph / Chunk Layer 阶段清单

#### 必画核心节点

- `Chunk Planning Task`
- `Chunk Policy`
- `Chunk Proposal`
- `Chunk`
- `Chunk Boundary`
- `Chunk Boundary Adjustment`
- `Chunk Bridge`
- `Chunk Group`
- `Chunk Coverage Check`
- `Chunk Warning`
- `Chunk Failure`
- `Evidence Graph Node`
- `Evidence Graph Edge`
- `Evidence Graph Cluster`
- `Evidence Graph Gap`

#### 必画核心边

- `planned_by`
- `proposed_by`
- `split_to`
- `adjusted_by`
- `bridged_by`
- `grouped_to`
- `graph_links_to`
- `warned_by`
- `failed_by`

#### 必做动态变化

- `Chunk` 在切块时连续出现
- `Chunk Boundary Adjustment` 动态插入并重连边
- `Evidence Graph Edge` 会新增、断开、重连
- `Chunk Group / Evidence Graph Cluster` 可聚合和解聚
- 覆盖率不足时生成 `Chunk Warning / Evidence Graph Gap`

### 7. Evidence Pack 阶段清单

#### 必画核心节点

- `Chunk`
- `Chunk Group`
- `Retrieval Task`
- `Retrieval Candidate`
- `Rerank Task`
- `Evidence Pack Build Task`
- `Evidence Pack`
- `Evidence Pack Segment`
- `Evidence Pack Quality Check`
- `Evidence Pack Warning`

#### 必画核心边

- `retrieved_as`
- `reranked_to`
- `packed_to`
- `quality_checked_to`
- `warned_by`

#### 必做动态变化

- `Retrieval Candidate` 检索命中不断变化
- `Rerank Task` 会导致排序重排
- `Evidence Pack Segment` 随选择结果增删
- `Evidence Pack` ready 前持续追加和剔除证据
- pack 质量不足时挂入 `Evidence Pack Warning`

### 8. Concept Candidate Review 阶段清单

#### 必画核心节点

- `Concept Review Task`
- `Concept Candidate`
- `Entity Candidate`
- `Event Candidate`
- `Process Candidate`
- `Candidate Support Set`
- `Category Candidate`
- `Scope Candidate`
- `Candidate Risk`
- `Candidate Warning`
- `Candidate Drop Decision`

#### 必画核心边

- `reviews_to`
- `proposes`
- `supports`
- `categorizes_as`
- `scopes_as`
- `warned_by`
- `drops_by`

#### 必做动态变化

- 新候选不断生成
- 类别、范围、风险标签持续补全
- `Candidate Support Set` 可能扩张或收缩
- 低质量候选被 `Candidate Drop Decision` 挂起或移除

### 9. Relation Review / Family Normalization 阶段清单

#### 必画核心节点

- `Relation Review Task`
- `Relation Candidate`
- `Family Candidate`
- `Alias Candidate`
- `Name Variant Candidate`
- `Family Normalization Decision`
- `Candidate Warning`

#### 必画核心边

- `reviews_to`
- `proposes`
- `aliases_as`
- `variants_as`
- `family_normalizes_to`
- `conflicts_as`
- `warned_by`

#### 必做动态变化

- 新关系候选生成
- family / alias / variant 关系动态补入
- 冲突关系可转入 `Candidate Warning`
- `Family Normalization Decision` 会建立、改写或撤销归一边

### 10. Definition / Summary / Conflict Consolidation 阶段清单

#### 必画核心节点

- `Definition Review Task`
- `Conflict Consolidation Task`
- `Definition Candidate`
- `Summary Candidate`
- `Conflict Candidate`
- `Candidate Support Set`
- `Candidate Warning`
- `Candidate Drop Decision`

#### 必画核心边

- `reviews_to`
- `defines`
- `summarizes`
- `conflicts_as`
- `supports`
- `warned_by`
- `drops_by`

#### 必做动态变化

- 定义、摘要、冲突候选实时追加
- `conflicts_as` 关系会新增或消解
- 支持证据集合不断补入
- 被挡住的定义候选进入 `Candidate Warning / Candidate Drop Decision`

### 11. Canonical Knowledge 阶段清单

#### 必画核心节点

- `Merge Task`
- `Merge Proposal`
- `Merge Cluster`
- `Merge Conflict`
- `Normalization Decision`
- `Family Normalization Decision`
- `Canonical Item`
- `Canonical Entity`
- `Canonical Event`
- `Canonical Process`
- `Canonical Relation`
- `Canonical Definition`
- `Canonical Summary`
- `Canonical Alias Set`
- `Canonical Evidence Set`
- `Canonical Provenance`
- `Canonical Risk Profile`

#### 必画核心边

- `clustered_to`
- `merges_to`
- `normalizes_to`
- `family_normalizes_to`
- `forms_canonical`
- `retains_alias_set`
- `retains_evidence_set`
- `records_provenance`
- `profiles_risk`

#### 必做动态变化

- 候选不断汇入 `Merge Cluster`
- `Merge Conflict` 可能出现、解除、重新生成
- 新 `Canonical Item / Relation / Definition` 形成
- 证据集、别名集、来源链和风险画像持续补全

### 12. Quality Policy Evaluation / Governance Gate 阶段清单

#### 必画核心节点

- `Quality Evaluation Task`
- `Rule Group`
- `Rule Hit`
- `Rule Pass`
- `Rule Warning`
- `Rule Block`
- `Warning`
- `Block`
- `Manual Review`
- `Review Queue Entry`
- `Governance Comment`
- `Approval Decision`
- `Rejection Decision`
- `Merge Decision`
- `Edit Decision`
- `Gate Proposal`
- `Gate Decision`
- `Gate Reason Bundle`
- `Governance Audit Entry`
- `Blocked Result`
- `Publish Candidate`

#### 必画核心边

- `evaluated_by`
- `grouped_in_rule`
- `passes_by`
- `warned_by`
- `blocked_by`
- `reviewed_by`
- `queued_for_review`
- `commented_by`
- `approved_by`
- `rejected_by`
- `edited_by`
- `gated_by`
- `reasoned_by`
- `audited_as`
- `results_in`

#### 必做动态变化

- 新 `Rule Hit / Rule Warning / Rule Block` 持续追加
- `Manual Review` 和 `Review Queue Entry` 可被动态创建
- `Gate Decision` 会在运行中从 pending 切到 warning / blocked / passed
- `Blocked Result / Publish Candidate` 只在门禁结论稳定后生成
- 规则命中、人工复核、最终门禁之间的主路径必须高亮联动

### 13. Indexes / Snapshots / APIs 阶段清单

#### 必画核心节点

- `Publish Candidate`
- `Publish Warning`
- `Published Result`
- `Published Snapshot Node`
- `API Exposure Node`
- `Blocked Result`
- `Deferred Result`
- `Trace Record`
- `Audit Record`
- `Diff Record`

#### 必画核心边

- `publishes_to`
- `snapshotted_as`
- `exposed_to_api`
- `retained_as_blocked`
- `deferred_as`
- `traced_to`
- `diffed_to`

#### 必做动态变化

- `Publish Candidate` 转入发布或延后
- 快照、API、追溯、diff 结果按顺序生成
- 被阻断对象保留在 `Blocked Result`
- 延迟发布对象转入 `Deferred Result`

## 第一版绘图落地规则

为了让这份清单能直接服务后续 Pencil 线框和真实开发，这里补 5 条落地规则：

### 1. 每个阶段至少画一条主路径

主路径必须能回答：

- 当前阶段最核心的输入对象是什么
- 当前阶段最核心的判断/加工是什么
- 当前阶段最核心的输出对象是什么

### 2. 每个阶段至少有一个上下文簇

上下文簇用来承载：

- 辅助证据
- 风险对象
- 规则对象
- 待补对象

不能让图只剩一条光杆主链。

### 3. 每个阶段至少有一个“结果对象”

结果对象可以是：

- `Warning`
- `Block`
- `Manual Review`
- `Blocked Result`
- `Published Result`

如果一个阶段没有结果对象，用户无法判断这一步最终产生了什么影响。

### 4. 节点与边都必须能进入对象观察窗

后续设计和开发时，任何被画出来的：

- 主节点
- 风险节点
- 决策节点
- 主路径边
- 关键关系边

都必须可以点击，并进入右侧对象观察窗。

### 5. 动态变化对象要优先于静态说明对象

如果画布空间有限，优先保留：

- 会新增的节点
- 会断开的边
- 会重连的边
- 会切状态的判断对象

而不是优先保留静态说明类标签。

## 节点宇宙总表

以下节点按“来源对象 -> 处理对象 -> 证据对象 -> 知识对象 -> 判断对象 -> 输出对象”组织。

不是每篇文档都会出现所有节点，但模型层必须支持这些节点。

---

## 一、来源与接入对象节点

### 1. Source File

- 含义：原始文件本体
- 例子：`SV-2翻译.docx`

### 2. Source Version

- 含义：原始文件版本
- 用途：区分同名文件的不同导入批次或修订版

### 3. Source Folder

- 含义：素材目录节点
- 用途：表示该文档所属源目录

### 4. Source Archive Membership

- 含义：文档与知识库的归属关系节点

### 5. Source Metadata

- 含义：来源目录、导入时间、摘要、文件大小、MIME、hash 等元信息

### 6. Source Attachment

- 含义：附件对象
- 用途：表示文档携带的嵌入附件

### 7. Source Page

- 含义：原文件中的页级对象

### 8. Source Section

- 含义：原文档中的章节对象

### 9. Source Subsection

- 含义：更细的节对象

### 10. Source Paragraph

- 含义：原文档段落对象

### 11. Source Sentence

- 含义：段落中的句级对象

### 12. Source Bullet

- 含义：项目符号对象

### 13. Source Table

- 含义：原文中的表格对象

### 14. Source Table Row

- 含义：原文表格行对象

### 15. Source Table Cell

- 含义：原文表格单元格对象

### 16. Source Figure

- 含义：图示、图片、流程图原始对象

### 17. Source Figure Region

- 含义：图中的局部区域对象

### 18. Source Caption

- 含义：图表标题、图注、表注

### 19. Source Footnote

- 含义：脚注、注释

### 20. Source HeaderFooter

- 含义：页眉页脚对象

### 21. Source Reference

- 含义：参考文献、引用、交叉引用对象

### 22. Source Appendix

- 含义：附录对象

### 23. Source Glossary

- 含义：术语表对象

### 24. Intake Task

- 含义：该文档进入系统的接入任务

### 25. Intake Validation

- 含义：接入校验节点
- 用途：表示类型、大小、重复、归属等校验结果

### 26. Intake Warning

- 含义：接入阶段告警

### 27. Intake Failure

- 含义：接入阶段失败对象

---

## 二、解析与统一对象节点

### 28. Parser Routing Decision

- 含义：解析器路由决策节点
- 用途：记录为什么选择某种 parser

### 29. Parser Capability Match

- 含义：解析器适配判断节点

### 30. Parser Task

- 含义：具体解析执行任务

### 31. OCR Task

- 含义：OCR 子任务

### 32. OCR Region

- 含义：OCR 识别区域节点

### 33. Layout Detection Task

- 含义：版面识别任务

### 34. Structure Reconstruction Task

- 含义：结构重建任务

### 35. Parser Warning

- 含义：解析阶段警告

### 36. Parser Failure

- 含义：解析阶段失败对象

### 37. Parsed Page

- 含义：解析后的页级结构

### 38. Parsed Block

- 含义：解析后的块级结构

### 39. Parsed Paragraph

- 含义：解析后的段落结构

### 40. Parsed Sentence

- 含义：解析后的句对象

### 41. Parsed Header

- 含义：解析后的标题结构

### 42. Parsed List

- 含义：解析后的列表结构

### 43. Parsed Table

- 含义：解析后的表格结构

### 44. Parsed Table Row

- 含义：解析后的表格行结构

### 45. Parsed Table Cell

- 含义：解析后的表格单元格结构

### 46. Parsed Figure

- 含义：解析后的图示结构

### 47. Parsed Caption

- 含义：解析后的图注或表注结构

### 48. Parsed Footnote

- 含义：解析后的脚注结构

### 49. Parsed Reference

- 含义：解析后的引用结构

### 50. Parsed Metadata

- 含义：解析阶段生成的元信息结构

### 51. Unified Document

- 含义：统一文档对象

### 52. Unified Section

- 含义：统一后的章节对象

### 53. Unified Block

- 含义：统一文档中的标准块对象

### 54. Unified Segment

- 含义：块内部的标准化细段对象

### 55. Unified Anchor

- 含义：标准锚点对象

### 56. Unified Reference Link

- 含义：统一后的交叉引用连接节点

### 57. Normalization Warning

- 含义：统一阶段警告

---

## 三、证据构造对象节点

### 58. Evidence Extraction Task

- 含义：证据构造任务

### 59. Evidence Scope

- 含义：证据构造的范围对象

### 60. Evidence Unit

- 含义：最小证据单元

### 61. Evidence Span

- 含义：证据文本片段对象

### 62. Evidence Anchor

- 含义：证据锚点对象

### 63. Evidence Window

- 含义：上下文证据窗口对象

### 64. Evidence Context

- 含义：证据上下文对象

### 65. Evidence Citation

- 含义：证据引用对象

### 66. Evidence Quality Check

- 含义：证据质量检查节点

### 67. Evidence Warning

- 含义：证据构造阶段警告

### 68. Evidence Conflict

- 含义：证据相互冲突节点

### 69. Evidence Gap

- 含义：证据缺口节点

### 70. Evidence Duplicate

- 含义：重复证据节点

---

## 四、切块、证据图与证据包对象节点

### 71. Chunk Planning Task

- 含义：切块规划任务

### 72. Chunk Policy

- 含义：切块策略节点

### 73. Chunk Proposal

- 含义：切块候选方案节点

### 74. Chunk

- 含义：切分后的块级对象

### 75. Chunk Boundary

- 含义：块边界对象

### 76. Chunk Boundary Adjustment

- 含义：边界修正对象

### 77. Chunk Bridge

- 含义：跨块桥接对象

### 78. Chunk Group

- 含义：按主题或上下文组合后的块分组

### 79. Chunk Coverage Check

- 含义：切块覆盖检查对象

### 80. Chunk Warning

- 含义：切块阶段警告

### 81. Chunk Failure

- 含义：切块失败对象

### 82. Evidence Graph Node

- 含义：证据图中的节点

### 83. Evidence Graph Edge

- 含义：证据图中的连接

### 84. Evidence Graph Cluster

- 含义：证据图中的局部簇

### 85. Evidence Graph Gap

- 含义：证据图中的空洞或断链节点

### 86. Retrieval Task

- 含义：证据检索任务

### 87. Rerank Task

- 含义：证据重排任务

### 88. Retrieval Candidate

- 含义：进入证据包前的检索候选

### 89. Evidence Pack Build Task

- 含义：证据包构建任务

### 90. Evidence Pack

- 含义：面向后续候选生成的证据包

### 91. Evidence Pack Segment

- 含义：证据包中的子片段对象

### 92. Evidence Pack Quality Check

- 含义：证据包质量检查对象

### 93. Evidence Pack Warning

- 含义：证据包质量告警

---

## 五、候选知识对象节点

### 94. Concept Review Task

- 含义：概念候选审查任务

### 95. Relation Review Task

- 含义：关系候选审查任务

### 96. Definition Review Task

- 含义：定义候选审查任务

### 97. Conflict Consolidation Task

- 含义：冲突整合任务

### 98. Concept Candidate

- 含义：概念候选节点

### 99. Entity Candidate

- 含义：实体候选节点

### 100. Event Candidate

- 含义：事件候选节点

### 101. Process Candidate

- 含义：流程候选节点

### 102. Relation Candidate

- 含义：关系候选节点

### 103. Definition Candidate

- 含义：定义候选节点

### 104. Summary Candidate

- 含义：摘要候选节点

### 105. Family Candidate

- 含义：家族归一候选节点

### 106. Alias Candidate

- 含义：别名候选节点

### 107. Name Variant Candidate

- 含义：名称变体候选节点

### 108. Category Candidate

- 含义：类别候选节点

### 109. Scope Candidate

- 含义：语义范围候选节点

### 110. Conflict Candidate

- 含义：冲突候选节点

### 111. Candidate Support Set

- 含义：候选支撑证据集合

### 112. Candidate Risk

- 含义：候选风险对象

### 113. Candidate Warning

- 含义：候选阶段警告

### 114. Candidate Drop Decision

- 含义：某候选被丢弃的决定节点

---

## 六、归并与规范对象节点

### 115. Merge Task

- 含义：候选归并任务

### 116. Merge Proposal

- 含义：归并提案节点

### 117. Merge Cluster

- 含义：待归并候选簇

### 118. Merge Conflict

- 含义：归并冲突对象

### 119. Normalization Decision

- 含义：归一化决策节点

### 120. Family Normalization Decision

- 含义：家族归一决策节点

### 121. Canonical Item

- 含义：规范知识项

### 122. Canonical Entity

- 含义：规范实体对象

### 123. Canonical Event

- 含义：规范事件对象

### 124. Canonical Process

- 含义：规范流程对象

### 125. Canonical Relation

- 含义：规范关系对象

### 126. Canonical Definition

- 含义：规范定义对象

### 127. Canonical Summary

- 含义：规范摘要对象

### 128. Canonical Alias Set

- 含义：规范别名集合

### 129. Canonical Evidence Set

- 含义：规范对象所绑定的证据集合

### 130. Canonical Provenance

- 含义：规范对象的来源链路节点

### 131. Canonical Risk Profile

- 含义：规范对象风险画像节点

---

## 七、质量评估、治理与门禁对象节点

### 132. Quality Evaluation Task

- 含义：质量策略评估任务

### 133. Rule Group

- 含义：规则组节点

### 134. Rule Hit

- 含义：规则命中节点

### 135. Rule Pass

- 含义：规则通过节点

### 136. Rule Warning

- 含义：规则告警节点

### 137. Rule Block

- 含义：规则阻断节点

### 138. Rule Manual Review Trigger

- 含义：人工复核触发节点

### 139. Warning

- 含义：综合告警节点

### 140. Block

- 含义：综合阻断节点

### 141. Manual Review

- 含义：人工复核节点

### 142. Review Queue Entry

- 含义：进入人工治理队列的对象

### 143. Governance Comment

- 含义：治理说明节点

### 144. Approval Decision

- 含义：人工通过决定

### 145. Rejection Decision

- 含义：人工驳回决定

### 146. Merge Decision

- 含义：人工合并决定

### 147. Edit Decision

- 含义：人工修改决定

### 148. Gate Proposal

- 含义：门禁候选决定

### 149. Gate Decision

- 含义：质量门禁最终决定

### 150. Gate Reason Bundle

- 含义：门禁原因集合节点

### 151. Governance Audit Entry

- 含义：治理审计记录节点

---

## 八、输出、发布与追溯对象节点

### 152. Publish Candidate

- 含义：通过 Gate 后进入发布候选的对象

### 153. Publish Warning

- 含义：发布阶段告警节点

### 154. Published Result

- 含义：最终进入发布态的对象

### 155. Published Snapshot Node

- 含义：发布快照节点

### 156. API Exposure Node

- 含义：对外 API 可见对象节点

### 157. Blocked Result

- 含义：被 Gate 阻断的最终结果对象

### 158. Deferred Result

- 含义：暂缓处理对象

### 159. Trace Record

- 含义：追溯记录对象

### 160. Audit Record

- 含义：审计记录对象

### 161. Diff Record

- 含义：本次结果与上次结果的差异记录对象

---

## 九、聚合与辅助对象节点

### 162. Stage Summary Node

- 含义：某一阶段的摘要节点

### 163. Object Count Summary

- 含义：对象数量摘要节点

### 164. Risk Summary Node

- 含义：风险摘要节点

### 165. Pending Action Node

- 含义：后续待处理动作摘要节点

### 166. Timeline Marker

- 含义：时间轴标记节点

### 167. System Event

- 含义：系统事件节点

### 168. Operator Event

- 含义：人工操作事件节点

### 169. Stream Message Node

- 含义：流输出消息对象

### 170. Focus Marker Node

- 含义：当前聚焦对象节点

## 边类型总表

### 来源结构边

- `contains`
- `belongs_to_folder`
- `belongs_to_archive`
- `has_version`
- `has_metadata`
- `has_page`
- `has_section`
- `has_subsection`
- `has_paragraph`
- `has_sentence`
- `has_bullet`
- `has_table`
- `has_row`
- `has_cell`
- `has_figure`
- `has_caption`
- `has_footnote`
- `has_reference`
- `has_appendix`

### 解析与统一边

- `validated_by`
- `routed_to`
- `matched_by`
- `parsed_to`
- `ocr_to`
- `layout_detected_to`
- `reconstructed_to`
- `normalized_to`
- `anchored_by`
- `linked_reference_to`

### 证据构造边

- `extracts_to`
- `evidence_from`
- `spans_to`
- `anchored_to`
- `contextualized_by`
- `cites`
- `quality_checked_by`
- `conflicts_with`
- `duplicates`

### 切块与证据图边

- `planned_by`
- `proposed_by`
- `split_to`
- `adjusted_by`
- `bridged_by`
- `grouped_to`
- `graph_links_to`
- `retrieved_as`
- `reranked_to`
- `packed_to`
- `quality_checked_to`

### 候选生成边

- `reviews_to`
- `proposes`
- `supports`
- `defines`
- `summarizes`
- `aliases_as`
- `variants_as`
- `categorizes_as`
- `scopes_as`
- `conflicts_as`
- `drops_by`

### 归并与规范边

- `clustered_to`
- `merges_to`
- `normalizes_to`
- `family_normalizes_to`
- `forms_canonical`
- `retains_alias_set`
- `retains_evidence_set`
- `records_provenance`
- `profiles_risk`

### 质量评估与治理边

- `evaluated_by`
- `grouped_in_rule`
- `passes_by`
- `warned_by`
- `blocked_by`
- `reviewed_by`
- `queued_for_review`
- `commented_by`
- `approved_by`
- `rejected_by`
- `edited_by`
- `gated_by`
- `reasoned_by`
- `audited_as`

### 输出与追溯边

- `publishes_to`
- `snapshotted_as`
- `exposed_to_api`
- `retained_as_blocked`
- `deferred_as`
- `traced_to`
- `diffed_to`

### 辅助表现边

- `summarized_by`
- `counts_for`
- `highlights`
- `streams_to`
- `focuses_on`

## 第一版布局草图规则

### 整体布局

单文档页采用 `顶部定位 + 概要链 + 主状态图 + 观察窗 + 辅助带` 的布局。

```text
+------------------------------------------------------------------------------------------------------------------+
| 顶部定位区：文档名称 / 文档类型 / 当前阶段 / 当前状态 / run_id / 返回动作                                          |
+------------------------------------------------------------------------------------------------------------------+
| 概要主流程链：Intake -> Parser -> Unified -> Evidence -> Evidence Pack -> Review -> Canonical -> Gate -> Publish |
+------------------------------------------------------------------------------------------------------------------+
| 主状态图画布（左 2/3）                                             | 阶段观察窗（右 1/3）                        |
|                                                                    |                                             |
| 采用多层图布局，当前阶段子图展开，其他子图折叠                       | 流输出主区 + 结构化摘要 + 动作区             |
+------------------------------------------------------------------------------------------------------------------+
| 底部辅助带：证据入口 / 规则入口 / 产物入口 / 关联对象入口                                                       |
+------------------------------------------------------------------------------------------------------------------+
```

### 画布分层规则

主状态图不建议画成普通左到右的单线流程图，而应采用 `五列主层 + 当前阶段局部展开 + 折叠聚合节点` 的方式。

#### 第 1 列：来源与解析层

- Source File
- Source Page / Section / Paragraph / Table / Figure
- Intake Task / Validation
- Parser Routing Decision
- Parser Task / OCR Task / Layout Detection
- Parsed Block / Parsed Table / Parsed Figure

#### 第 2 列：统一与证据构造层

- Unified Document
- Unified Block / Unified Segment
- Unified Anchor
- Evidence Extraction Task
- Evidence Unit / Span / Anchor / Context
- Evidence Warning / Conflict / Gap

#### 第 3 列：切块、证据图与证据包层

- Chunk Planning Task
- Chunk / Chunk Boundary / Adjustment
- Chunk Group / Chunk Bridge
- Evidence Graph Node / Edge / Cluster
- Retrieval Task / Rerank Task
- Evidence Pack Build Task / Evidence Pack

#### 第 4 列：候选与规范层

- Concept / Relation / Definition / Summary / Conflict Candidate
- Candidate Support Set / Risk / Warning
- Merge Task / Merge Proposal / Merge Cluster
- Canonical Item / Relation / Definition / Summary / Alias Set / Provenance

#### 第 5 列：规则、治理与输出层

- Quality Evaluation Task
- Rule Group / Rule Hit / Rule Warning / Rule Block
- Warning / Block / Manual Review / Review Queue Entry
- Gate Proposal / Gate Decision / Gate Reason Bundle
- Publish Candidate / Published Result / Blocked Result / Audit Record / Trace Record

### 当前阶段展开规则

所有列都可见，但只有当前阶段对应列簇展开到详细模式。

#### 当前阶段 = Parser Router

重点展开：

- Parser Routing Decision
- Parser Capability Match
- Source Metadata
- Intake Validation
- Intake Warning

#### 当前阶段 = Parser Execution

重点展开：

- Parser Routing Decision
- Parser Task
- OCR Task
- Layout Detection Task
- Structure Reconstruction Task
- Parsed Block / Parsed Table / Parsed Figure
- Parser Warning / Parser Failure

#### 当前阶段 = Unified Document Object

重点展开：

- Parsed Block
- Unified Document
- Unified Section / Unified Block / Unified Segment
- Unified Anchor
- Normalization Warning

#### 当前阶段 = Evidence Constructor

重点展开：

- Evidence Extraction Task
- Evidence Unit
- Evidence Span
- Evidence Anchor
- Evidence Context
- Evidence Warning / Evidence Conflict / Evidence Gap

#### 当前阶段 = Evidence Graph / Chunk Layer

重点展开：

- Chunk Planning Task
- Chunk / Boundary / Adjustment
- Chunk Group / Bridge
- Evidence Graph Node / Edge / Cluster
- Chunk Warning / Chunk Failure

#### 当前阶段 = Evidence Pack

重点展开：

- Retrieval Task / Rerank Task
- Evidence Pack Build Task
- Evidence Pack / Evidence Pack Warning

#### 当前阶段 = Concept Candidate Review

重点展开：

- Concept Candidate
- Entity Candidate
- Event Candidate
- Process Candidate
- Candidate Support Set
- Candidate Risk
- Candidate Warning / Candidate Drop Decision

#### 当前阶段 = Relation Review / Family Normalization

重点展开：

- Relation Candidate
- Family Candidate
- Alias Candidate
- Name Variant Candidate
- Family Normalization Decision
- Candidate Warning

#### 当前阶段 = Definition / Summary / Conflict Consolidation

重点展开：

- Definition Candidate
- Summary Candidate
- Conflict Candidate
- Candidate Support Set
- Candidate Warning / Candidate Drop Decision

#### 当前阶段 = Canonical Knowledge

重点展开：

- Merge Task
- Merge Proposal / Merge Cluster
- Merge Conflict
- Normalization Decision
- Family Normalization Decision
- Canonical Item / Relation / Definition / Summary
- Canonical Alias Set / Evidence Set / Provenance / Risk Profile

#### 当前阶段 = Quality Policy Evaluation / Governance Gate

重点展开：

- Quality Evaluation Task
- Rule Group
- Rule Hit / Rule Pass / Rule Warning / Rule Block
- Warning / Block / Manual Review
- Review Queue Entry
- Gate Proposal / Gate Decision / Gate Reason Bundle
- Governance Comment

#### 当前阶段 = Indexes / Snapshots / APIs

重点展开：

- Publish Candidate
- Publish Warning
- Published Result
- Published Snapshot Node
- API Exposure Node
- Blocked Result
- Trace Record / Audit Record / Diff Record

### 折叠与聚合规则

#### 1. 非当前阶段默认折叠

非当前阶段的节点簇只显示：

- 阶段摘要节点
- 当前状态
- 节点数量
- 风险数量

#### 2. 大量重复节点允许聚合

例如：

- 24 个 `Evidence Unit`
- 8 个 `Chunk`
- 6 个 `Rule Hit`

可以折叠成聚合节点，点击后展开。

#### 3. 关键节点永不被聚合掉

以下节点始终保留明确实例：

- Source File
- Unified Document
- Evidence Pack
- Canonical Item
- Gate Decision
- Published Result 或 Blocked Result

## 节点视觉样式规则

### 节点形状分类

#### A. 来源对象节点

- 形状：直角矩形
- 用途：表达原始材料及其结构

#### B. 任务节点

- 形状：轻圆角矩形
- 用途：表达正在执行的处理动作

#### C. 中间产物节点

- 形状：中圆角矩形
- 用途：表达系统生成的结构化或组合对象

#### D. 候选知识节点

- 形状：圆角矩形，带轻强调边框
- 用途：表达尚未 canonical 的知识候选

#### E. 规范知识节点

- 形状：较强调的圆角矩形
- 用途：表达已形成的规范对象

#### F. 判断节点

- 形状：六边形或强调矩形
- 用途：表达规则命中和判断

#### G. 决策节点

- 形状：菱形或强调边框矩形
- 用途：表达门禁、人工审批、归并决策

#### H. 输出节点

- 形状：封口型圆角矩形
- 用途：表达发布、阻断、暂缓等结果

### 节点视觉分组

#### 1. 来源对象节点

- 背景：白或浅灰
- 边框：浅灰
- 文本：深灰

#### 2. 任务节点

- 背景：浅蓝灰
- 边框：中性灰
- 文本：深灰

#### 3. 证据对象节点

- 背景：浅蓝或浅米蓝
- 边框：蓝灰
- 文本：深灰

#### 4. Chunk / Pack 节点

- 背景：浅蓝
- 边框：蓝色系
- 文本：深灰

#### 5. 候选知识节点

- 背景：浅青、浅紫灰、浅薄荷色
- 边框：轻强调
- 文本：深灰

#### 6. Canonical 节点

- 背景：浅绿
- 边框：绿色系
- 文本：深灰

#### 7. Rule Hit 节点

- 背景：浅黄
- 边框：黄棕
- 文本：深灰

#### 8. Warning 节点

- 背景：浅橙黄
- 边框：橙色
- 文本：深灰

#### 9. Block 节点

- 背景：浅橙红
- 边框：深橙红
- 文本：深灰

#### 10. Manual Review 节点

- 背景：浅金色
- 边框：金棕色
- 文本：深灰

#### 11. Publish Result 节点

- 背景：浅绿或中浅绿
- 边框：深绿
- 文本：深灰

#### 12. Blocked Result 节点

- 背景：浅橙红
- 边框：深橙红
- 文本：深灰

### 节点标签结构

每个节点建议使用三段式标签：

1. 顶部：节点类型
2. 中部：节点名称 / 摘要
3. 底部：状态 / 数量 / 风险提示

例如：

```text
Evidence Pack
pack-03 / definition-support
running · 6 条 evidence
```

### 节点尺寸等级

#### 小节点

用于：

- Rule Hit
- Warning
- Anchor
- Reference

#### 中节点

用于：

- Parsed Block
- Evidence Unit
- Chunk
- Candidate

#### 大节点

用于：

- Source File
- Unified Document
- Evidence Pack
- Canonical Item
- Gate Decision

#### 聚合节点

用于：

- `24 个 Evidence Unit`
- `8 个 Rule Hit`

聚合节点要带数量角标。

## 节点状态变化规则

### 通用状态集合

- `queued`
- `scheduled`
- `running`
- `streaming`
- `ready`
- `warning`
- `blocked`
- `manual_review`
- `approved`
- `rejected`
- `merged`
- `published`
- `skipped`
- `failed`
- `stale`
- `archived`

### 节点状态变化规则

#### Source / Metadata 类

- `ready`
- `stale`
- `archived`

#### Intake Task

- `queued -> running -> ready`
- `queued -> running -> warning`
- `queued -> running -> failed`

#### Parser Task

- `queued -> running -> streaming -> ready`
- `queued -> running -> warning`
- `queued -> running -> failed`

#### OCR / Layout / Reconstruction 子任务

- `queued -> running -> ready`
- `queued -> running -> warning`

#### Unified Document

- `queued -> running -> building -> ready`
- `queued -> running -> warning`

#### Evidence Unit / Evidence Context

- `queued -> collecting -> running -> ready`
- `queued -> collecting -> warning`

#### Chunk / Chunk Group

- `planned -> running -> adjusted -> ready`
- `planned -> running -> warning`
- `planned -> running -> failed`

#### Evidence Pack

- `collecting -> reranking -> streaming -> ready`
- `collecting -> warning`
- `collecting -> failed`

#### Candidate

- `proposed -> enriched -> ready`
- `proposed -> warning`
- `proposed -> dropped`
- `proposed -> merged`

#### Canonical

- `forming -> merged -> ready`
- `forming -> warning`

#### Rule Hit / Rule Warning / Rule Block

- `detected -> confirmed`

#### Manual Review

- `pending -> approved`
- `pending -> rejected`
- `pending -> edited`

#### Gate Decision

- `pending -> warning`
- `pending -> blocked`
- `pending -> manual_review`
- `pending -> passed`

#### Publish Candidate

- `ready -> published`
- `ready -> blocked`
- `ready -> deferred`

#### Published Result / Blocked Result

- `ready`
- `stale`

## 颜色规则

### 状态颜色

- `queued`：浅灰
- `scheduled`：浅蓝灰
- `running`：蓝色
- `streaming`：亮蓝
- `ready`：绿色
- `warning`：黄橙
- `blocked`：橙红
- `manual_review`：金色
- `approved`：绿色
- `rejected`：红色
- `merged`：青绿
- `published`：深绿
- `skipped`：灰色
- `failed`：深红
- `stale`：棕灰
- `archived`：灰蓝

### 节点高亮规则

#### 当前阶段主节点

- 粗边框
- 外发光
- 与右侧观察窗联动高亮

#### 当前流输出命中的节点

- 短暂脉冲高亮
- 如果是新增边，边也高亮

#### 已完成历史节点

- 保留状态色，但降低明度

#### 未进入节点

- 统一灰化

#### 被阻断节点

- 节点和相关边同时染成阻断色

#### 待人工复核节点

- 金色高亮
- 可叠加“待人工”徽标

### 边颜色规则

- 普通关系边：中性灰
- 当前路径边：蓝色高亮
- 支撑边：蓝灰
- 归并边：青绿
- 规则判断边：黄棕
- 阻断边：橙红
- 发布边：深绿

### 边样式规则

- 实线：确定关系
- 虚线：候选关系、推定关系、暂未确认关系
- 点线：辅助解释关系、聚合关系
- 粗边：当前关键路径

## 流输出与图联动规则

### 1. 流输出主区为主视图之一

只要当前阶段存在持续分析文本，右侧阶段观察窗就以流输出为主。

### 2. 流输出中提到的对象，图中同步高亮

流输出提到：

- `Evidence Pack`
- `Definition Candidate`
- `Rule Hit`
- `Gate Decision`

则相应节点同步高亮。

### 3. 阻断事件出现时，自动聚焦到 Gate 子图

如果流输出出现 `blocked`、`manual review`、`rule hit` 等阻断关键信息：

- 图自动聚焦到规则与门禁区域
- 最终阻断对象和原因边同步高亮

### 4. 新增节点应有轻量动态反馈

例如：

- 新 Evidence Unit 出现
- 新 Candidate 生成
- 新 Rule Hit 命中

可采用：

- 淡入
- 轻脉冲
- 新节点角标

### 5. 用户点击节点时，流输出过滤到相关片段

点击 `Definition Candidate`：

- 观察窗优先展示与其相关的分析流
- 结构化摘要同步切到该对象的输入输出

### 6. 用户点击边时，流输出过滤到“关系形成过程”

点击边时，观察窗不应显示空摘要。

应显示：

- 这条边表示什么关系
- 这条关系在哪个阶段形成
- 由哪些对象参与
- 当前状态是什么
- 是否命中过规则
- 是否被阻断、降级或待人工处理

### 7. 默认联动优先级

默认联动顺序应为：

1. 当前阶段自动高亮对应阶段图谱
2. 当前流输出自动高亮图中对象
3. 用户点击节点后，观察窗切换到节点模式
4. 用户点击边后，观察窗切换到边模式
5. 用户取消选择后，观察窗回到阶段模式

## 对象观察窗模式合同

右侧观察窗应统一为“对象观察窗”，至少支持三种模式。

### 1. 阶段模式

触发条件：

- 页面初始进入
- 只切换阶段，未点击节点或边

主要内容：

- 当前阶段实时分析流
- 阶段输入摘要
- 阶段输出摘要
- 风险摘要
- 下一步动作

### 2. 节点模式

触发条件：

- 点击任意节点

主要内容：

- 节点名称与类型
- 当前状态
- 与该节点相关的实时处理流
- 输入对象
- 输出对象
- 命中规则
- 关联边
- 下钻动作

### 3. 边模式

触发条件：

- 点击任意边

主要内容：

- 边类型
- 源节点与目标节点
- 形成时刻
- 当前状态
- 这条关系对应的分析流
- 相关规则命中
- 相关阻断 / 人工复核
- 上下游跳转动作

## 统一观察窗内容框架模板

三种视角虽然承载的对象不同，但观察窗的骨架必须统一。这样用户切换阶段、节点、边时，不需要重新学习信息层次；前端实现时，也能复用同一套容器、分区和交互。

### 统一骨架

无论是哪种视角，观察窗都固定为 5 层：

1. `头部身份区`
2. `模式切换区`
3. `实时流主区`
4. `结构化摘要区`
5. `底部动作区`

默认比例建议：

- 头部身份区：10% - 12%
- 模式切换区：6% - 8%
- 实时流主区：42% - 50%
- 结构化摘要区：24% - 30%
- 底部动作区：10% - 12%

说明：

- 如果当前对象存在实时流，实时流主区必须占最大面积。
- 如果当前对象没有实时流，结构化摘要区可以上提为主区，但整体骨架不变。
- 观察窗本身必须支持纵向滚动。

### 统一字段分层

不管是哪种视角，内容都必须分成三类：

- `身份信息`：当前看的到底是谁
- `过程信息`：它现在或刚才在发生什么
- `结果信息`：它产生了什么结果、风险和后续动作

### 统一交互规则

- 点击阶段节点：进入阶段视角
- 点击图谱节点：进入节点视角
- 点击图谱边：进入边视角
- 取消选择：回到当前阶段视角
- 如果当前对象在运行中：默认自动滚动到最新流
- 如果用户手动滚动离开底部：暂停自动跟随，并显示“回到最新”

## 观察窗模板 A：阶段视角

阶段视角不是阶段说明页，而是“当前阶段的运行观察窗”。

### A1. 头部身份区

固定展示：

- 阶段名称
- 当前阶段状态
- 当前阶段所属大阶段
- 当前时间或最近更新时间
- 当前对象范围
  - 例如：`文档 1 / 68`、`当前知识库 nas-a`、`阶段对象 12 个`

可选补充：

- 当前运行层级标识
  - `全局`
  - `单知识库`
  - `单文档`

### A2. 模式切换区

固定展示：

- `阶段`
- `节点`
- `边`

阶段视角中，`阶段` 为激活态。
如果当前没有选中节点或边，`节点` / `边` 为可切但未激活态。

### A3. 实时流主区

阶段视角的主角是：

- 当前阶段实时分析流
- 当前阶段运行中发生的对象变化流
- 当前阶段的关键判断流

流条目建议统一结构：

- 时间戳
- 事件类型标签
  - `进度`
  - `生成`
  - `连接`
  - `调整`
  - `规则`
  - `告警`
  - `阻断`
  - `建议`
- 事件正文

### A4. 结构化摘要区

固定分成 4 块：

1. `输入摘要`
   - 输入对象数
   - 输入对象类型
   - 当前活跃输入对象

2. `输出摘要`
   - 当前阶段已生成对象
   - 当前阶段已完成对象
   - 当前阶段待进入下游对象

3. `风险摘要`
   - 告警数
   - 阻断数
   - 待人工数
   - 当前最重风险

4. `当前聚焦`
   - 当前主路径
   - 当前活跃节点
   - 当前活跃边

### A5. 底部动作区

阶段视角固定动作建议：

- 查看当前活跃节点
- 查看当前活跃边
- 查看阶段完整快照
- 切换到上一阶段 / 下一阶段
- 查看阶段规则命中

## 观察窗模板 B：节点视角

节点视角不是简单的节点详情，而是“图谱中某个节点对象的观察窗”。

### B1. 头部身份区

固定展示：

- 节点名称
- 节点类型
- 节点状态
- 所属阶段
- 最近更新时间

如果节点有来源身份，还必须展示：

- 来源对象
- 节点 ID / 外部标识

### B2. 模式切换区

固定展示：

- `阶段`
- `节点`
- `边`

节点视角中，`节点` 为激活态。
同时显示当前选中节点的轻提示，例如：

- `当前选中：Rule Hit RH-17`

### B3. 实时流主区

节点视角的主角是：

- 与该节点相关的实时处理流
- 该节点的生成、调整、告警、阻断、放行等过程流

节点流重点展示：

- 节点何时生成
- 节点何时被更新
- 节点何时被规则命中
- 节点何时被人工复核或阻断
- 节点何时进入下游

### B4. 结构化摘要区

固定分成 5 块：

1. `节点内容`
   - 节点核心值
   - 节点文本或载荷摘要
   - 节点的关键字段

2. `来源与上下文`
   - 来源对象
   - 所属局部簇
   - 所属主路径位置

3. `上下游对象`
   - 上游节点列表
   - 下游节点列表
   - 关联边数量

4. `规则与风险`
   - 命中规则
   - 风险等级
   - 当前是否阻断 / 待人工 / 可放行

5. `证据与追溯`
   - 支撑证据数
   - 关键证据锚点
   - 快速追溯入口

### B5. 底部动作区

节点视角固定动作建议：

- 查看上游节点
- 查看下游节点
- 查看关联边
- 查看完整证据
- 回到阶段视角

## 观察窗模板 C：边视角

边视角不是关系说明，而是“图谱中某条边对象的观察窗”。

### C1. 头部身份区

固定展示：

- 边名称或边类型
- 边状态
- 所属阶段
- 源节点
- 目标节点
- 最近更新时间

如果边有方向性、权重、置信度，也必须展示：

- 边方向
- 边权重 / 强度 / 置信度

### C2. 模式切换区

固定展示：

- `阶段`
- `节点`
- `边`

边视角中，`边` 为激活态。
同时显示当前选中边的轻提示，例如：

- `当前选中：blocked_by`

### C3. 实时流主区

边视角的主角是：

- 这条边的形成过程
- 这条边的调整过程
- 这条边的断开、重连、升级、阻断过程

边流重点展示：

- 何时建立
- 为什么建立
- 是否被修正
- 是否被规则命中
- 是否导致阻断 / 放行 / 人工复核

### C4. 结构化摘要区

固定分成 5 块：

1. `关系定义`
   - 边类型
   - 源节点
   - 目标节点
   - 方向

2. `形成依据`
   - 建立原因
   - 触发对象
   - 关键证据

3. `关系状态`
   - 当前状态
   - 是否稳定
   - 是否可继续向下游传播

4. `规则与影响`
   - 相关规则命中
   - 相关告警 / 阻断 / 人工复核
   - 对上下游的影响

5. `路径位置`
   - 所在主路径位置
   - 所属局部簇
   - 相邻关键边

### C5. 底部动作区

边视角固定动作建议：

- 查看源节点
- 查看目标节点
- 查看完整证据
- 查看相关规则
- 回到阶段视角

## 三种视角的差异边界

为了避免观察窗在实现时混乱，必须明确：

### 阶段视角回答的问题

- 这个阶段整体现在在做什么
- 当前阶段输入了什么
- 当前阶段产出了什么
- 当前阶段主要风险是什么

### 节点视角回答的问题

- 这个节点对象是什么
- 它从哪里来
- 它现在是什么状态
- 它与哪些对象有关
- 它为什么会被告警、阻断或放行

### 边视角回答的问题

- 这条边表达了什么关系
- 它为什么成立
- 它连接了哪些对象
- 它在什么时候建立、调整、断开或重连
- 它对后续流程造成了什么影响

## 三种视角的实现优先级

第一版优先保证：

1. 头部身份区准确
2. 实时流主区可读
3. 结构化摘要区字段固定
4. 底部动作区足够少但有效

第一版不强求：

- 复杂富文本
- 多层嵌套表格
- 过多的次级操作按钮

优先保证“看得懂、能切换、能追踪”。

## 13 个阶段的观察窗视角合同

下面的合同是在通用“阶段模式 / 节点模式 / 边模式”之上的阶段化展开。每个阶段都必须明确：

- 阶段视角到底看该阶段整体在发生什么
- 节点视角到底看该阶段图谱中的单个节点对象在表达什么
- 边视角到底看该阶段图谱中的单条边对象在表达什么

### 1. Asset Intake

#### 阶段视角

- 当前接入任务、来源目录、文件批次、接入总量
- 当前接入进度、成功/失败/重复/跳过数量
- 当前批次中最新接入的文件对象
- 接入告警、校验异常、重复素材判定
- 接入结果流与下一阶段可进入对象

#### 节点视角

- 若点击 `Source File`：显示文件名、来源路径、大小、摘要、时间戳、接入状态
- 若点击 `Import Task`：显示任务状态、处理批次、耗时、当前处理文件、告警
- 若点击 `File Digest`：显示摘要算法、摘要值、重复检测结果、关联源文件
- 若点击 `Intake Result`：显示接入结论、阻断原因、后续流向
- 节点流输出重点展示“文件进入、校验、去重、接入结果形成”的动态过程

#### 边视角

- `imported_from`：解释文件与源目录/源档案的归属关系
- `hashed_to`：解释文件与摘要结果的形成关系
- `validated_by`：解释接入校验依据、校验规则、校验结果
- `results_in`：解释该文件为何进入某个接入结果
- 边流输出重点展示“这条关系何时建立、由哪一步触发、是否因异常被中断”

### 2. Parser Router

#### 阶段视角

- 当前路由任务、文档类型判断、候选解析器集合
- 当前选择的解析路线及其原因
- 被排除解析器、冲突规则、降级或阻断原因
- 当前进入下游解析器的对象数
- 路由决策流与规则命中摘要

#### 节点视角

- 若点击 `Routing Task`：显示任务状态、当前文件、候选解析器、已命中规则
- 若点击 `Document Type`：显示识别出的文档类型、置信度、来源依据
- 若点击 `Parser Candidate`：显示解析器名称、适用条件、是否被选中/排除
- 若点击 `Routing Decision`：显示最终路由、采用原因、未采用候选
- 节点流输出重点展示“类型识别、规则判定、解析器选择”的变化过程

#### 边视角

- `classified_as`：解释文件被判断为某类型的依据
- `evaluated_by`：解释类型或文件如何进入路由规则评估
- `selects`：解释为什么最终选择某个解析器
- `rejected_by`：解释为什么候选解析器被排除
- 边流输出重点展示“判断依据、路由切换、候选收敛”的过程

### 3. Parser Execution

#### 阶段视角

- 当前解析任务、解析器、页级进度、结构恢复进度
- 当前已生成的页面/块/表格/图形对象数量
- 解析告警、OCR 问题、布局问题、失败页
- 当前准备进入统一文档的对象数
- 解析流输出与关键异常定位

#### 节点视角

- 若点击 `Parser Task`：显示任务状态、解析器、当前页、当前子任务
- 若点击 `Parsed Page`：显示页码、页级文本量、结构摘要、是否异常
- 若点击 `Parsed Block`：显示块类型、块内容摘要、来源页、解析质量
- 若点击 `OCR Result` / `Layout Result`：显示识别文本、布局框、可信度
- 节点流输出重点展示“页块生成、OCR 补入、布局恢复、失败重试”

#### 边视角

- `executed_by`：解释任务与解析器之间的实际执行关系
- `parsed_to`：解释原始文件如何生成某页或某块
- `extracts`：解释某页/某块抽出的子对象
- `detects`：解释布局/OCR/结构结果的形成关系
- 边流输出重点展示“生成、失败、修正、补录”的事件流

### 4. Unified Document Object

#### 阶段视角

- 当前统一任务、输入页块数量、输出统一对象数量
- 结构归一、顺序重排、缺失补齐、对象合并状态
- 当前统一文档是否 ready、是否仍存在结构不一致
- 当前可进入证据构造的对象范围
- 统一过程流与归一规则摘要

#### 节点视角

- 若点击 `Unified Document`：显示文档级统一状态、结构树摘要、字段完备度
- 若点击 `Unified Section` / `Unified Paragraph`：显示文本、层级位置、来源页块
- 若点击 `Normalization Rule`：显示规则说明、命中对象、调整结果
- 若点击 `Normalization Decision`：显示保留/合并/重排结论
- 节点流输出重点展示“归一、重排、补齐、丢弃”的变化过程

#### 边视角

- `normalized_to`：解释解析对象如何映射成统一对象
- `mapped_from`：解释统一对象的来源集合
- `reordered_by`：解释顺序为何调整
- `cleaned_by`：解释清洗或字段修正规则
- 边流输出重点展示“对象收敛、字段修正、层级归属”的关系形成

### 5. Evidence Constructor

#### 阶段视角

- 当前证据构造任务、已生成证据单元数量、锚点覆盖率
- 当前证据单元分布、缺锚点对象、证据不足对象
- 当前准备进入 chunk 层的证据集合
- 证据构造告警、锚点冲突、跨度异常
- 证据构造流与证据质量摘要

#### 节点视角

- 若点击 `Evidence Unit`：显示证据文本、来源段落、长度、证据状态
- 若点击 `Evidence Anchor`：显示页码/段落/字符范围、定位质量
- 若点击 `Evidence Span`：显示引用范围、边界、是否被修正
- 若点击 `Evidence Warning`：显示告警原因、受影响对象、建议动作
- 节点流输出重点展示“证据切分、锚点补齐、span 修正、证据弃用”

#### 边视角

- `evidence_from`：解释证据单元来自哪段统一文本
- `anchored_at`：解释证据锚点如何指向原文位置
- `spans`：解释证据跨度与原文的关系
- `warned_by`：解释某条证据关系为何被标为风险
- 边流输出重点展示“证据建立、锚点定位、跨度调整”的过程

### 6. Evidence Graph / Chunk Layer

#### 阶段视角

- 当前 chunk 规划任务、chunk 总数、边界修正数、图连接数
- 当前活跃 chunk、聚合 chunk 组、上下文连接状态
- 哪些 chunk 正在调整、哪些关系刚建立或断开
- 当前 evidence graph 的连通性与风险点
- chunk 层实时变化流

#### 节点视角

- 若点击 `Chunk`：显示 chunk 内容摘要、大小、来源证据、状态
- 若点击 `Chunk Group`：显示组内对象、分组理由、当前稳定性
- 若点击 `Boundary Fix`：显示修正原因、修正前后边界、影响对象
- 若点击 `Evidence Graph Node`：显示其在局部图中的上下文角色
- 节点流输出重点展示“chunk 生成、重切、聚合、断开、重连”

#### 边视角

- `split_to`：解释某对象为何拆成多个 chunk
- `grouped_into`：解释多个 chunk 为何聚成组
- `linked_to`：解释 chunk 之间建立上下文连接的依据
- `adjusted_by`：解释边界修正对关系的影响
- 边流输出重点展示“分裂、聚合、重连、消失”的动态关系

### 7. Evidence Pack

#### 阶段视角

- 当前证据包任务、检索命中数、重排结果、入包对象数
- 当前证据包中的核心证据、边缘证据、被踢出的证据
- 当前证据包是否 ready、是否仍缺关键支持证据
- 证据包告警、检索偏差、重排不稳定
- 取证与重排实时流

#### 节点视角

- 若点击 `Evidence Pack`：显示入包对象、主支撑证据、当前状态
- 若点击 `Retrieval Query`：显示检索意图、过滤条件、命中范围
- 若点击 `Retrieved Candidate`：显示候选证据对象及其打分
- 若点击 `Rerank Result`：显示重排顺序、保留/淘汰原因
- 节点流输出重点展示“检索、命中、重排、入包、淘汰”

#### 边视角

- `retrieves`：解释查询如何命中对象
- `selected_into`：解释对象为何被纳入证据包
- `reranked_to`：解释排序变化和位次变化
- `supports`：解释某对象如何成为主支持证据
- 边流输出重点展示“命中形成、排序变化、入包/出包”的关系流

### 8. Concept Candidate Review

#### 阶段视角

- 当前概念候选任务、候选数、已丢弃数、待人工数
- 当前主概念候选、别名、类别判定、置信度分布
- 当前候选支持证据与风险摘要
- 候选告警、低质量项、噪声项处理结果
- 概念候选实时形成流

#### 节点视角

- 若点击 `Concept Candidate`：显示名称、类别、置信度、状态、支持证据
- 若点击 `Concept Alias`：显示别名、来源、别名冲突情况
- 若点击 `Concept Category`：显示类别结论及其依据
- 若点击 `Concept Drop`：显示丢弃原因、触发规则、相关证据
- 节点流输出重点展示“候选提出、别名追加、类别调整、丢弃”

#### 边视角

- `proposes`：解释证据包如何提出这个候选
- `supports`：解释哪些证据真正支撑该候选
- `categorized_as`：解释类别形成的依据
- `aliased_as`：解释别名与候选的关系
- 边流输出重点展示“提出、支持、修正、剔除”的关系过程

### 9. Relation Review / Family Normalization

#### 阶段视角

- 当前关系候选任务、关系数、家族归一结果、冲突关系数
- 当前活跃关系、当前家族组、当前别名冲突
- 关系风险、端点不一致、归一失败
- 待人工复核关系与推荐动作
- 关系/家族实时收敛流

#### 节点视角

- 若点击 `Relation Candidate`：显示关系类型、端点、状态、支持证据
- 若点击 `Family Group`：显示组内成员、归一策略、冲突数量
- 若点击 `Alias Collision`：显示冲突名称、冲突对象、冲突原因
- 若点击 `Normalization Decision`：显示保留/合并/拆分结论
- 节点流输出重点展示“关系提出、端点重挂、家族归并、冲突处理”

#### 边视角

- `connects`：解释这条关系连接了哪些对象
- `typed_as`：解释关系类型如何确定
- `belongs_to_family`：解释对象为何属于某个家族组
- `merged_with` / `conflicts_with`：解释合并或冲突关系成立原因
- 边流输出重点展示“端点连接、家族吸收、冲突暴露、重挂接”

### 10. Definition / Summary / Conflict Consolidation

#### 阶段视角

- 当前定义/摘要/冲突整合任务、定义数、冲突对数、挂起数
- 当前主要定义对象、当前主要冲突对象
- 冲突是否已解决、摘要是否收敛
- 当前进入规范阶段的候选内容
- 定义与冲突整合实时流

#### 节点视角

- 若点击 `Definition Candidate`：显示定义文本、支持证据、质量状态
- 若点击 `Summary Candidate`：显示摘要文本、覆盖范围、压缩结果
- 若点击 `Conflict Candidate` / `Conflict Pair`：显示冲突双方、冲突点、状态
- 若点击 `Consolidation Decision`：显示解决方式、保留对象、挂起原因
- 节点流输出重点展示“定义生成、摘要收敛、冲突形成、冲突解决”

#### 边视角

- `defined_by`：解释定义如何被证据支撑
- `summarized_from`：解释摘要来自哪些对象
- `conflicts_with`：解释冲突关系为何成立
- `resolved_by`：解释如何把冲突导向结论
- 边流输出重点展示“定义支撑、摘要聚合、冲突拉链、解决路径”

### 11. Canonical Knowledge

#### 阶段视角

- 当前规范化任务、合并簇数量、规范对象数量、丢弃对象数量
- 当前活跃合并簇、当前形成的规范对象、当前规范风险
- 当前进入质量门禁的规范对象集合
- 合并冲突、归一风险、未完成规范项
- 规范知识实时成形流

#### 节点视角

- 若点击 `Canonical Item` / `Canonical Relation` / `Canonical Definition`：显示规范对象内容、来源候选、状态
- 若点击 `Merge Proposal` / `Merge Cluster`：显示聚类对象、合并原因、冲突点
- 若点击 `Merge Decision`：显示最终保留对象、淘汰对象、决策依据
- 若点击 `Dropped Candidate`：显示被淘汰原因与其原始候选
- 节点流输出重点展示“候选合并、对象成形、对象淘汰、关系重挂”

#### 边视角

- `merges_to`：解释候选如何汇成规范对象
- `included_in`：解释对象为何被纳入规范簇
- `dropped_by`：解释对象为何被丢弃
- `supports` / `defined_by`：解释规范对象与支撑内容的关系
- 边流输出重点展示“吸收、剔除、重定向、定稿”的关系形成

### 12. Quality Policy Evaluation / Governance Gate

#### 阶段视角

- 当前质量评估任务、命中规则数、告警数、阻断数、待人工数
- 当前活跃主路径、当前主阻断对象、当前待处理证据
- 当前门禁结论与推荐动作
- 当前可发布对象、被阻断对象、挂起对象
- 质量门禁实时评估流

#### 节点视角

- 若点击 `Rule Hit`：显示规则名、规则组、命中值、触发原因
- 若点击 `Warning` / `Block`：显示告警/阻断内容、严重度、影响对象
- 若点击 `Manual Review`：显示人工复核触发原因、待补内容、当前状态
- 若点击 `Gate Decision`：显示门禁结论、状态、上下游影响、理由包
- 若点击 `Blocked Result` / `Publish Target`：显示最终被阻断或放行的对象与去向
- 节点流输出重点展示“规则命中、告警形成、阻断形成、人工复核、门禁判定”

#### 边视角

- `evaluated_by`：解释规范对象与规则评估的关系
- `hits`：解释规则命中是如何形成的
- `warned_by` / `blocked_by`：解释为什么形成告警或阻断
- `reviewed_by`：解释人工复核为何被触发
- `results_in` / `publishes_to`：解释门禁结论如何导向最终结果
- 边流输出重点展示“命中、升级、阻断、放行、终止”的关系变化

#### Quality Gate 高保真观察窗模板

下面这组模板不是抽象字段清单，而是可以直接拿去画 UI、拆前后端字段、设计流输出文案的高保真内容模板。

##### A. Quality Gate 阶段视角模板

###### 头部身份区

- 标题：`质量门禁`
- 状态标签：`阻断中` / `运行中` / `已通过`
- 所属大阶段：`规范化与发布`
- 当前范围：`单文档 · SV-2翻译`
- 最近更新时间：`09:43:27`
- 辅助身份：`当前对象 4 个主节点 / 3 条关键边`

###### 模式切换区

- `阶段`
- `节点`
- `边`

阶段视角默认激活 `阶段`。

###### 实时流主区

流标题建议：`质量门禁实时评估流`

流条目建议按以下类型组织：

- `进度`
  - `09:43:08 已载入规范对象 Canonical Item #12，进入质量评估。`
- `规则`
  - `09:43:11 命中规则 min_supporting_documents，当前支撑文档数 1，期望值 2。`
- `告警`
  - `09:43:15 已形成告警 Warning W-4：定义支撑不足，建议补证。`
- `阻断`
  - `09:43:20 已形成阻断 Block B-2：门禁结论暂不放行。`
- `人工复核`
  - `09:43:24 已触发人工复核 MR-1，等待补充证据。`
- `结论`
  - `09:43:27 Gate Decision GD-3 已更新为 blocked，Publish Target 未创建。`

###### 结构化摘要区

1. `输入摘要`
   - 规范对象：`Canonical Item #12`
   - 关系对象：`Canonical Relation #3`
   - 证据集：`1 条主证据 / 2 条辅助证据`

2. `输出摘要`
   - 告警：`1`
   - 阻断：`1`
   - 人工复核：`1`
   - 发布目标：`未创建`

3. `风险摘要`
   - 最高风险：`支撑文档不足`
   - 风险等级：`高`
   - 当前结论：`blocked`

4. `当前聚焦`
   - 主路径：`规范对象 -> Rule Hit -> Gate Decision -> Blocked Result`
   - 当前活跃节点：`Gate Decision GD-3`
   - 当前活跃边：`blocked_by`

###### 底部动作区

- `查看当前活跃节点`
- `查看当前活跃边`
- `查看完整规则命中`
- `切换到上一阶段`
- `查看门禁完整快照`

##### B. Quality Gate 节点视角模板

下面以 5 类高频节点为模板。

###### B1. 点击 Rule Hit

头部身份区：

- 标题：`Rule Hit RH-17`
- 节点类型：`规则命中`
- 状态：`active`
- 所属阶段：`质量门禁`
- 来源对象：`Canonical Item #12`

实时流主区：

- `09:43:11 规则 min_supporting_documents 开始评估。`
- `09:43:12 当前值 1，阈值 2，规则命中。`
- `09:43:14 关联 Warning W-4 已创建。`
- `09:43:18 命中结果持续流入 Gate Decision GD-3。`

结构化摘要区：

1. `命中内容`
   - 规则名：`min_supporting_documents`
   - 当前值：`1`
   - 阈值：`2`
   - 结果：`hit`

2. `来源与上下文`
   - 来源节点：`Canonical Item #12`
   - 所属规则组：`traceability`
   - 所属主路径位置：`Gate 输入层`

3. `上下游对象`
   - 上游：`Canonical Item #12`
   - 下游：`Warning W-4`、`Gate Decision GD-3`
   - 关联边：`evaluated_by`、`hits`

4. `规则与风险`
   - 风险等级：`高`
   - 当前是否阻断：`是`
   - 当前是否待人工：`是`

5. `证据与追溯`
   - 关键证据：`Definition Candidate #12`
   - 支撑文档：`1`
   - 追溯入口：`查看支撑文档`

底部动作区：

- `查看源规范对象`
- `查看 Gate Decision`
- `查看关联边`
- `查看完整证据`
- `回到阶段`

###### B2. 点击 Warning / Block

头部身份区：

- 标题：`Warning W-4` 或 `Block B-2`
- 节点类型：`告警` / `阻断`
- 状态：`active`
- 所属阶段：`质量门禁`
- 影响对象：`Canonical Item #12`

实时流主区重点：

- 告警/阻断何时生成
- 由哪条规则升级而来
- 是否触发人工复核
- 是否已改变 Gate Decision

结构化摘要区重点：

1. `内容`
   - 告警/阻断标题
   - 描述
   - 严重度

2. `来源`
   - 触发规则
   - 触发节点
   - 触发时间

3. `影响`
   - 影响对象
   - 影响边
   - 对发布的影响

4. `处理状态`
   - 是否已处理
   - 是否转人工
   - 是否仍在阻断链上

5. `建议动作`
   - 补证
   - 人工复核
   - 规则豁免（若允许）

###### B3. 点击 Manual Review

头部身份区：

- 标题：`Manual Review MR-1`
- 节点类型：`人工复核`
- 状态：`pending`
- 所属阶段：`质量门禁`
- 当前责任：`治理工作台`

实时流主区重点：

- 为什么触发人工复核
- 当前等待什么材料
- 上一次系统建议是什么
- 当前是否已被人工接手

结构化摘要区重点：

1. `触发原因`
2. `待补内容`
3. `关联对象`
4. `阻断影响`
5. `后续去向`

###### B4. 点击 Gate Decision

头部身份区：

- 标题：`Gate Decision GD-3`
- 节点类型：`门禁决策`
- 状态：`blocked`
- 所属阶段：`质量门禁`
- 当前对象：`SV-2翻译`

实时流主区重点：

- 哪些规则流入该决策
- 决策从 pending 变成 blocked 的过程
- 当前是否仍可能转为 pass
- 当前结论影响了哪些后续对象

结构化摘要区重点：

1. `决策内容`
   - 当前结论：`blocked`
   - 决策理由包：`1 阻断 / 1 告警 / 1 人工复核`

2. `来源与上下文`
   - 输入规范对象
   - 关联规则组
   - 当前主路径位置

3. `上下游对象`
   - 上游：`Rule Hit RH-17`、`Warning W-4`
   - 下游：`Blocked Result BR-2`
   - 潜在下游：`Publish Target`

4. `风险与状态`
   - 风险等级：`高`
   - 是否终止发布：`是`
   - 是否等待人工：`是`

5. `证据与追溯`
   - 关键证据锚点
   - 支撑文档数
   - 相关规则入口

###### B5. 点击 Blocked Result / Publish Target

头部身份区：

- 标题：`Blocked Result BR-2` 或 `Publish Target PT-1`
- 节点类型：`门禁结果`
- 状态：`terminal`
- 所属阶段：`质量门禁`

实时流主区重点：

- 这个结果何时生成
- 由哪个 Gate Decision 产生
- 是否还会变化
- 是否会进入下游发布

结构化摘要区重点：

1. `结果内容`
2. `来源决策`
3. `影响范围`
4. `后续流向`
5. `可逆性`

##### C. Quality Gate 边视角模板

下面以 5 类高频边为模板。

###### C1. 点击 evaluated_by

头部身份区：

- 标题：`evaluated_by`
- 边类型：`评估关系`
- 源节点：`Canonical Item #12`
- 目标节点：`Rule Hit RH-17`
- 状态：`completed`

实时流主区重点：

- 规范对象何时进入规则评估
- 评估时用了哪些值
- 当前评估是否仍在更新

结构化摘要区重点：

1. `关系定义`
2. `形成依据`
3. `评估结果`
4. `影响下游`
5. `路径位置`

###### C2. 点击 hits

头部身份区：

- 标题：`hits`
- 边类型：`命中关系`
- 源节点：`Rule Hit RH-17`
- 目标节点：`Warning W-4 / Gate Decision GD-3`
- 状态：`active`

实时流主区重点：

- 命中关系何时建立
- 命中是否持续升级
- 当前是否已演变成阻断

结构化摘要区重点：

1. `关系定义`
   - 命中值
   - 阈值
   - 结果

2. `形成依据`
   - 规则
   - 当前值
   - 证据

3. `关系状态`
   - active / terminal
   - 是否还会继续传播

4. `规则与影响`
   - 下游节点
   - 影响发布与否

5. `路径位置`
   - 所在主路径位置

###### C3. 点击 warned_by / blocked_by

头部身份区：

- 标题：`warned_by` 或 `blocked_by`
- 边类型：`告警关系` / `阻断关系`
- 源节点：`Warning W-4` / `Block B-2`
- 目标节点：`Gate Decision GD-3`
- 状态：`active`

实时流主区重点：

- 为什么从告警升级成阻断
- 是否经过人工复核
- 是否改变了门禁结论

结构化摘要区重点：

1. `关系定义`
2. `形成依据`
3. `关系状态`
4. `规则与影响`
5. `路径位置`

###### C4. 点击 reviewed_by

头部身份区：

- 标题：`reviewed_by`
- 边类型：`人工复核关系`
- 源节点：`Gate Decision GD-3`
- 目标节点：`Manual Review MR-1`
- 状态：`pending`

实时流主区重点：

- 何时触发人工复核
- 当前等待什么动作
- 是否还会回流到 Gate Decision

结构化摘要区重点：

1. `关系定义`
2. `形成依据`
3. `等待状态`
4. `对当前门禁的影响`
5. `回流路径`

###### C5. 点击 results_in / publishes_to

头部身份区：

- 标题：`results_in` 或 `publishes_to`
- 边类型：`结果关系`
- 源节点：`Gate Decision GD-3`
- 目标节点：`Blocked Result BR-2` / `Publish Target PT-1`
- 状态：`terminal`

实时流主区重点：

- 何时生成最终结果
- 为什么是 blocked 还是 publish
- 是否仍可能回退

结构化摘要区重点：

1. `关系定义`
2. `形成依据`
3. `终态说明`
4. `对下游的影响`
5. `相邻关键边`

##### D. Quality Gate 观察窗的布局强调

Quality Gate 是当前页面的重点阶段，因此观察窗在这个阶段必须额外强调：

- `实时流主区` 默认占比可以提高到 50% - 55%
- `规则与风险` 块必须固定可见，不允许被折叠到首屏外
- `Gate Decision` 与 `Rule Hit` 的上下游关系必须可直接跳转
- `Blocked Result` / `Publish Target` 必须在节点视角和边视角都能看到
- 如果当前阶段正在运行，观察窗默认跟随 `Gate Decision` 或当前活跃 `Rule Hit`

### 13. Indexes / Snapshots / APIs

#### 阶段视角

- 当前发布任务、快照版本、索引写入、API 暴露状态
- 当前生成的发布对象、未生成对象、发布告警
- 当前对外可见内容、版本标记、差异记录
- 当前发布是否稳定、是否需要回滚或补索引
- 发布与索引实时流

#### 节点视角

- 若点击 `Publish Target`：显示待发布对象、状态、依赖条件
- 若点击 `Publication Snapshot`：显示版本号、快照内容摘要、生成时间
- 若点击 `Search Index` / `Graph Index`：显示索引内容、索引状态、覆盖范围
- 若点击 `API Payload`：显示对外载荷摘要、可见字段、版本归属
- 若点击 `Version Tag` / `Diff Record` / `Audit Record`：显示版本、差异、审计说明
- 节点流输出重点展示“发布目标生成、索引写入、快照落盘、API 更新”

#### 边视角

- `published_to`：解释对象如何进入快照或发布结果
- `indexed_as`：解释对象如何进入某种索引
- `versioned_as`：解释对象与版本标签的关系
- `served_by`：解释快照如何对外暴露为 API
- `warned_by`：解释发布期告警与对象之间的关系
- 边流输出重点展示“发布、入索引、打版本、暴露 API”的关系建立过程

## 第一版布局草图规则

### 1. 页面必须同时有“总链”和“细图”

不可只画详细图而丢失主流程定位。

不可只画主流程链而没有当前阶段细图。

### 2. 中部主状态图优先表达“对象关系”，不是“步骤列表”

即使图里有从左到右的主方向，也不应该做成单线流程。

### 3. 当前阶段子图必须占最大视觉权重

用户打开单文档页时，最想看的不是“总流程”，而是：

- 现在这一阶段正在处理什么
- 哪些节点在变化
- 为什么会被拦住

### 4. 辅助信息全部降级到下方或右侧

例如：

- 规则列表
- 证据入口
- 产物入口
- 关联对象入口

这些都不应抢主图位置。

### 5. 第一版 Pencil 绘制采用“可读优先”而不是“完美图论布局”

先把：

- 节点类别
- 主层次
- 当前阶段展开
- 流输出联动

画清楚，再追求更复杂的自动布局感。

### 6. 全部阶段图谱都必须可切换

页面中部主图不是固定一张。

必须支持：

- 默认显示当前运行阶段图谱
- 点击任意已完成阶段后，切换到该阶段图谱
- 点击当前阶段后，刷新当前阶段的实时动态图谱
- 点击未来阶段时显示轻禁用或不可进入态
- 顶层阶段切换后，如存在二级子阶段图谱，允许进入子阶段图谱

### 7. 节点与边都必须进入观察窗

第一版即使不能把所有节点和边都做成真实交互，也必须在线框中表达出：

- 节点可点击
- 边可点击
- 点击后的观察窗上下文切换

## 第一版 Pencil 绘制建议

为了先把图画出来，第一版建议至少画出下面这些核心节点：

### 必须画出的节点

- Source File
- Intake Task
- Parser Task
- Parsed Block
- Unified Document
- Evidence Unit
- Chunk
- Evidence Pack
- Concept Candidate
- Relation Candidate
- Definition Candidate
- Canonical Item
- Rule Hit
- Manual Review
- Gate Decision
- Publish Candidate
- Published Result
- Blocked Result

### 必须画出的边

- `validated_by`
- `parsed_to`
- `normalized_to`
- `evidence_from`
- `split_to`
- `packed_to`
- `proposes`
- `supports`
- `merges_to`
- `evaluated_by`
- `blocked_by`
- `publishes_to`

### 必须画出的动态状态

- `running`
- `streaming`
- `ready`
- `warning`
- `blocked`
- `manual_review`

## 与运行中心其他两层的关系

### 全局并行运行视图

看知识库与阶段编排，不展开文档微流程。

### 单知识库运行视图

看知识库内文档群在各阶段的分布，不展开单文档全部细节。

### 单文档下钻视图

才进入本文档定义的“单文档处理状态图”。

因此：

**单文档处理状态图是三层里最细、最复杂、最动态的那一层。**

## 结论

后续回到 Pencil 时，不再继续把单文档页画成普通流程链，而按下面的结构重画：

1. 顶部：文档身份与状态定位
2. 上部：概要主流程链
3. 中部左：单文档处理状态图
4. 中部右：阶段观察窗（流输出优先）
5. 底部：轻量辅助入口

这张图要体现的不是“阶段顺序”，而是：

**文档如何在处理过程中不断生成对象、连接对象、改变对象状态，并最终形成被放行或被阻断的知识结果。**
