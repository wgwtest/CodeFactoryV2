# 基础平台（Base Platform）平台数据资源底座设计-260514-2314-P2到P3首版实现设计

> 本文件是 `BasePlatform-平台数据资源底座设计.md` 的实现级补充稿。主文档回答基础平台（Base Platform）的定义、资源归属、物理存储形态和长期架构边界；本文件只回答当前仓库首版如何把 `P2 -> Base Platform -> P3` 落成代码。
>
> 本文件不是新的平级主设计文档，也不替代主文档。若本文与主文档冲突，以主文档的资源归属原则、冻结副本原则和平台统一读取原则为准。

**日期：** 2026-05-14  
**补充主题：** `P2 -> Base Platform -> P3` 首版实现设计  
**关联主设计：** `DOC/CODEX_DOC/02_设计说明/BasePlatform_基础平台/BasePlatform-平台数据资源底座设计.md`

## 1. 实现目标

首版实现目标是把当前直接链路：

```text
P2 RequirementAuthoringDocument.frozen_package
  -> P3 SoftwareDesignV2Service 直接扫描 P2 表
```

改造为目标链路：

```text
P2 发布需求规格包
  -> Base Platform 生成平台资源登记项（ArtifactEnvelope）
  -> P3 查询 Base Platform 中的需求规格包资源
  -> P3 创建会话时登记平台消费记录（ArtifactConsumption）
```

首版必须做到：

1. `P2` 发布后，平台表中有一条需求规格包（`requirement_spec_package`）资源记录。
2. 资源正文（payload）是发布时刻冻结副本，不是指向 `P2` 表的运行时引用。
3. `P3` 的 `input-packages` 默认从平台读取，而不是继续扫描 `RequirementAuthoringDocument`。
4. `P3` 创建 `P3DesignLabSession` 时记录消费事实。
5. 保留旧读取路径作为短期降级兼容，避免已有页面和测试一次性断裂。
6. 通过后端测试证明 `P2 -> Base Platform -> P3` 可查询、可消费、可追溯。

## 2. 当前代码事实

截至 2026-05-14，当前仓库事实如下。

### 2.1 `P2` 发布事实

当前 `P2` 发布入口是：

```text
POST /api/requirement-analysis/spec-items/{spec_item_id}/publish
```

对应代码：

- `apps/api/app/api/routes/requirement_spec_work_items.py`
- `apps/api/app/requirement_spec_work_items/service.py`

当前 `RequirementSpecWorkItemService.publish_item()` 的主要动作是：

1. 读取 `RequirementSpecWorkItem`。
2. 调用 `RequirementAuthoringService.freeze()` 冻结需求规格编写文档。
3. 从 `document["frozen_package"]` 中取 `structured_spec`。
4. 创建 `RequirementSpec`。
5. 回写 `RequirementSpecWorkItem.status = published_to_p3`。
6. 回写 `p3_consumable`、`published_requirement_spec_id`、`published_package_id`。

这个链路目前没有平台资源登记项，也没有平台消费记录。

### 2.2 `P3` 读取事实

当前 `P3` 输入包查询入口是：

```text
GET /api/software-design-v2/input-packages
```

对应代码：

- `apps/api/app/api/routes/software_design_v2.py`
- `apps/api/app/software_design_v2/service.py`

当前 `SoftwareDesignV2Service.list_input_packages()` 的主要动作是：

```text
查询 RequirementAuthoringDocument
  -> 过滤 frozen_package.p3_consumable = true
  -> _build_input_package(document)
```

这仍然是 `P3` 直接读取 `P2` 内部表，不符合主设计的目标链路。

### 2.3 持久化与事务事实

当前仓库使用：

```text
Base.metadata.create_all(engine)
```

而不是独立迁移流。模型注册入口是：

```text
apps/api/app/db/models/__init__.py
```

当前多个仓储方法内部直接 `commit()`，例如：

- `RequirementSpecWorkItemRepository.add_item()`
- `RequirementSpecWorkItemRepository.save_item()`
- `RequirementSpecRepository.add_spec()`

这意味着首版实现时不能简单假设：

```text
冻结 P2 文档 + 创建 RequirementSpec + 写平台 ArtifactEnvelope + 回写 WorkItem
```

天然处于一个数据库事务中。若不处理，会出现“`RequirementSpec` 已创建但平台资源未登记”或“平台资源已登记但 `WorkItem` 未回写”的半成功状态。

## 3. 实现边界

### 3.1 首版实现

首版实现以下能力：

1. 新增平台交换后端模块。
2. 新增平台资源表模型和消费记录表模型。
3. 新增平台交换服务（PlatformExchangeService）。
4. 新增平台交换应用程序接口（API）路由。
5. 改造 `P2` 发布链路，发布时写入 `requirement_spec_package` 平台资源。
6. 改造 `P3` 输入包查询链路，优先从平台资源读取。
7. 改造 `P3` 会话创建链路，创建会话后登记消费记录。
8. 补充后端测试。

### 3.2 首版不实现

首版不实现以下能力：

1. 不引入微服务拆分。
2. 不引入独立事件总线。
3. 不引入多租户权限模型。
4. 不引入对象存储或文件中心。
5. 不把 `P1/P4/P5` 资源全部落地。
6. 不重做 `P2` 或 `P3` 前端页面。
7. 不把 `P3DesignLabSession` 改成持久化表。

## 4. 后端模块设计

建议新增目录：

```text
apps/api/app/platform_exchange/
  __init__.py
  models.py
  repository.py
  service.py
apps/api/app/db/models/platform_exchange.py
apps/api/app/api/routes/platform_exchange.py
```

职责如下：

| 文件 | 职责 |
| --- | --- |
| `db/models/platform_exchange.py` | SQLAlchemy 表模型 |
| `platform_exchange/models.py` | Pydantic 命令、查询参数和响应模型 |
| `platform_exchange/repository.py` | 平台资源与消费记录读写 |
| `platform_exchange/service.py` | 发布、查询、消费、幂等、哈希摘要计算、`P2/P3` 映射 |
| `api/routes/platform_exchange.py` | 平台交换 HTTP API |

模型注册要求：

```text
apps/api/app/db/models/__init__.py
```

必须导入 `platform_exchange` 模型模块，确保 `Base.metadata.create_all(engine)` 能创建新表。

路由注册要求：

```text
apps/api/app/main.py
```

必须 include `platform_exchange_router`。

## 5. 数据表设计

### 5.1 `platform_exchange_artifacts`

表模型建议命名：

```text
PlatformExchangeArtifact
```

最小字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| `artifact_id` | `String` 主键 | 平台资源 ID |
| `artifact_type` | `String(64)` | 首版固定支持 `requirement_spec_package` |
| `artifact_version` | `String(32)` | 业务版本，首版使用 `RequirementSpecWorkItem.version` |
| `schema_version` | `String(32)` | 首版使用 `requirement_spec_package.v1` |
| `producer_stage` | `String(16)` | 首版为 `P2` |
| `producer_ref_id` | `String(255)` | 首版为 `RequirementSpecWorkItem.id` |
| `producer_ref_type` | `String(128)` | 首版为 `RequirementSpecWorkItem` |
| `lifecycle_status` | `String(32)` | `published / superseded / revoked` |
| `payload_mode` | `String(32)` | 首版固定为 `inline` |
| `payload` | `JSON` | 平台资源正文冻结副本 |
| `payload_ref` | `String` 可空 | 首版为空 |
| `payload_hash` | `String(128)` | 规范化 JSON 后计算 |
| `parent_artifact_ids` | `JSON` | 首版可为空列表 |
| `source_trace` | `JSON` | 发布来源追溯 |
| `idempotency_key` | `String(512)` 唯一 | 幂等键 |
| `created_at` | `DateTime` | 平台登记时间 |
| `frozen_at` | `DateTime` 或 `String` | 上游冻结时间 |
| `published_at` | `DateTime` | 平台发布时间 |
| `published_by` | `String` 可空 | 首版可为 `system` |

索引建议：

- `artifact_type + producer_stage + lifecycle_status`
- `producer_stage + producer_ref_id`
- `idempotency_key` 唯一索引

### 5.2 `platform_exchange_consumptions`

表模型建议命名：

```text
PlatformExchangeConsumption
```

最小字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| `consumption_id` | `String` 主键 | 平台消费记录 ID |
| `artifact_id` | `String` | 被消费平台资源 ID |
| `consumer_stage` | `String(16)` | 首版为 `P3` |
| `consumer_ref_id` | `String(255)` | 首版为 `P3DesignLabSession.session_id` |
| `consumer_ref_type` | `String(128)` | 首版为 `P3DesignLabSession` |
| `consumption_mode` | `String(32)` | 首版为 `snapshot` |
| `accepted_schema_version` | `String(32)` | 首版为 `requirement_spec_package.v1` |
| `result_status` | `String(32)` | `accepted / rejected / failed` |
| `result_message` | `String` 可空 | 消费说明 |
| `consumed_at` | `DateTime` | 消费时间 |

索引建议：

- `artifact_id`
- `consumer_stage + consumer_ref_id`

## 6. 平台交换服务设计

### 6.1 服务对象

新增：

```text
PlatformExchangeService
```

首版方法：

| 方法 | 用途 |
| --- | --- |
| `publish_artifact(command)` | 通用发布入口 |
| `publish_requirement_spec_package(command)` | `P2` 需求规格包发布入口 |
| `list_artifacts(filters)` | 查询平台资源 |
| `get_artifact(artifact_id)` | 读取平台资源 |
| `consume_artifact(command)` | 登记平台消费 |
| `list_consumptions(filters)` | 查询消费记录 |

### 6.2 哈希与幂等

资源正文哈希摘要（payload hash）必须基于规范化 JSON 计算：

```text
json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
```

首版幂等键：

```text
producer_stage + artifact_type + producer_ref_id + artifact_version + payload_hash
```

处理规则：

1. 若同一幂等键已存在，返回已有资源。
2. 若同一 `producer_stage + artifact_type + producer_ref_id + artifact_version` 已存在但 `payload_hash` 不同，返回版本冲突，要求上游生成新版本。
3. 不允许覆盖既有 `payload`。

### 6.3 状态替代规则

首版发布新版本时：

1. 新资源写入为 `published`。
2. 同一 `producer_stage + artifact_type + producer_ref_id` 下旧的 `published` 资源可标记为 `superseded`。
3. 已存在的消费记录仍指向旧 `artifact_id`。

## 7. `P2` 发布链路改造

### 7.1 发布时资源组装

在 `RequirementSpecWorkItemService.publish_item()` 中，冻结文档和创建 `RequirementSpec` 后，组装需求规格包资源正文（RequirementSpecPackage）。

资源正文建议包含：

| 字段 | 来源 |
| --- | --- |
| `standard_document` | `document["frozen_package"]["standard_document"]` |
| `structured_spec` | `document["frozen_package"]["structured_spec"]` |
| `annotations` | `document["frozen_package"]["annotations"]` |
| `check_result` | `document["check_result"]` |
| `knowledge_binding` | `item.knowledge_binding` 或 `document["semantic_state"]["knowledge_binding"]` |
| `source_trace` | 由 `P2` 发布服务组装 |
| `p3_consumable` | `true` |

`source_trace` 至少包含：

```text
spec_item_id
authoring_document_id
requirement_spec_id
requirement_spec_version
frozen_at
published_from
```

### 7.2 发布后回写

`RequirementSpecWorkItem` 当前已有：

```text
published_requirement_spec_id
published_package_id
p3_consumable
```

首版建议：

1. `published_requirement_spec_id` 继续指向当前 `RequirementSpec.id`。
2. `published_package_id` 改为平台 `artifact_id`。
3. `p3_consumable` 保持 `True`。
4. `status` 保持 `published_to_p3`。

这里 `published_package_id` 的语义应从“P3 输入包 ID”收敛为“平台资源 ID”。这是必要的，因为主链权威读取源已经从 `P2` 内部表转为平台资源表。

### 7.3 事务处理

当前仓储内部多处直接 `commit()`，短期无法天然保证完整发布链路的单事务原子性。

首版建议采用两步策略：

1. **本次实现内的最小修正**
   - `PlatformExchangeRepository` 支持 `add_*` 和 `save_*`，但由服务层控制最终 `commit()`。
   - `P2` 发布中“写平台资源 + 回写 `RequirementSpecWorkItem`”尽量放在同一个 `session.commit()` 中。
   - 对已经由旧仓储提前提交的 `RequirementSpec`，通过幂等键和版本冲突检测保证重试可恢复。

2. **后续重构方向**
   - 将 `RequirementSpecRepository.add_spec()`、`RequirementSpecWorkItemRepository.save_item()` 拆分为 `add/flush/commit` 语义。
   - 让 `P2` 发布完整链路由应用服务统一提交。

首版不应为了追求事务完美而大面积重构所有既有仓储。当前更稳妥的做法是把平台写入设计成幂等、可重试、可检测冲突。

## 8. `P3` 读取与消费改造

### 8.1 输入包查询

改造：

```text
SoftwareDesignV2Service.list_input_packages()
```

目标读取路径：

```text
PlatformExchangeService.list_artifacts(
  artifact_type="requirement_spec_package",
  producer_stage="P2",
  lifecycle_status="published"
)
  -> map ArtifactEnvelope.payload to P3DesignInputPackage
```

映射规则：

| `P3DesignInputPackage` 字段 | 平台来源 |
| --- | --- |
| `input_package_id` | `artifact_id` |
| `source_document_id` | `payload.source_trace.authoring_document_id` |
| `source_title` | `payload.standard_document.title` 或 `source_trace.title` |
| `standard_document` | `payload.standard_document` |
| `structured_spec` | `payload.structured_spec` |
| `annotations` | `payload.annotations` |
| `knowledge_binding` | `payload.knowledge_binding` |
| `frozen_at` | `source_trace.frozen_at` |
| `p3_consumable` | `payload.p3_consumable` |
| `related_designs` | 继续用当前内存会话关系计算 |

### 8.2 降级兼容

首版建议保留旧扫描路径作为降级：

```text
优先读 Base Platform
  -> 若平台表中无 requirement_spec_package
    -> 回退到旧的 RequirementAuthoringDocument.frozen_package 扫描
```

降级规则必须受控：

1. 只允许平台表为空时回退。
2. 一旦平台存在 `P2` 已发布资源，`P3` 默认不得再混合读取旧路径。
3. 测试中应覆盖平台路径，不能只依赖回退路径。

### 8.3 会话创建与消费记录

改造：

```text
SoftwareDesignV2Service.create_session()
```

目标行为：

1. 根据 `input_package_id` 读取平台资源。
2. 创建当前内存态 `P3DesignLabSession`。
3. 调用 `PlatformExchangeService.consume_artifact()` 登记消费记录。
4. 返回原有会话响应结构，保持页面兼容。

消费命令建议：

```text
artifact_id = input_package_id
consumer_stage = P3
consumer_ref_id = session_id
consumer_ref_type = P3DesignLabSession
consumption_mode = snapshot
accepted_schema_version = requirement_spec_package.v1
result_status = accepted
```

## 9. 平台 API 设计

新增路由：

```text
apps/api/app/api/routes/platform_exchange.py
```

首版接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/platform-exchange/artifacts` | 查询平台资源 |
| `GET` | `/api/platform-exchange/artifacts/{artifact_id}` | 获取资源详情 |
| `POST` | `/api/platform-exchange/artifacts` | 通用发布入口，首版可仅内部使用 |
| `POST` | `/api/platform-exchange/artifacts/{artifact_id}/consume` | 登记消费 |
| `GET` | `/api/platform-exchange/consumptions` | 查询消费记录 |

首版 `P2` 发布不要求前端直接调用 `/platform-exchange/artifacts`。更合适的入口仍是：

```text
POST /api/requirement-analysis/spec-items/{spec_item_id}/publish
```

平台 API 主要用于调试、验收和后续跨阶段统一查询。

## 10. 错误处理

首版错误分类：

| 场景 | 建议状态码 | 说明 |
| --- | --- | --- |
| 资源不存在 | `404` | `artifact_id` 不存在 |
| 资源版本冲突 | `409` | 同一版本已有不同 payload hash |
| schema 不支持 | `400` | 当前消费者不接受该结构模式版本 |
| 被撤销资源不可消费 | `409` | `revoked` 不允许消费 |
| 参数不合法 | `400` | 请求字段缺失或非法 |

`P3` 创建会话时，若消费登记失败：

1. 首版建议直接返回失败，不应静默忽略。
2. 因当前 `P3DesignLabSession` 是内存态对象，消费失败后应删除刚创建的内存会话，避免出现无消费记录的会话。

## 11. 测试方案

### 11.1 新增测试

新增：

```text
apps/api/tests/test_platform_exchange_p2_p3_api.py
```

建议覆盖：

1. `P2` 发布后生成平台资源。
2. 平台资源 `artifact_type = requirement_spec_package`。
3. 平台资源 `payload` 包含 `standard_document`、`structured_spec`、`source_trace`。
4. 平台资源 `producer_ref_id` 指向 `RequirementSpecWorkItem.id`。
5. `P3` 的 `GET /api/software-design-v2/input-packages` 返回平台资源映射出的输入包。
6. `P3` 创建会话后生成 `ArtifactConsumption`。
7. 重复发布同一版本不会生成不可区分的重复资源。
8. 平台资源被 `superseded` 后，默认查询只返回最新 `published` 资源。

### 11.2 回归测试

必须继续通过：

```bash
uv run pytest apps/api/tests/test_requirement_spec_work_items_api.py apps/api/tests/test_software_design_v2_api.py -q
```

新增测试通过后，再跑：

```bash
uv run pytest apps/api/tests/test_platform_exchange_p2_p3_api.py -q
```

若 `P3` 响应结构发生变化，应优先保持旧字段兼容，而不是同步改前端页面。

## 12. 实施顺序

建议按以下顺序实现：

1. 新增 `PlatformExchangeArtifact` 和 `PlatformExchangeConsumption` 表模型，并注册到 `db.models.__init__`。
2. 新增 `platform_exchange` 的 Pydantic 模型、仓储和服务。
3. 新增平台交换路由，并注册到 `main.py`。
4. 编写最小平台 API 测试，先验证可发布、可查询、可消费。
5. 改造 `P2` 发布链路，写入 `RequirementSpecPackage` 平台资源。
6. 改造 `P3` 输入包查询，优先平台、无平台时回退旧扫描。
7. 改造 `P3` 会话创建，登记消费记录。
8. 补齐 `P2 -> Base Platform -> P3` 链路测试。
9. 跑 P2、P3 既有后端回归测试。

## 13. 验收标准

首版实现完成时，应满足：

1. `POST /api/requirement-analysis/spec-items/{id}/publish` 返回的 `published_package_id` 是平台 `artifact_id`。
2. `GET /api/platform-exchange/artifacts?artifact_type=requirement_spec_package` 能查到该资源。
3. 资源详情中的 `payload` 是完整冻结副本，不需要回源 `P2` 才能给 `P3` 使用。
4. `GET /api/software-design-v2/input-packages` 返回的平台输入包 `input_package_id = artifact_id`。
5. `POST /api/software-design-v2/sessions` 成功后，`GET /api/platform-exchange/consumptions` 能查到对应消费记录。
6. 旧的 `test_requirement_spec_work_items_api.py` 和 `test_software_design_v2_api.py` 不回退。
7. 新增 `test_platform_exchange_p2_p3_api.py` 覆盖平台主链。

## 14. 风险与约束

### 14.1 事务半成功风险

当前仓储提交边界分散，是首版最大实现风险。首版必须依赖幂等键、版本冲突检测和可重试发布降低风险；后续再统一仓储事务语义。

### 14.2 `published_package_id` 语义迁移风险

当前 `published_package_id` 更像 `P3` 输入包 ID。首版改成平台 `artifact_id` 后，必须确认前端和测试没有依赖旧格式 `p3-input-*`。

### 14.3 旧路径回退风险

保留旧扫描路径是为了平滑迁移，但不能让它长期存在为默认事实源。首版测试必须证明平台路径被真实使用。

### 14.4 `P3DesignLabSession` 非持久化风险

当前 `P3DesignLabSession` 是进程内内存对象。消费记录可以落库，但会话本身重启后丢失。这是当前 `P3` 既有约束，不在本次基础平台首版中解决。

## 15. 结论

本次实现应以“平台资源副本成为 `P2 -> P3` 正式读取源”为主线，不应只新增一组平台 API 而让 `P3` 继续直查 `P2` 表。

首版最重要的代码判断标准是：

```text
P3 能否在不读取 RequirementAuthoringDocument 的前提下，
仅凭 platform_exchange_artifacts.payload 创建 P3DesignInputPackage。
```

如果这个标准没有满足，基础平台只是被旁路写入了一条记录，并没有真正成为数据资源底座。
