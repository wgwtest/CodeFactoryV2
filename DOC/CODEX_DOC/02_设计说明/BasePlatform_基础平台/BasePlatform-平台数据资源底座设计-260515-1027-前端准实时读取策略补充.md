# Base Platform 平台数据资源底座设计补充：前端准实时读取策略

> 本文件是 `BasePlatform-平台数据资源底座设计.md` 的待确认补充稿。
>
> 本补充稿仅用于说明前端准实时读取策略，待确认后再合并回主设计文档。当前不替代主设计文档。

**日期：** 2026-05-15  
**状态：** 待用户确认  
**适用范围：** `P3` 输入包列表、基础平台监控日志台（Base Platform Monitor）、后续 `P4/P5` 平台资源输入列表  
**关联实现：**

- `apps/web/src/lib/usePollingResource.ts`
- `apps/web/src/pages/BasePlatformMonitorPage.tsx`
- `apps/web/src/pages/P3DesignLabPage.tsx`

## 1. 补充背景

`P2 -> Base Platform -> P3` 首版链路已经具备后端同步一致性：

```text
P2 发布需求规格包
  -> Base Platform 写入平台资源登记项（ArtifactEnvelope）
  -> P3 查询平台资源并映射为 P3 设计输入包（P3DesignInputPackage）
```

但是前端页面如果只在首次打开时请求一次数据，会出现以下体验问题：

```text
用户先打开 P3 页面或 Base Platform Monitor
  -> 用户在另一个页面完成 P2 发布
  -> 后端平台表已经有新资源
  -> 已打开页面仍显示旧数据
```

该问题不是平台存储失败，也不是 `P3` 后端查询失败，而是已打开前端页面缺少准实时刷新机制。

因此，需要把 `P3` 与基础平台监控日志台统一纳入同一套前端数据新鲜度策略。

## 2. 设计结论

首版采用统一的前端准实时读取策略：

```text
页面首次打开：立即请求
页面保持可见：每 1 秒轮询一次
页面从后台切回前台：立即请求
用户手动刷新：立即请求
请求未完成时：不发起并发重复请求
请求失败时：保留上一版可用数据并显示错误
```

该策略适用于：

| 页面或模块 | 请求接口 | 刷新周期 | 说明 |
| --- | --- | --- | --- |
| 基础平台监控日志台（Base Platform Monitor） | `GET /api/platform-exchange/monitor` | 1 秒 | 展示 `P1 ~ P5` 与 `Base Platform` 总账 |
| P3 设计输入包列表（P3 Input Packages） | `GET /api/software-design-v2/input-packages` | 1 秒 | 让 `P2` 发布后的需求规格包尽快进入 `P3` 可选输入 |
| 后续 `P4/P5` 输入列表 | 待定 | 1 秒 | 延续相同策略 |

从用户视角，`P2` 发布后，`P3` 和基础平台日志台都应在约 1 秒内看到新结果。

## 3. 为什么不区分监控台和 P3

虽然从系统职责上看：

- 基础平台监控日志台是只读观察页面；
- `P3` 输入包列表是业务入口；

但从用户验收视角看，两者的实时性要求一致：

```text
P2 已发布
  -> P3 应能尽快看到
  -> Base Platform Monitor 也应能尽快看到
```

因此首版不再为两者设置不同刷新策略。二者统一使用同一套前端准实时读取机制。

## 4. 技术实现口径

### 4.1 通用 Hook

前端新增通用读取机制：

```text
usePollingResource
```

中文口径为：

```text
前端轮询资源读取 Hook
```

职责包括：

1. 组件挂载后立即加载数据；
2. 页面可见时按固定周期轮询；
3. 浏览器标签页从后台切回前台时立即刷新；
4. 浏览器窗口重新获得焦点时立即刷新；
5. 避免同一资源重复并发请求；
6. 组件卸载时清理定时器和事件监听；
7. 请求失败时调用错误处理，但不强制清空旧数据。

### 4.2 Base Platform Monitor 接入

基础平台监控日志台通过以下方式读取：

```text
usePollingResource(
  intervalMs = 1000,
  load = GET /api/platform-exchange/monitor
)
```

页面展示数据来自：

- `platform_exchange_artifacts`
- `platform_exchange_consumptions`

首版仍不新增审计事件表。

### 4.3 P3 输入包列表接入

`P3DesignLabPage` 通过以下方式读取：

```text
usePollingResource(
  intervalMs = 1000,
  load = GET /api/software-design-v2/input-packages
)
```

刷新后必须保留用户当前选择：

```text
如果当前 selectedPackageId 仍存在
  -> 保留当前选择
否则
  -> 选择最新列表中的第一项
```

这样可以避免页面自动刷新时打断用户正在查看或操作的输入包。

## 5. 数据一致性边界

该策略解决的是前端可见性问题，不改变后端权威事实。

后端权威链路仍然是：

```text
P2 发布接口返回 200
  -> Base Platform 已写入 published 状态 artifact
  -> P3 input-packages API 从 Base Platform 查询该 artifact
```

前端 1 秒轮询只负责让已经打开的页面及时重新读取后端状态。

如果出现以下问题，不能归因为前端轮询：

1. `P2` 发布接口失败；
2. `P2` 发布接口返回 200 但平台表没有写入资源；
3. `P3` 后端 `input-packages` 查询条件错误；
4. 平台资源生命周期状态不是 `published`；
5. 数据库事务未提交或服务连接到不同数据库。

这些属于后端链路一致性问题，应通过后端合同测试和接口检查定位。

## 6. 与事件推送的关系

1 秒轮询是首版准实时方案，不是最终事件驱动架构。

后续如果需要更强实时性，可以演进为：

```text
Server-Sent Events（服务端事件推送，SSE）
WebSocket（双向实时通信）
平台事件总线
```

但即使后续切换为推送机制，也应优先复用当前抽象边界：

```text
页面不直接绑定传输机制
  -> 页面调用统一资源读取/订阅抽象
  -> 底层可从 polling 替换为 SSE/WebSocket
```

也就是说，`usePollingResource` 当前是轮询实现；后续可扩展为统一的 `useRealtimeResource` 或在内部增加推送能力，而不是让每个页面各自实现实时通信。

## 7. 验收要求

### 7.1 Base Platform Monitor

验收点：

1. 打开监控日志台时立即加载当前平台资源；
2. 页面保持打开时，`P2` 发布后约 1 秒内出现 `P2` 发布日志；
3. `P3` 创建会话并消费平台资源后，约 1 秒内出现 `P3` 消费日志；
4. 轮询不产生发布、撤销、保存、删除、消费等写操作；
5. 请求失败时不清空已有日志。

### 7.2 P3 输入包列表

验收点：

1. 打开 `P3DesignLabPage` 时立即加载输入包列表；
2. 页面保持打开时，`P2` 发布后约 1 秒内新增输入包；
3. 用户已经选中的输入包仍存在时，自动刷新不能改变当前选择；
4. 用户切回浏览器标签页时立即刷新；
5. “刷新输入包”按钮可以手动触发同一读取逻辑。

## 8. 测试要求

对应前端测试至少覆盖：

```text
BasePlatformMonitorPage.test.tsx
  -> 页面打开后每 1 秒重新请求 monitor snapshot
  -> 新发布 artifact 能显示到 P2 框

P3DesignLabPage.test.tsx
  -> 页面打开后每 1 秒重新请求 input packages
  -> 新输入包能显示到 P3 输入列表
```

相关回归命令：

```bash
corepack pnpm --dir apps/web exec vitest run \
  src/test/BasePlatformMonitorPage.test.tsx \
  src/test/P3DesignLabPage.test.tsx

corepack pnpm --dir apps/web exec tsc --noEmit

uv run pytest apps/api/tests/test_platform_exchange_p2_p3_api.py -q
```

## 9. 待合并到主文档的位置建议

用户确认后，建议把本补充内容合并到主设计文档以下位置：

1. `5. 前端软件设计`
   - 增补“前端准实时读取策略”；
   - 明确 `BasePlatformMonitorPage` 与 `P3DesignLabPage` 共用 1 秒刷新机制。

2. `6. 后端工作机制`
   - 补充说明前端轮询不改变后端同步写入和权威存储口径。

3. `16. 验收标准`
   - 增补 `P2` 发布后 `P3` 和 `Base Platform Monitor` 在约 1 秒内可见的验收项。

本补充稿确认前，不修改主设计文档。
