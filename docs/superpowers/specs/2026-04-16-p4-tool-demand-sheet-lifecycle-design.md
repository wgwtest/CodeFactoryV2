# P4.2.1 工具需求单生命周期与状态约束设计

**日期：** 2026-04-16

**对应节点：**
- `P4.2.1` 协议与对象模型

## 1. 问题定义

当前 `P4.2` 闭环规格已经定义了总单与叶子项的处理状态，但没有把以下约束单独固定下来：

- `P3` 撤销工单
- `P4` 驳回工单
- 撤销与驳回的角色边界
- 终态留痕与审计字段
- 工单业务生命周期与处理进度状态的分离

如果这部分继续混在“输入工序链闭环”总规格里，后续实现很容易把 `processing / ready / failed` 之类处理态误当成完整生命周期，进而出现：

- 想“撤销”时只能物理删除运行时 JSON
- `P4` 无法表达“驳回但保留记录”
- `P5` 无法区分“还没做好”、“被驳回了”还是“需求源主动撤回了”

因此，`P4.2.1` 必须单独定义“工具需求单”的生命周期约束。

同时需要把 `工具需求单` 明确提升为 `P3 / P4 / P5` 之间的主干交付流对象，而不是只存在于某个模拟页里的临时运行态。

## 2. 设计目标

- 明确区分“业务生命周期状态”和“处理进度状态”
- 明确区分“撤销”和“驳回”
- 固定 `P3 / P4 / P5` 的动作边界
- 固定“待审定 / 已审定 / 已交付 / P4 闭环完成”的完成判定
- 要求所有生命周期终态保留记录，不允许把删除文件当业务动作
- 给后续 API、数据模型、页面动作提供稳定契约

## 3. 核心区分

### 3.1 撤销 vs 驳回

`撤销`：

- 发起方是 `P3` 或未来真实需求提出方
- 语义是“需求源主动收回这张工单”
- 不是 `P4` 的判断结论

`驳回`：

- 发起方是 `P4`
- 语义是“`P4` 认为该工单当前不满足受理条件，因此拒绝进入有效处理”
- 必须保留驳回原因和驳回记录

两者都不是物理删除。

### 3.2 生命周期状态 vs 审定状态 vs 交付状态

工单至少存在三组对外状态：

- `lifecycle_status`：工单在业务流转上的位置
- `review_status`：工单里的需求项是否都完成审定
- `delivery_status`：工单里的已批准需求项是否都已形成可交付结果

这三组状态不能继续混成一个字段。

补充约束：

- 若实现层暂时保留 `processing_status`，它也只能是内部派生进度，不能继续承担整单对外主状态语义
- 页面和跨阶段协议必须优先暴露 `lifecycle_status / review_status / delivery_status`

### 3.3 业务动作 vs 开发态清理

业务动作：

- 提交
- 接受
- 驳回
- 撤销
- 关闭

开发态清理：

- 删除本地 `.data/tool_hub/*.json`
- 重置测试现场

开发态清理不是业务能力，也不能替代生命周期接口。

## 4. 角色边界

### 4.1 `P3` / `P3-sim`

允许动作：

- 生成工单草稿
- 提交工单
- 撤销自己发出的工单

不允许动作：

- 驳回工单
- 修改 `P4` 内部处理进度
- 直接改写 `P4` 的匹配/制造结论

### 4.2 `P4`

允许动作：

- 接受工单
- 驳回工单
- 处理已接受工单
- 对单个需求项做审定
- 在审定通过后产出匹配结果与制造计划

不允许动作：

- 替 `P3` 撤销工单
- 把“删除记录”当成驳回

### 4.3 `P5` / `P5-sim`

允许动作：

- 查询工单
- 查询叶子项
- 查询进度
- 基于 `P4` 输出做消费决策

保留动作：

- 关闭工单可作为后续扩展能力

不允许动作：

- 撤销工单
- 驳回工单
- 改写 `P4` 内部处理状态

## 5. 状态模型

### 5.1 工单业务生命周期状态

`ToolDemandSheet.lifecycle_status` 建议固定为：

- `submitted`
- `accepted`
- `rejected`
- `withdrawn`
- `closed`

说明：

- `submitted`：`P3` 已正式发出，`P4` 已收到
- `accepted`：`P4` 接受受理，允许进入处理流
- `rejected`：`P4` 驳回，保留记录，终态
- `withdrawn`：`P3` 主动撤销，保留记录，终态
- `closed`：下游消费结束，终态

`draft` 可以作为 `P3` 本地页内暂存态，但不是 `P4` 侧正式工单状态。

### 5.2 工单审定状态

`ToolDemandSheet.review_status` 建议固定为：

- `pending_review`
- `reviewing`
- `reviewed`

说明：

- `pending_review`：所有叶子项都还没有最终审定结论
- `reviewing`：部分叶子项已审定，但仍有待审项
- `reviewed`：所有叶子项都已有最终审定结论

### 5.3 工单交付状态

`ToolDemandSheet.delivery_status` 建议固定为：

- `not_delivered`
- `delivering`
- `delivered`

说明：

- `not_delivered`：还没有任何被批准项形成可交付结果
- `delivering`：一部分被批准项已可交付，但仍有批准项不可交付
- `delivered`：所有被批准项都已经形成可交付结果

补充边界：

- 这里的“已交付”表示 `P4` 已经把交付物准备好，`P5` 现在可以取
- 不要求等待 `P5` 真正签收或消费成功
- 当 `lifecycle_status` 为 `rejected / withdrawn / closed` 时，`review_status / delivery_status` 必须冻结，不再推进

### 5.4 叶子项审定状态

`ToolDemandItem.review_status` 建议固定为：

- `pending_review`
- `approved_delivery`
- `approved_manufacture`
- `rejected`

说明：

- `approved_delivery`：叶子项被批准为“直接交付现有工具”
- `approved_manufacture`：叶子项被批准为“进入研制名单”
- `rejected`：叶子项在当前工单内被驳回，不进入交付和研制

### 5.5 叶子项处理状态

`ToolDemandItem.processing_status` 延续当前 `P4` 内部处理流即可：

- `accepted`
- `analyzing`
- `checking`
- `matched_existing`
- `manufacturing_pending`
- `manufacturing_in_progress`
- `ready_for_fetch`
- `failed`

但叶子项不单独拥有“撤销/驳回”语义，叶子项的业务有效性由所属总单的 `lifecycle_status` 决定。

补充约束：

- `manufacturing_pending / manufacturing_in_progress / ready_for_fetch` 只能发生在 `review_status = approved_manufacture` 之后
- “推荐未命中”不等于“已经进入研制”

即：

- 如果总单被 `withdrawn`
- 或总单被 `rejected`

则该总单下所有叶子项和其供给结果一律视为“失效但保留记录”。

## 6. 状态迁移规则

### 6.1 工单主状态迁移

固定迁移关系：

- `submitted -> accepted`
- `submitted -> rejected`
- `submitted -> withdrawn`
- `accepted -> withdrawn`
- `accepted -> closed`

禁止迁移：

- `rejected -> accepted`
- `withdrawn -> accepted`
- `closed -> accepted`
- 任一终态重新打开原工单

如果需求要重新进入处理，必须重新生成新工单，而不是直接把旧工单改回处理中。

### 6.2 工单审定状态聚合规则

聚合规则固定为：

- 全部叶子项都是 `pending_review`：`review_status = pending_review`
- 既有终态审定项，又仍存在 `pending_review`：`review_status = reviewing`
- 所有叶子项都落入最终审定结论：
  - `approved_delivery`
  - `approved_manufacture`
  - `rejected`
  则 `review_status = reviewed`

### 6.3 工单交付状态聚合规则

聚合范围只统计“已批准”的叶子项，不统计 `rejected` 项。

固定规则：

- 没有任何批准项形成交付结果：`delivery_status = not_delivered`
- 一部分批准项已形成交付结果：`delivery_status = delivering`
- 所有批准项都已形成交付结果：`delivery_status = delivered`

其中“形成交付结果”的定义为：

- `approved_delivery` 项已有正式 `fetch_manifest`
- `approved_manufacture` 项已进入 `ready_for_fetch`

### 6.4 叶子项审定规则

叶子项默认进入：

- `review_status = pending_review`

允许迁移：

- `pending_review -> approved_delivery`
- `pending_review -> approved_manufacture`
- `pending_review -> rejected`

禁止迁移：

- 终态审定结果之间直接互相改写
- 未经人工审定直接进入制造计划

补充边界：

- `P4` 的“整单驳回”用于受理层拒绝，直接让 `ToolDemandSheet.lifecycle_status = rejected`
- `P4` 的“叶子项驳回”用于逐项审定，保持整单仍处于 `accepted`

### 6.5 撤销规则

撤销由 `P3` 发起，必须满足：

- 工单属于当前需求源
- 工单尚未 `closed`
- 工单尚未 `rejected`

撤销后必须：

- 写入生命周期事件 `withdrawn`
- 记录撤销原因
- 冻结叶子项推进
- 冻结制造计划推进
- 保留整单、叶子项、计划和历史事件

### 6.6 整单驳回规则

驳回由 `P4` 发起，适用于受理判定失败或协议校验失败场景。

驳回后必须：

- 写入生命周期事件 `rejected`
- 记录驳回原因码与说明
- 不再继续处理该工单
- 保留完整记录供 `P3` 查看

### 6.7 关闭规则

关闭不是删除。

关闭表示：

- 下游消费阶段已经完成
- 该工单退出活动视图
- 但仍然保留历史可查

当前 `P5-sim` 阶段可以只预留 `closed` 契约，不要求本轮立即做关闭按钮。

### 6.8 工单完成判定

`工具需求单` 至少存在两个完成里程碑，不能混成一个“完成”：

`已审定`：

- 所有叶子项都已经落到最终审定结论
- 最终审定结论只允许是：
  - `approved_delivery`
  - `approved_manufacture`
  - `rejected`
- 此时整单 `review_status = reviewed`

`已交付`：

- 所有被批准的叶子项都已经形成可交付结果
- `approved_delivery` 项必须已有正式 `fetch_manifest`
- `approved_manufacture` 项必须已经 `ready_for_fetch`
- `rejected` 项不计入交付完成范围
- 此时整单 `delivery_status = delivered`

`P4 闭环完成`：

- 整单已经 `accepted`
- 且已经 `reviewed`
- 且所有被批准的叶子项都已经可交付

补充边界：

- `已审定` 不等于 `已交付`
- `已交付` 的语义是“P4 已准备好，P5 现在可以取”
- 不要求等待 `P5` 真正签收或消费成功
- 如果工单进入 `rejected / withdrawn / closed`，则不再继续朝“已交付”推进

## 7. 留痕与审计

每张工单必须具备事件留痕：

```yaml
lifecycle_events:
  - event_id:
    event_type:
    actor_phase:
    actor_id:
    from_status:
    to_status:
    reason_code:
    reason_message:
    occurred_at:
```

至少覆盖：

- `submitted`
- `accepted`
- `rejected`
- `withdrawn`
- `closed`

硬约束：

- 驳回必须有原因
- 撤销必须有原因
- 终态必须可追溯到操作者和时间
- 不允许“静默删除后假装没发生过”

叶子项审定还必须具备独立留痕：

```yaml
review_records:
  - record_id:
    item_id:
    decision:
    reviewed_by:
    importance_score:
    urgency_score:
    rationality_verdict:
    review_comment:
    reviewed_at:
```

至少覆盖：

- `approve_delivery`
- `approve_manufacture`
- `reject`

## 8. 对现有对象模型的约束

`ToolDemandSheet` 后续应至少补齐：

```yaml
lifecycle_status:
review_status:
delivery_status:
lifecycle_events:
last_actor_phase:
last_actor_id:
terminal_reason_code:
terminal_reason_message:
```

`ToolDemandItem` 后续应至少补齐：

```yaml
review_status:
recommendation_type:
importance_score:
urgency_score:
rationality_verdict:
review_comment:
reviewed_by:
reviewed_at:
review_records:
```

`ToolManufacturePlan` 至少要补一条受控规则：

- 只有当所属叶子项进入 `approved_manufacture`
- 才允许创建制造计划

`ToolDemandItem` 与 `ToolManufacturePlan` 还至少要补一条受控规则：

- 当所属工单进入 `rejected / withdrawn / closed`
- 不得继续向前推进
- 已有结果只允许历史查看，不允许继续作为有效供给对外消费

## 9. 页面与接口约束

### 9.1 `P3-sim`

应该拥有：

- 提交工单动作
- 撤销已提交工单动作
- 查看撤销结果与撤销原因

### 9.2 `P4`

应该拥有：

- 受理结论
- 整单驳回动作
- 叶子项审定动作
- 审定原因和评分展示
- 对已撤销工单的只读提示

### 9.3 `P5-sim`

查询时必须能区分：

- 工单正常处理中
- 工单仍在待审或审定中
- 工单已审定但尚未全部交付
- 工单已交付可取
- 工单已被驳回
- 工单已被撤销

对于 `rejected / withdrawn` 工单，`P5` 不应继续把其视为有效待取供给。

## 10. 与当前实现的差距

当前实现仍存在以下差距：

- `ToolDemandSheet` 还没有稳定暴露 `review_status / delivery_status`
- 没有 `withdrawn`
- 没有 `rejected`
- 叶子项还没有正式 `review_status`
- 未命中分支仍可能在待审前自动进入制造
- 没有生命周期事件日志
- 没有撤销接口
- 没有驳回接口
- 没有叶子项审定接口
- 本地删除 JSON 只能算开发重置，不能算业务撤销

因此，后续关于工单生命周期的实现，应优先归入 `P4.2.1`，而不是继续散落在页面层做临时按钮。

## 11. 本节点结论

`P4.2.1` 当前必须作为独立节点成立，且其主设计文档就是本文。

后续任何涉及以下主题的改动，都必须先对照本文：

- 工单撤销
- 工单驳回
- 工单终态
- 工单已审定
- 工单已交付
- `P4` 闭环完成定义
- 生命周期事件日志
- 叶子项审定结论
- `P3 / P4 / P5` 动作边界
