# P1 知识产出质量改进交接文档

## 1. 文档目的

本文面向继续开发 `CodeFactoryV2` P1 业务知识库的高级 AI / 工程代理。

目标不是重新解释 P1 是什么，而是明确说明：当前 P1 知识产出质量处于什么水平，主要短板在哪里，下一轮应该按什么顺序改进，哪些实体类型和关系类型需要扩充，以及改造时应遵守哪些工程边界。

## 2. 当前结论

当前 P1 已经具备较完整的工程链路：

- 文档接入与解析。
- 正式抽取链。
- 文档级正式产物仓。
- 工作态 / curated / published 分层。
- 13 阶段运行态可视化。
- 质量图谱、质量门禁与发布边界的雏形。

但当前知识产出还更接近“可浏览、可演示、可联调的候选知识”，尚不能视为高质量的“可发布领域知识库”。

核心判断：

- 工程壳子成熟度高于知识本体成熟度。
- 当前抽取结果数量充足，但对象语义、证据锚点、定义摘要、跨文档归并和关系语义仍偏弱。
- 下一轮应优先提高知识可信度和可消费性，而不是继续单纯扩大抽取数量。

## 3. 当前事实基线

当前 active 知识库样本为 `.data/knowledge_output/小量数据测试用v2-knowledge.json`。

抽样统计：

- 文档数：7。
- 实体数：380。
- 事件数：11。
- 流程数：61。
- 关系数：789。
- `document_mentions` 关系：529。
- 真实业务关系约：260。
- 总知识项：452。
- 有 evidence excerpt 的知识项：389。
- 有可定位 anchor / chunk / segment 级证据的知识项：0。
- 有稳定 definition / summary 字段的知识项：0。
- 单文档支撑知识项：425。
- 多文档支撑知识项：27。
- 业务关系图孤立知识项：238。
- 业务关系图孤立率约：52.7%。
- curated 产物中所有知识项仍为 `pending`，没有真正治理收敛。

这些数据说明：

- 当前系统能抽到大量候选对象。
- 当前系统能形成基本图谱。
- 当前系统能记录来源文档和证据摘录。
- 但当前系统还不能充分回答“这个知识为什么可信、边界是什么、与其他知识如何结构化关联、是否可正式发布”。

## 4. 关键代码与设计落点

后续开发前应重点阅读以下文件：

- `apps/api/app/extraction/schema.py`
  - 当前结构化抽取 schema。
  - 目前顶层知识对象只允许 `entity / event / process`。
  - 当前关系只允许 7 种。

- `apps/api/app/extraction/service.py`
  - LLM 结构化抽取、chunked formal extraction、规则抽取结果合并。
  - 当前 prompt 明确限制 candidates 最多 24、relations 最多 16。

- `apps/api/app/archive_knowledge/document_artifacts.py`
  - 文档级 contribution 构造与全集聚合。
  - 当前 evidence 主要是 excerpt + document_id。

- `apps/api/app/archive_knowledge/quality_gate_policy.py`
  - 当前质量门禁实际执行逻辑。
  - 当前主要看 batch / document scope 的 `supporting_documents`、`risk_score`、`hard_conflict`。

- `apps/api/app/archive_knowledge/contracts/knowledge_resolution.py`
  - 已定义 `KnowledgeIdentityKey`、`CrossDocumentMatchCandidate`、`KnowledgeMergeDecision`、`CanonicalKnowledgeItem` 等库级归并模型。
  - 当前设计比实际产物更先进，应优先把这些模型真正用于正式知识归并。

- `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`
  - 原设计已经明确 P1 一等对象不应只有实体、事件、流程，还包括规则、指标、证据、版本等。

- `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-知识质量与图谱质量保障设计.md`
  - 已定义内容质量、关系质量、图谱质量、证据优先、跨文档同知识验证等原则。

## 5. 当前主要问题

### 5.1 抽取 schema 过窄

当前实现中的结构化 schema 只支持：

- `entity`
- `event`
- `process`

当前关系只支持：

- `describes`
- `owned_by`
- `part_of`
- `operational_exchange`
- `participates_in_exchange`
- `scoped_by`
- `process_scoped_by`

这会导致规则、指标、约束、接口、数据对象、文档工件、需求、决策等内容被挤入 `entity.category`，产生语义混杂。

### 5.2 类别体系失控

当前类别存在中英文混用和粒度混用，例如：

- `system`
- `系统`
- `system_or_service`
- `service`
- `service_taxonomy`
- `domain_concept`
- `architecture_concept`

这说明 category 目前是自由文本，而不是受控词表。

### 5.3 证据不够强

当前大部分知识项有 excerpt，但缺少：

- 页码。
- 章节。
- block id。
- chunk id。
- segment id。
- anchor id。
- evidence role。
- evidence confidence。

因此系统能展示“摘录”，但不能稳定回答“这条知识来自原文哪里”。

### 5.4 缺定义与语义边界

当前知识对象通常只有：

- name。
- category。
- aliases。
- document_ids。
- evidence excerpt。

缺少：

- definition。
- summary。
- scope。
- boundary。
- exclusions。
- business meaning。
- why this item matters。

下游系统使用时会退化为“名词表检索”，很难转成需求、流程、设计对象。

### 5.5 关系语义不足

`document_mentions` 占关系大头，真正业务关系占比有限。

当前关系能表达“属于、描述、拥有、交换”，但不够表达：

- 流程步骤。
- 输入输出。
- 规则约束。
- 指标度量。
- 接口提供。
- 数据流向。
- 版本替代。
- 冲突和修订。

### 5.6 库级归并没有真正收口

当前存在同名跨类型重复，例如同一名称同时作为 entity 和 process 出现。

原因是当前聚合仍较依赖名称和简单 alias，而不是完整使用：

- object type。
- normalized name。
- aliases。
- definition signature。
- relation neighborhood。
- evidence refs。
- policy snapshot。

设计中已经有库级归并模型，下一轮应把它从“契约定义”推进到“实际产物”。

### 5.7 质量门禁偏粗

当前质量门禁更像批次级或文档级 gate，不是对象级内容质量评估。

应该补齐：

- item 级质量。
- relation 级质量。
- publication batch 级质量。

并将结果写回知识项、关系和质量报告。

## 6. 改进目标

下一轮 P1 知识质量改造应达成以下目标：

1. 每个正式知识对象都有稳定类型、受控类别、定义摘要和可定位证据。
2. 每条正式业务关系都有端点类型约束、方向约束、证据支撑和置信度。
3. 跨文档相同知识能被识别、合并、更新或标记冲突。
4. 质量门禁能解释至少以下原因：
   - 证据不足。
   - 缺少定义。
   - 类别不合法。
   - 关系端点不兼容。
   - 关系方向异常。
   - 重复或冲突。
5. 发布态知识不再只是候选集合，而是 `CanonicalKnowledgeItem` 驱动的规范知识集合。

## 7. 建议扩充的顶层知识对象类型

不建议继续只扩 `entity.category`。应扩充顶层 item_type。

建议第一批支持：

| item_type | 含义 | 说明 |
| --- | --- | --- |
| `entity` | 稳定领域对象 | 组织、角色、系统、服务、设施、数据对象等 |
| `event` | 触发或发生的动作 | 状态变化、版本变化、关键业务事件 |
| `process` | 有步骤和输入输出的流程 | 运行流程、治理流程、工程流程 |
| `rule` | 规则、约束、条件 | 制度、判定条件、边界规则、合规要求 |
| `metric` | 指标、口径、阈值 | 统计指标、质量指标、运行指标 |
| `evidence` | 一等证据对象 | 可定位原文证据，不应只作为 item 内嵌字段 |
| `document_artifact` | 文档工件 | AV/OV/SV/TV、章节、表格、模型图 |
| `requirement` | 需求或能力要求 | 面向 P2/P3 的需求输入 |
| `decision` | 决策或治理结论 | 审核、发布、合并、修订、驳回 |
| `constraint` | 约束 | 可作为 rule 的轻量子类，也可独立建模 |

第一阶段可以不一次性全量实现，但 schema 设计应预留这些类型，避免继续把所有对象压进 entity。

## 8. 建议受控实体子类型

如果继续保留 `entity.category`，应改为受控词表。

建议第一批实体子类型：

| category | 含义 |
| --- | --- |
| `organization` | 组织 |
| `role` | 角色 |
| `system` | 系统 |
| `service` | 服务 |
| `capability` | 能力 |
| `function` | 功能 |
| `interface` | 接口 |
| `data_object` | 数据对象 |
| `facility` | 设施 |
| `architecture_artifact` | 架构工件 |
| `technology` | 技术 |
| `operational_node` | 运行节点 |
| `stakeholder` | 干系人 |
| `document_section` | 文档章节或结构单元 |

要求：

- 不允许中英文混用同义 category。
- 不允许 LLM 自由生成新 category。
- 对未知类别使用 `unknown` 或 `needs_classification`，进入治理队列。

## 9. 建议扩充的关系类型

关系类型应按家族分组，并为每种关系声明 source / target 约束。

### 9.1 结构关系

| relation_type | 含义 |
| --- | --- |
| `contains` | 包含 |
| `part_of` | 属于 |
| `decomposes_to` | 分解为 |
| `specializes` | 特化 |
| `instance_of` | 是某类实例 |

### 9.2 职责关系

| relation_type | 含义 |
| --- | --- |
| `owned_by` | 被拥有 |
| `operated_by` | 被运行维护 |
| `responsible_for` | 负责 |
| `governed_by` | 受治理 |

### 9.3 流程关系

| relation_type | 含义 |
| --- | --- |
| `has_step` | 流程包含步骤 |
| `precedes` | 前置于 |
| `triggers` | 触发 |
| `consumes` | 消耗输入 |
| `produces` | 产生输出 |
| `blocks` | 阻断 |

### 9.4 数据与接口关系

| relation_type | 含义 |
| --- | --- |
| `exchanges_with` | 与之交换 |
| `sends` | 发送 |
| `receives` | 接收 |
| `provides_interface` | 提供接口 |
| `uses_interface` | 使用接口 |
| `uses_data` | 使用数据 |
| `updates_data` | 更新数据 |

### 9.5 规则与指标关系

| relation_type | 含义 |
| --- | --- |
| `constrains` | 约束 |
| `applies_to` | 适用于 |
| `measures` | 度量 |
| `has_threshold` | 具有阈值 |
| `validates` | 校验 |

### 9.6 证据与治理关系

| relation_type | 含义 |
| --- | --- |
| `evidenced_by` | 由证据支撑 |
| `derived_from` | 派生自 |
| `conflicts_with` | 与之冲突 |
| `updates` | 更新 |
| `supersedes` | 替代 |
| `deprecated_by` | 被废弃 |
| `approved_by` | 被批准 |
| `rejected_by` | 被驳回 |

## 10. 关系契约要求

新增关系时，不要只添加枚举。每种关系必须具备关系契约：

- `relation_type`
- `source_item_types`
- `target_item_types`
- `source_categories`
- `target_categories`
- `direction_semantics`
- `inverse_relation_type`
- `evidence_required`
- `anchor_required`
- `min_confidence`
- `publish_allowed`
- `manual_review_required`

示例：

```json
{
  "relation_type": "constrains",
  "source_item_types": ["rule", "constraint"],
  "target_item_types": ["process", "entity", "requirement"],
  "direction_semantics": "source constrains target",
  "evidence_required": true,
  "anchor_required": true,
  "min_confidence": 0.75,
  "publish_allowed": true,
  "manual_review_required": false
}
```

## 11. Evidence 对象改造建议

将当前 evidence excerpt 升级为一等对象或标准引用。

建议字段：

```json
{
  "evidence_id": "EV-...",
  "document_id": "doc-...",
  "document_title": "...",
  "source_file_path": "...",
  "page": 12,
  "section_path": ["3", "3.2"],
  "heading": "....",
  "chunk_id": "chunk-...",
  "segment_ids": ["seg-..."],
  "anchor_ids": ["anchor-..."],
  "excerpt": "...",
  "normalized_excerpt": "...",
  "evidence_role": "name | definition | relation | constraint | metric | example",
  "supports_field": "canonical_name | category | definition | relation",
  "confidence": 0.86,
  "extraction_method": "docling + structured_llm",
  "policy_snapshot_id": "..."
}
```

验收要求：

- 正式知识项至少有一个 `evidence_role = name` 或 `definition` 的证据。
- 正式关系至少有一个 `evidence_role = relation` 的证据。
- 发布态知识必须能从对象详情跳回文档、章节、chunk 或 segment。

## 12. Definition / Summary / Boundary 改造建议

每个规范知识对象建议新增：

```json
{
  "definition": "...",
  "summary": "...",
  "scope": "...",
  "boundary": "...",
  "exclusions": [],
  "business_meaning": "...",
  "confidence": 0.82,
  "definition_evidence_refs": []
}
```

说明：

- `definition` 解释“它是什么”。
- `summary` 面向下游系统快速消费。
- `scope` 说明适用范围。
- `boundary` 说明边界。
- `exclusions` 说明不包括什么。
- `business_meaning` 说明为什么重要。

这部分可以由 `definition_summary_conflict_consolidation` 阶段产出。

## 13. 库级归并改造建议

当前设计中已有以下模型：

- `KnowledgeIdentityKey`
- `CrossDocumentMatchCandidate`
- `KnowledgeMergeDecision`
- `CanonicalKnowledgeItem`
- `ArchiveKnowledgeResolutionSnapshot`

下一轮应把它们接入正式聚合链路。

建议流程：

```text
DocumentContribution
  -> DocumentKnowledgeCandidate
  -> KnowledgeIdentityKey
  -> CrossDocumentMatchCandidate
  -> KnowledgeMergeDecision
  -> CanonicalKnowledgeItem
  -> ArchiveKnowledgeResolutionSnapshot
  -> PublicationCandidateSnapshot
```

归并判断不能只看 name，应至少组合：

- item_type。
- normalized_name。
- aliases。
- category。
- definition_signature。
- relation_neighborhood_hash。
- evidence_refs。
- source_document_ids。
- policy_snapshot_id。

归并决策应区分：

- `new`
- `same`
- `update`
- `conflict`
- `split`
- `reject`

注意：

- 已发布知识不能被新文档静默覆盖。
- 新文档改变定义、阈值、关系方向、适用范围时，应生成 revision candidate。
- 文档移出后，不应删除正式知识本体，只应重算证据支撑，必要时标记 unsupported。

## 14. 质量门禁改造建议

质量门禁应分三层。

### 14.1 Item 级

至少检查：

- `item.item_type_valid`
- `item.category_in_controlled_vocabulary`
- `item.canonical_name_noise_free`
- `item.definition_present`
- `item.evidence_traceable_to_location`
- `item.evidence_supports_name`
- `item.evidence_supports_definition`
- `item.supporting_document_count_min`
- `item.semantic_scope_clear`
- `item.granularity_consistent`

### 14.2 Relation 级

至少检查：

- `relation.relation_type_valid`
- `relation.endpoints_exist`
- `relation.endpoints_type_compatible`
- `relation.direction_valid`
- `relation.evidence_required`
- `relation.evidence_supports_both_endpoints`
- `relation.confidence_min`
- `relation.duplicate_relation_count_max`
- `relation.self_loop_allowed`

### 14.3 Publication batch 级

至少检查：

- `publication.approved_only`
- `publication.evidence_coverage_ratio_min`
- `publication.anchored_evidence_ratio_min`
- `publication.definition_coverage_ratio_min`
- `publication.low_confidence_item_ratio_max`
- `publication.low_confidence_relation_ratio_max`
- `publication.unresolved_conflict_count_max`
- `publication.orphan_item_ratio_max`

## 15. 推荐实施顺序

不要一次性大改全部 schema。建议分 6 个切片。

### Slice 1：受控词表和关系契约

目标：

- 新增 item type registry。
- 新增 category registry。
- 新增 relation contract registry。
- 保持旧 API 兼容。

产物：

- Python 常量或配置文件。
- Pydantic 校验。
- 单元测试覆盖合法/非法类型。

### Slice 2：Evidence 标准化

目标：

- 将 evidence 从 excerpt 扩展为标准对象。
- 保留旧字段，新增 `source_refs` / `evidence_refs`。
- 尽可能接入 chunk / segment / anchor。

产物：

- `EvidenceRef` / `EvidenceObject` contract。
- 文档详情页和知识详情页能展示定位信息。

### Slice 3：定义和摘要产出

目标：

- 在 structured LLM schema 中加入 definition / summary / scope / boundary。
- 在 `definition_summary_conflict_consolidation` 阶段持久化真实输出。

产物：

- 知识对象详情不再只显示 name/category/evidence。
- 质量报告能统计 definition coverage。

### Slice 4：库级归并真实化

目标：

- 让 `KnowledgeIdentityKey` 和 `KnowledgeMergeDecision` 真正参与 aggregate。
- 处理 same / update / conflict / split。

产物：

- `ArchiveKnowledgeResolutionSnapshot` 不再只是契约，而是正式运行产物。
- 图谱主节点逐步切换为 canonical item。

### Slice 5：对象级质量门禁

目标：

- 质量门禁从批次粗指标升级为 item / relation / publication batch 三层。
- 门禁结果写回质量报告和对象详情。

产物：

- 每个被阻断对象有阻断原因。
- 每条异常关系有端点、方向或证据说明。

### Slice 6：发布态出口升级

目标：

- 系统输出合同从“实体/事件/流程列表”升级为 canonical knowledge API。
- 保持旧接口适配。

产物：

- P2/P4/P5 消费的是规范对象、关系邻域、定义摘要、证据链和质量状态。

## 16. 兼容性要求

改造时必须保持以下兼容性：

- `/api/knowledge/archive/{archive_id}/summary`
- `/api/knowledge/archive/{archive_id}/graph`
- `/api/knowledge/archive/{archive_id}/entities`
- `/api/knowledge/archive/{archive_id}/events`
- `/api/knowledge/archive/{archive_id}/processes`
- `/api/knowledge/archive/{archive_id}/items/{item_id}`

建议策略：

- 新 schema 内部升级。
- 旧接口做 projection / adapter。
- 不要求前端一次性全改。
- 不破坏 P1 -> P4 当前冻结消费面。

## 17. Prompt 改造建议

当前 prompt 只要求抽实体、事件、流程和 7 类关系。

下一轮 prompt 应改成：

- 先抽 evidence units。
- 再抽 typed candidates。
- 再抽 definitions。
- 再抽 typed relations。
- 最后输出 conflicts / uncertainty。

建议 LLM 输出包含：

```json
{
  "candidates": [],
  "relations": [],
  "definitions": [],
  "evidence_units": [],
  "conflicts": [],
  "uncertain_items": []
}
```

注意：

- 不要让 LLM 自由创造 category。
- category 和 relation_type 必须来自 registry。
- 不确定对象进入 `uncertain_items`，不要强行入库。

## 18. 验收指标

下一轮改造完成后，建议以当前 active 样本重新跑一次，至少达到：

- anchored evidence coverage >= 0.8。
- definition coverage >= 0.7。
- business relation evidence coverage >= 0.8。
- orphan item ratio <= 0.35。
- category controlled vocabulary hit ratio >= 0.95。
- relation endpoint valid ratio = 1.0。
- relation direction valid ratio >= 0.9。
- curated pending ratio 明显下降，至少能自动区分 approved / warning / blocked。
- 同名跨类型重复能进入 merge / split / conflict 决策，而不是静默共存。

## 19. 不建议做的事

不要优先做：

- 只扩大 LLM 抽取数量。
- 只增加前端展示卡片。
- 只调 prompt 而不改 schema。
- 继续允许 category 自由文本发散。
- 把规则、指标、约束继续塞进 entity。
- 让发布态直接暴露单文档候选节点。

这些动作会让产物看起来更丰富，但不会真正提高知识质量。

## 20. 最重要的工程判断

P1 下一阶段的核心不是“抽更多”，而是“抽得更可证、可归并、可解释、可发布”。

优先级应为：

```text
Evidence Anchor
  -> Controlled Ontology
  -> Definition / Boundary
  -> Relation Contract
  -> Cross-document Resolution
  -> Object-level Quality Gate
  -> Canonical Publication API
```

只要沿着这条路线推进，P1 才会从“知识候选展示系统”升级为“后续 P2/P4/P5 可以可靠消费的正式业务知识底座”。
