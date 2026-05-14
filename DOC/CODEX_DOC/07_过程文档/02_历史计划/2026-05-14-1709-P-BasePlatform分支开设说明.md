# P-BasePlatform 分支开设说明

## 1. 文档目的

本文用于说明为什么 `P2 -> P3` 平台交换层不应继续塞入当前 `P2` 需求分析系统分支，而应单独开设跨阶段实现分支。

本文不是平台交换层的完整设计说明，完整设计事实源仍以以下文档为准：

- `DOC/CODEX_DOC/02_设计说明/00_总纲/03-P1-P6数据互联互通与平台交换层设计.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计-260513-1105-需规管理发布工作流补充.md`
- `DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计.md`

本文只回答：

- 新分支要解决什么问题；
- 当前 `P2` 分支保留什么工作；
- 新分支首版做什么、不做什么；
- 如何验收新分支是否真正打通 `P2 -> P3` 交换层。

## 2. 建议分支

建议新建分支：

```text
feat/p-base-platform
```

建议从当前已合入或即将合入的 `P2` 需规管理发布实现基线切出。若当前 `P2` 分支仍有未提交修复，应先完成或明确暂存边界，再开设本分支，避免把排版修复、删除按钮、发布 409 提示等 `P2` 局部问题混入交换层分支。

## 3. 分支开设理由

平台交换层不是 `P2` 的内部子模块。

当前 `P2 -> P3` 的实现态是：

```text
RequirementSpecWorkItem
  -> RequirementAuthoringDocument.frozen_package
  -> P3DesignInputPackage
  -> P3DesignLabSession
```

该链路已经能支撑当前页面测试，但仍存在以下架构缺口：

- `P3` 当前直接扫描 `P2` 冻结文档，而不是查询统一成果物交换登记。
- 发布人、发布时间、消费时间、消费结果、幂等键和内容 hash 没有统一记录。
- `P3` 消费后没有独立 `ArtifactConsumption` 记录。
- 后续 `P3 -> P4`、`P4 -> P5`、`P1 ~ P5 -> P6` 也需要同一类成果物交换机制。

因此，完整平台交换层应作为跨阶段公共能力实现，而不是放进 `requirement_spec_work_items` 或 `requirement_authoring` 内部。

## 4. 当前 P2 分支保留范围

当前 `P2` 分支适合继续完成以下局部事项：

| 范围 | 说明 |
| --- | --- |
| 需规对象管理 | `4.1` 需求规格说明管理、新建、删除、进入配置、发布 |
| 发布前置校验 | 阻断型缺口检查、409 业务提示 |
| P2 发布状态展示 | `published_to_p3`、`p3_consumable`、`published_requirement_spec_id`、`published_package_id` |
| 最小发布元数据补齐 | 可补 `published_at`、`published_by`、`publish_action_id`，但不引入完整交换层 |
| P2 文档同步 | 保持 P2 主设计与补充设计一致 |

当前 `P2` 分支不应承担：

- 新增平台级 `ArtifactEnvelope` / `ArtifactConsumption` 域模型；
- 改造 `P3` 输入包读取路径；
- 建立跨阶段成果物查询接口；
- 实现 `P3 -> P4`、`P4 -> P5` 的交换层延伸；
- 建立全平台成果物事件 outbox。

## 5. 新分支首版目标

`feat/p-base-platform` 首版目标是：

```text
P2 发布冻结需规包
  -> 平台交换层登记 ArtifactEnvelope
  -> P3 查询可消费 RequirementSpecPackage
  -> P3 消费时登记 ArtifactConsumption
  -> P3 创建 P3DesignInputPackage / P3DesignLabSession
```

首版只打通 `P2 -> P3`，不要求一次覆盖全部阶段。

## 6. 首版对象模型

### 6.1 ArtifactEnvelope

最小字段：

| 字段 | 说明 |
| --- | --- |
| `artifact_id` | 平台成果物 ID |
| `artifact_type` | 首版取 `requirement_spec_package` |
| `artifact_version` | 业务版本，可从需规对象版本派生 |
| `schema_version` | 成果物 schema 版本 |
| `producer_stage` | 固定为 `P2` |
| `producer_ref_id` | `RequirementSpecWorkItem.id` 或发布记录 ID |
| `lifecycle_status` | `published` / `revoked` / `superseded` |
| `payload_mode` | `inline` 或 `object_ref`，首版可先用 `inline` |
| `payload_ref` | 大对象引用，首版可为空 |
| `payload_hash` | 冻结包内容 hash |
| `parent_artifact_ids` | 上游成果物链 |
| `source_trace` | 来源与追溯信息 |
| `idempotency_key` | 防重复发布键 |
| `created_at` | 登记时间 |
| `frozen_at` | P2 文档冻结时间 |
| `published_at` | 发布到交换层时间 |
| `published_by` | 发布人或系统操作者 |

### 6.2 ArtifactConsumption

最小字段：

| 字段 | 说明 |
| --- | --- |
| `consumption_id` | 消费记录 ID |
| `artifact_id` | 被消费成果物 |
| `consumer_stage` | 固定为 `P3` |
| `consumer_ref_id` | `P3DesignLabSession.session_id` 或输入快照 ID |
| `consumption_mode` | `snapshot` |
| `accepted_schema_version` | P3 实际接受的 schema 版本 |
| `result_status` | `accepted` / `rejected` / `failed` |
| `result_message` | 消费结果说明 |
| `consumed_at` | 消费时间 |

### 6.3 RequirementSpecPackage

首版 payload 可复用当前冻结包内容，但需要明确包装：

| 字段 | 来源 |
| --- | --- |
| `standard_document` | `frozen_package.standard_document` |
| `structured_spec` | `frozen_package.structured_spec` |
| `annotations` | `frozen_package.annotations` |
| `check_result` | `RequirementAuthoringDocument.check_result` |
| `knowledge_binding` | `semantic_state.knowledge_binding` |
| `source_trace` | 需规对象、模板、知识绑定、分析会话、冻结时间 |
| `p3_consumable` | 当前应为 `true` |

## 7. 首版 API 边界

建议新增平台交换层 API 族：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/platform-exchange/artifacts` | 查询可消费成果物 |
| `GET` | `/platform-exchange/artifacts/{artifact_id}` | 获取成果物详情 |
| `POST` | `/platform-exchange/artifacts` | 登记成果物，首版可仅由 P2 发布服务内部调用 |
| `POST` | `/platform-exchange/artifacts/{artifact_id}/consume` | 登记 P3 消费 |
| `GET` | `/platform-exchange/consumptions` | 查询消费记录 |

`P2` 对外仍保留：

```text
POST /api/requirement-analysis/spec-items/{id}/publish
```

但发布服务内部应在冻结和创建 `RequirementSpec` 后登记 `ArtifactEnvelope`。

`P3` 首版仍保留：

```text
GET /api/software-design-v2/input-packages
```

但数据来源应从“直接扫描 `RequirementAuthoringDocument.frozen_package`”逐步切换为“查询平台交换层中 `artifact_type=requirement_spec_package` 且可消费的成果物”。

## 8. 首版非目标

本分支首版不做：

- 不重做 `P2` 需规管理 UI。
- 不重做 `P3 Design Lab` 页面布局。
- 不实现全量 `P3 -> P4` 交换层。
- 不实现完整事件 outbox 和异步队列。
- 不做多租户权限系统。
- 不把 `P3Order` 恢复为新版主接口术语。
- 不要求拆成独立微服务。

## 9. 建议实施步骤

1. 新增 `platform_exchange` 后端域模型和仓储。
2. 新增 `ArtifactEnvelope`、`ArtifactConsumption` 的 Pydantic 模型。
3. 新增平台交换层 API 路由和最小测试。
4. 改造 P2 发布服务：发布成功后登记 `ArtifactEnvelope`。
5. 改造 P3 输入包服务：优先从交换层读取 `RequirementSpecPackage`，保留旧扫描路径作为降级或迁移兼容。
6. P3 创建设计会话时登记 `ArtifactConsumption`。
7. 补充合同测试：P2 发布后，P3 可通过交换层看到同一成果物；P3 消费后有消费记录。
8. 更新文档：回写交换层设计、P2/P3 节点合同、验收大纲和测试记录。

## 10. 验收标准

首版通过标准：

1. P2 发布一条完整需规后，生成 `ArtifactEnvelope<RequirementSpecPackage>`。
2. 成果物包含 `published_at`、`published_by`、`frozen_at`、`payload_hash`、`source_trace`。
3. P3 通过交换层能查询到该成果物，并转换为 `P3DesignInputPackage`。
4. P3 基于该输入包创建设计会话后，生成 `ArtifactConsumption`。
5. 再次发布同一版本不会重复生成不可区分的成果物，至少具备幂等键或版本区分。
6. 当前 `/api/software-design-v2/input-packages` 仍可被 `/p3-design-lab` 使用。
7. 现有 P2 需规管理测试和 P3 Design Lab 测试不回退。

建议验证命令：

```bash
npm --prefix apps/web test -- RequirementAnalysisLabPage.test.tsx P3DesignLabPage.test.tsx
npm --prefix apps/web run build
pytest apps/api/tests/test_requirement_spec_work_items_api.py
```

若新增 API 测试，应补充类似：

```bash
pytest apps/api/tests/test_platform_exchange_p2_p3_api.py
```

## 11. 风险与控制

| 风险 | 控制 |
| --- | --- |
| 交换层侵入 P2 / P3 业务逻辑 | 交换层只保存成果物元数据、payload、消费记录，不生成需求或设计 |
| 新旧读取路径冲突 | 首版允许 P3 输入包服务保留旧扫描路径，但应明确优先级和降级日志 |
| 发布审计仍不完整 | 首版必须补 `published_by`、`published_at`、`payload_hash`、`source_trace` |
| 过早泛化到全平台 | 首版只做 `P2 -> P3`，但模型命名保持可扩展 |
| UI 被迫大改 | 不改 P2/P3 主界面，只保持现有接口返回兼容 |

## 12. 当前状态

`已开设本地分支：feat/p-base-platform；工作树：.worktrees/p-base-platform`

本分支已从当前 `main` 基线 `32d0e02` 创建。后续首版实现应保持为平台基础能力，不并入 P2 或 P3 单一业务分支。
