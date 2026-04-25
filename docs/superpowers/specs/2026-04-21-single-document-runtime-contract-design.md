# 单文档运行数据契约设计

## 目的

当前系统已经能产出：

- 文档级 contribution
- archive 级 knowledge payload
- 审核/发布数据

但还不能直接支撑新的 `/archives` 工作台里“单文档处理状态图 + 三种观察窗”的真实运行态需求。

本设计的目标是先定义并实现一套 **13 阶段统一后端运行数据契约**，把当前真实产物映射为可消费的运行数据，而不是一次性重写整条处理引擎。

## 当前真实后端链路

现有正式链路大致是：

1. `ArchiveExtractionService.build_archive(...)`
2. `build_archive_knowledge(...)`
3. `discover_documents(...)`
4. `ParsingService.parse_file(...)`
5. `build_document_contribution(...)`
6. `DocumentArtifactRepository.upsert(...)`
7. `aggregate_document_contributions(...)`
8. `ArchiveKnowledgeService` 对外提供 summary / graph / documents / items / publication

这条链当前已经有真实数据，但问题是：

- 中间阶段没有统一快照
- 节点/边对象没有统一契约
- 没有对象级事件流
- 观察窗所需的阶段/节点/边 payload 不存在

## 目标 13 阶段

统一阶段如下：

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

## 本次实现范围

本次不是重写引擎，而是做三件事：

1. 新增统一契约模型
2. 把当前真实产物映射成 13 阶段运行数据
3. 新增单文档 runtime API

## 统一契约模型

新增模型位于：

- `apps/api/app/archive_knowledge/runtime_contract.py`

核心对象：

- `DocumentRuntimeContract`
- `RuntimeStageSnapshot`
- `RuntimeStageGraph`
- `RuntimeGraphNode`
- `RuntimeGraphEdge`
- `RuntimeObserverPayload`
- `RuntimeEvent`
- `RuntimeSummarySection`

统一状态枚举：

- `pending`
- `running`
- `completed`
- `blocked`
- `warning`
- `unavailable`

统一观察窗模式：

- `stage`
- `node`
- `edge`

## 映射服务

新增映射服务位于：

- `apps/api/app/archive_knowledge/runtime_service.py`

服务职责：

1. 从当前真实产物收集上下文：
   - manifest document source info
   - document contribution
   - build state
   - publication overview
2. 统一推断 13 阶段状态
3. 为每个阶段构建：
   - graph nodes / edges
   - stage observer
   - node observers
   - edge observers

当前映射策略：

- 有真实持久化对象的阶段优先用真实数据
- 暂未持久化的阶段允许用 `derived` 节点/边映射，但会显式标记 `origin = derived`
- 当前完全没有真实可依托对象时，标记为 `unavailable`

## 新接口

新增接口：

- `GET /api/knowledge/archive/{archive_id}/documents/{document_id}/runtime`

返回内容：

- 文档标题
- 当前阶段
- 文档总体状态
- runtime 契约来源模式
- 已持久化阶段列表
- 13 阶段运行快照

新增顶层契约字段：

- `runtime_mode`
  - `persisted`：13 个阶段都来自真实持久化快照
  - `hybrid`：部分阶段来自真实持久化快照，其余阶段由 runtime service 派生
  - `derived`：当前文档没有持久化阶段快照，整份 runtime 由现有知识产物派生
  - `legacy_fallback`：当前文档来自旧知识库产物，runtime 通过 legacy payload 兜底构建
- `persisted_stage_ids`
  - 按 13 阶段顺序返回当前已经真实持久化的阶段 id 列表

## 与前端运行工作台的关系

这套契约直接服务于：

- 单文档处理状态图
- 阶段观察窗
- 节点观察窗
- 边观察窗

它允许前端后续做到：

- 根据 `current_stage_id` 自动落当前阶段
- 按阶段切换图谱快照
- 点击节点和边直接进入对应观察窗
- 在运行中阶段显示实时流主区

## 当前版本的限制

这次实现仍然有明确限制：

1. `definition_summary_conflict_consolidation` 还没有真实持久化对象，当前为派生映射
2. `quality_gate` 目前是根据 evidence / review / publication 状态推断的门禁对象，而不是独立持久化门禁引擎
3. 事件流仍然是从现有对象推导的观察流，不是后台独立事件总线

## 后续推荐落地顺序

1. 让 `Asset Intake / Evidence Pack / Quality Gate` 三个阶段先拥有真实阶段对象持久化
2. 再把 `Definition / Conflict` 从派生映射升级成真实阶段对象
3. 最后让单知识库与全局运行页复用同一套 runtime contract 扩展出更高层级的运行数据
