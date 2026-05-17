# 软件设计说明范本-SX-DataStore

## 文档说明

本文是面向 CodeFactory P2/P3 主链生成验证的软件设计说明范本，样例对象为 `SX-DataStore`。本文采用 P2 阶段软件设计说明中“先定设计口径、再定系统定位、边界、总体架构、前端、后端、对象、API、流程、约束、目录和验收”的结构组织方式，但内容完全基于 `SX-DataStore` 项目的真实设计和代码，不复用其他阶段系统的业务内容。

本文不是需求规格说明，不负责重新定义用户需求；本文负责把需求落实为软件结构、模块边界、对象模型、接口分组、运行流程和验证口径。

本文事实源主要来自：

- `/home/wgw/CodexProject/SX-DataStore/README.md`
- `/home/wgw/CodexProject/SX-DataStore/package.json`
- `/home/wgw/CodexProject/SX-DataStore/apps/api-server/src/`
- `/home/wgw/CodexProject/SX-DataStore/apps/portal-web/`
- `/home/wgw/CodexProject/SX-DataStore/apps/admin-web/`
- `/home/wgw/CodexProject/SX-DataStore/apps/ai-search-service/main.py`
- `/home/wgw/CodexProject/SX-DataStore/packages/types/src/`
- `/home/wgw/CodexProject/SX-DataStore/packages/page-schema/src/`
- `/home/wgw/CodexProject/SX-DataStore/DOC/CODEX_DOC/02_设计说明/`
- `/home/wgw/CodexProject/SX-DataStore/DOC/CODEX_DOC/03_规范与流程/`

## 1. 文档目的与设计口径

### 1.1 文档目的

本文用于说明 `SX-DataStore` 的软件设计方案，明确系统总体架构、前端设计、后端服务边界、共享对象模型、API 分组、关键运行流程、智能检索服务、工程目录和验收口径。

本文重点回答：

- 系统按什么架构层次组织。
- 三门户前端如何划分页面、组件和运行时装配职责。
- 后端如何按模块化单体承接资源、申请、审批、治理、工作台和页面配置。
- 共享类型和页面 schema 如何成为前后端契约。
- 资源申请、审批、交付、治理和页面解析如何形成可验证运行链路。

### 1.2 设计口径

本文采用以下设计口径：

1. 以受控资源体系为业务中心，不以首页或页面壳层为架构中心。
2. 系统层次和文档层次分离。系统按业务本体、流程状态、治理策略、能力检索、接口装配、页面交互六层组织；文档目录只是描述这些层次的载体。
3. 当前阶段采用 monorepo + 模块化单体后端 + 多前端应用，不强推微服务拆分。
4. 前端页面只消费 ViewModel、领域对象聚合和 PageResolve 结果，不直接发明业务事实。
5. 后端服务边界先于物理部署边界。`apps/api-server` 中的模块是正式服务边界的代码投影。
6. 资源对象、资源申请、审批任务、交付订单和资源实例必须保持边界清晰。
7. 页面配置能力服务本系统页面运行时装配，不扩展为通用低代码平台。

### 1.3 术语使用规则

| 术语 | 设计含义 |
| --- | --- |
| `Resource` | 资源对象本体，描述资源是什么、能做什么、由谁负责、当前状态如何。 |
| `ResourceInstance` | 用户或组织获得资源后的具体使用事实，描述本次获得、状态、有效期和入口。 |
| `ResourceRequest` | 一次资源申请、续期、变更或合作请求。 |
| `ApprovalTask` | 申请流程中某个责任节点需要处理的审批动作。 |
| `ProvisioningOrder` | 审批通过后用于交付或开通资源实例的过程对象。 |
| `PageConfig` | 页面配置版本、作用域和模块布局事实。 |
| `PageResolve` | 按上下文解析页面最终生效结构的运行时服务职责。 |
| `ViewModel` | 页面消费的聚合视图模型，连接页面和领域对象。 |

### 1.4 系统主路径

系统主路径如下：

```text
资源目录与详情 -> 资源篮与申请 -> 审批任务 -> 交付处理 -> 资源实例 -> 工作台与治理 -> 页面配置与运行时装配
```

辅助路径包括：

- 资源创建、版本维护、发布、上线和下线。
- 资源图谱、关系图谱、能力产物和检索索引。
- 公共页面、个人页面和资源级页面配置。
- 智能检索意图识别与候选资源过滤。

## 2. 系统定位

### 2.1 一句话定位

`SX-DataStore` 是一个面向仿真资源治理的三门户资源平台原型系统，以受控资源体系为核心，提供资源发现、申请审批、交付使用、生产维护、治理审计和页面运行时装配能力。

### 2.2 正面工作对象

系统正面工作对象包括：

- 资源对象：数据、模型、工具包、工具服务。
- 资源版本：资源发布版本、发布说明、发布状态。
- 能力产物：文档、样例输出、评估摘要、接口说明、对象树、运行环境说明。
- 资源关系：依赖、调用、派生、处理、同主题、同组织等资源关系。
- 资源申请：用户发起的试用、正式使用或合作请求。
- 审批任务：责任链中的批准、拒绝或退回补充动作。
- 资源实例：用户获得资源后形成的可使用对象。
- 治理动作：接管、冻结、恢复、强制下线、审计追踪。
- 页面配置：公共、个人、资源级页面配置及运行时解析结果。

### 2.3 用户角色

系统前端以三类角色上下文组织：

| 角色上下文 | 前端入口 | 主要工作对象 |
| --- | --- | --- |
| 消费者 | `apps/portal-web` | 资源目录、详情、申请、我的申请、我的资源实例、资源图谱。 |
| 生产者 | `apps/admin-web` 的 `/producer` 入口 | 我生产的资源、资源工作区、审批任务、交付任务。 |
| 管理者 | `apps/admin-web` 的 `/manager` 入口 | 治理驾驶舱、全资源列表、用户分析、全用户列表、异常治理。 |

审批职责不是第四类系统角色，而是依附于生产者、资源负责人、协作者或管理者的动态职责。

## 3. 业务目标与边界

### 3.1 首版负责

首版软件设计负责支持以下能力：

- 消费者门户：资源商店首页、资源列表、频道页、详情页、申请入口、我的资源中心、资源图谱。
- 生产者门户：生产者首页、资源列表、资源维护工作区、审批处理、交付处理。
- 管理者门户：治理驾驶舱、资源分布、资源列表、用户分析、用户注册表。
- 后端 API：资源目录、资源详情、资源图谱、申请创建与查询、审批查询与决策、工作台聚合、治理聚合、页面配置查询与解析。
- 共享契约：资源类型、交付方式、请求类型、审批状态、页面类型、页面作用域和页面模块 schema。
- 智能检索服务：基于自然语言提取资源类型、领域和交付方式筛选条件。
- 冒烟验证：关键页面和接口的运行态检查。

### 3.2 首版不负责

首版软件设计不负责：

- 生产级数据库选型、迁移脚本和真实持久化完整方案。
- 完整微服务拆分、服务注册、网关、熔断和分布式事务。
- 真实统一身份认证、组织目录同步和生产级权限引擎。
- 真实大模型 RAG、向量数据库和复杂检索排序。
- 真实资源下载、模型执行、工具服务调用和算力调度。
- 生产级运营计费、合同、订单和采购流程。

### 3.3 上下游边界

| 上下游 | 边界说明 |
| --- | --- |
| 上游需求 | 来自资源平台业务需求、三角色门户需求、资源治理需求和页面配置需求。 |
| 下游实现 | `apps/api-server`、`apps/portal-web`、`apps/admin-web`、`apps/ai-search-service`、`packages/types`、`packages/page-schema`。 |
| 下游测试 | 工作区单元测试、全局 QA 脚本、运行时冒烟验证、页面截图和接口响应证据。 |
| 外部系统 | 原型阶段不直接依赖真实统一身份、真实资源仓库或真实模型执行平台。 |

### 3.4 软件设计原则

#### 3.4.1 资源事实优先于页面表现

页面只表达当前用户、资源、流程和治理规则的投影。资源对象、申请、审批、实例和治理记录应由后端服务和共享契约维护。

#### 3.4.2 服务边界优先于物理拆分

当前后端以 NestJS 模块化单体实现，但应保持资源、请求、审批、治理、工作台、页面配置和契约输出的服务边界。

#### 3.4.3 聚合接口优先于前端拼装

工作台、治理页、资源工作区和资源详情属于多对象聚合页面。前端应优先消费后端聚合视图或 PageResolve 结果，不应跨多个接口自行重建正式事实。

#### 3.4.4 共享契约优先于重复类型

资源类型、流程状态、页面类型和页面 schema 应优先在 `packages/types` 与 `packages/page-schema` 中定义，前端和后端共同消费。

#### 3.4.5 完成条件

软件设计完成至少应满足：

- 前端路由、页面组件、后端模块、共享类型和运行脚本之间能对应。
- 资源申请到实例形成闭环。
- 页面配置到运行时解析形成闭环。
- 关键入口可通过冒烟验证检查。

## 4. 总体架构

### 4.1 总体分层

系统采用六层架构：

| 层次 | 职责 | 主要对象或模块 |
| --- | --- | --- |
| S1 业务本体层 | 定义资源和关系对象 | `Resource`、`ResourceVersion`、`ResourceRelationship`、`ResourceNeighborEdge`、`ResourceInstance`。 |
| S2 流程与状态层 | 定义申请、审批、交付和审计流转 | `ResourceRequest`、`ApprovalTask`、`ProvisioningOrder`、`ResourceAuditEvent`。 |
| S3 治理与策略层 | 定义权限、可见性、组织边界、生命周期和异常接管 | 审批路由、治理规则、审计策略、资源责任链。 |
| S4 能力与检索层 | 定义资源能力产物、图谱、索引和检索 | 能力产物、资源图谱、AI 检索筛选。 |
| S5 接口与装配层 | 定义 API、DTO、ViewModel、PageConfig、PageResolve | `apps/api-server`、`packages/types`、`packages/page-schema`。 |
| S6 页面与交互层 | 定义三门户页面、组件和编辑交互 | `apps/portal-web`、`apps/admin-web`。 |

### 4.2 产品能力模块

| 能力模块 | 前端承接 | 后端承接 | 共享契约 |
| --- | --- | --- | --- |
| 资源目录与详情 | `portal-web` 资源页、详情页 | `resources` 模块 | `ResourceSummary`、资源详情相关类型。 |
| 资源申请 | `portal-web` 申请入口与资源中心 | `requests` 模块 | `ResourceRequestSummary`、`RequestType`。 |
| 审批处理 | `admin-web` 审批页 | `approvals` 模块 | `ApprovalTaskSummary`、`ApprovalStatus`。 |
| 资源交付 | `admin-web` 交付页 | `workspace` 聚合与流程数据 | `ProvisioningOrderSummary`、`ProvisioningStatus`。 |
| 生产者工作区 | `admin-web` 资源工作区 | `workspace`、`resources` | 资源、版本、责任链和工作区 ViewModel。 |
| 治理驾驶舱 | `admin-web` 管理者页 | `governance` 模块 | 治理摘要和审计聚合对象。 |
| 页面配置运行时 | 门户运行时、工作台运行时 | `page-config` 模块 | `PageSchema`、`PageResolveResult`。 |
| 智能检索 | 检索入口和推荐解释 | `ai-search-service` | 查询意图、筛选条件、候选资源结果。 |

### 4.3 产品能力与后端层次关系

```text
页面与交互层
  -> 消费者门户 / 生产者门户 / 管理者门户
接口与运行时装配层
  -> API Controller / Service / DTO / ViewModel / PageResolve
能力与检索层
  -> 资源图谱 / 检索过滤 / AI 查询意图 / 能力产物
治理与策略层
  -> 角色职责 / 可见性 / 审批路由 / 异常接管 / 审计
流程与状态层
  -> ResourceRequest / ApprovalTask / ProvisioningOrder / ResourceAuditEvent
业务本体层
  -> Resource / ResourceVersion / ResourceInstance / ResourceRelationship
```

### 4.4 部署与运行单元

当前本地运行单元包括：

| 单元 | 技术栈 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| `apps/api-server` | NestJS 11 + TypeScript | `3001` | 后端 API 和聚合服务。 |
| `apps/portal-web` | Next.js 15 + React 19 | `3000` | 消费者门户。 |
| `apps/admin-web` | Next.js 15 + React 19 + Cesium | `3200` | 生产者和管理者门户。 |
| `apps/ai-search-service` | FastAPI + Pydantic | 可配置 | 智能检索意图解析服务。 |

## 5. 前端软件设计

### 5.1 模块定位、职责与核心概念

#### 5.1.1 技术栈

前端采用：

- Next.js `15.5.15`
- React `19.x`
- TypeScript
- CSS 全局样式和组件内组合样式
- Cesium，用于管理者门户地球分布视图
- `@sx/page-schema`，用于页面 schema 和运行时装配契约
- `@sx/types`，用于资源与工作流共享类型

#### 5.1.2 前端应用划分

| 应用 | 路径 | 职责 |
| --- | --- | --- |
| 消费者门户 | `apps/portal-web` | 资源商店、资源检索、频道、详情、申请、我的资源中心、资源图谱。 |
| 生产者/管理者门户 | `apps/admin-web` | 生产者首页、资源工作区、审批、交付、治理驾驶舱、用户分析。 |

`apps/admin-web` 承接生产者和管理者两个角色上下文，不意味着生产者和管理者业务对象混同。前端需要通过路由、壳层和 ViewModel 明确当前角色上下文。

#### 5.1.3 核心概念定义

| 概念 | 前端含义 |
| --- | --- |
| 角色壳层 | 根据消费者、生产者、管理者上下文展示不同导航、摘要和动作入口。 |
| 页面模块 | 可由 PageSchema 描述的页面单元，例如搜索区、分类树、资源卡片、治理面板。 |
| 锚定区域 | 不应被普通编辑操作移除或拖离的页面骨架区域。 |
| 编排区 | 可通过配置调整模块位置、尺寸、样式或显示内容的区域。 |
| 运行时状态 | 页面配置、后端 API、用户上下文和资源上下文共同决定的最终展示状态。 |

### 5.2 前端分层与装载生命周期

#### 5.2.1 分层结构

前端建议按以下层次理解：

```text
App Route
  -> Page Shell
    -> Runtime Loader / Server API Adapter
      -> ViewModel Presenter
        -> Domain Component
          -> Primitive UI Component
```

当前代码中的典型映射：

| 层次 | 消费者门户示例 | 生产者/管理者门户示例 |
| --- | --- | --- |
| App Route | `app/page.tsx`、`app/resources/page.tsx`、`app/resources/[resourceId]/page.tsx` | `app/producer/page.tsx`、`app/manager/page.tsx`、`app/workspace/resources/[resourceId]/page.tsx` |
| Page Shell | `storefront-chrome.tsx`、`portal-topbar.tsx` | `producer-shell.tsx`、`manager-shell.tsx`、`workspace-v2-shell.tsx` |
| Runtime Loader | `portal-runtime.ts`、`server-api.ts` | `workspace-api.ts`、`workspace-runtime.ts` |
| Presenter | `home-storefront.ts`、`search-presenter.ts` | `dashboard.ts`、`workspace-v2.ts` |
| Domain Component | `resource-card.tsx`、`consumer-resource-detail.tsx` | `producer-resource-workspace.tsx`、`manager-dashboard.tsx` |
| Primitive | `sx-primitives.tsx` | `sx-primitives.tsx` |

#### 5.2.2 装载生命周期

前端页面装载生命周期：

1. 路由接收页面上下文，例如首页、资源列表、资源详情、生产者资源页或治理页。
2. 读取环境变量中的 API 地址，例如 `SX_API_BASE_URL`。
3. 调用后端领域接口、聚合接口或页面解析接口。
4. 将响应转换为页面 ViewModel。
5. 根据角色上下文和状态渲染页面壳层、模块和动作入口。
6. 当 API 不可用或数据为空时，展示降级状态或运行时提示。

#### 5.2.3 状态机设计

前端至少应覆盖以下状态：

| 状态域 | 状态 | 处理方式 |
| --- | --- | --- |
| 页面装载 | `idle`、`loading`、`ready`、`empty`、`error` | 加载中、正常展示、空数据、错误提示。 |
| 数据来源 | `runtime`、`fallback`、`mock` | 明确展示真实运行时、降级或模拟数据来源。 |
| 用户上下文 | `consumer`、`producer`、`manager` | 控制导航、动作和页面语义。 |
| 申请状态 | `pending`、`approved`、`rejected`、`cancelled` | 映射为我的申请、审批页和资源详情动作状态。 |
| 实例状态 | `pendingProvisioning`、`active`、`expiringSoon`、`revoked` | 映射为我的资源实例状态。 |

### 5.3 页面执行设计

#### 5.3.1 路由结构

消费者门户主要路由：

| 页面 | 路由 |
| --- | --- |
| 资源商店首页 | `/` |
| 全部资源列表 | `/resources` |
| 频道页 | `/channels/[channel]` |
| 资源详情 | `/resources/[resourceId]` |
| 我的资源中心 | `/my/resources` |
| 资源图谱 | `/graphs` |
| 申请创建 API route | `/requests/create` |

生产者与管理者门户主要路由：

| 页面 | 路由 |
| --- | --- |
| 生产者首页 | `/producer` |
| 生产者资源列表 | `/producer/resources` |
| 生产者资源工作区 | `/producer/resources/[resourceId]` |
| 申请审批 | `/producer/approvals` |
| 交付处理 | `/producer/deliveries` |
| 管理者驾驶舱 | `/manager` |
| 全资源列表 | `/manager/resources` |
| 用户分析 | `/manager/users` |
| 全用户列表 | `/manager/users/registry` |
| 工作台兼容入口 | `/workspace`、`/workspace-v2` |
| 工作台资源页 | `/workspace/resources/[resourceId]` |

#### 5.3.2 页面区块与后端模块映射

| 页面区块 | 后端来源 | 说明 |
| --- | --- | --- |
| 搜索与分类 | `resources`、`page-config` | 资源检索和页面锚定配置。 |
| 资源卡片 | `resources` | 资源摘要和状态。 |
| 资源详情功能区 | `resources` | 类型化能力产物和资源关系。 |
| 我的申请 | `requests`、`workspace` | 申请状态和用户聚合。 |
| 我的资源实例 | `workspace` | 资源实例状态和入口。 |
| 审批面板 | `approvals` | 审批任务和决策动作。 |
| 交付面板 | `workspace` | 交付摘要和交付任务。 |
| 治理驾驶舱 | `governance` | 资源、用户、风险和异常聚合。 |
| 页面运行时 | `page-config` | 页面配置摘要和解析结果。 |

#### 5.3.3 页面命令提交规则

前端提交命令应遵守：

- 申请提交只调用请求接口，不直接创建资源实例。
- 审批决策只调用审批接口，不直接修改资源对象本体。
- 页面草稿保存和发布只调用页面配置接口，不直接改写业务对象。
- 治理动作应经治理接口或治理聚合链路承接，不能伪装成普通生产者动作。

### 5.4 模块接口设计

#### 5.4.1 外部接口

前端应用依赖以下环境变量：

| 变量 | 使用方 | 说明 |
| --- | --- | --- |
| `SX_API_BASE_URL` | `portal-web`、`admin-web` | 后端 API 地址。 |
| `SX_ADMIN_BASE_URL` | `portal-web` | 消费者门户跳转生产者/管理者门户时使用。 |
| `PORT` | `api-server` | 后端 API 监听端口。 |

#### 5.4.2 内部接口

前端内部接口包括：

- `server-api.ts`：消费者门户访问后端 API 的适配层。
- `portal-runtime.ts`：消费者门户运行时装配与降级处理。
- `workspace-api.ts`：生产者/管理者门户访问后端 API 的适配层。
- `workspace-runtime.ts`：工作台运行时状态和页面配置处理。
- `role-context.ts`：角色上下文判断与页面入口控制。
- `storefront-page-schema.ts`、`storefront-module-registry.ts`：消费者门户页面模块注册和 schema 渲染。

### 5.5 约束、错误处理与模块边界

- 前端不得把模拟数据当作正式业务事实源；模拟数据只能作为原型阶段降级或测试数据。
- 页面不得自行推导正式权限，只能基于后端返回的上下文和能力入口渲染。
- 资源详情页可展示当前用户的申请状态和实例摘要，但不能承担生产者发布或管理者治理的完整工作台职责。
- 消费者“我的资源”和生产者“我的资源”必须按角色上下文区分。
- 页面配置解析失败时，应显示运行时错误或回退到安全默认页面。

## 6. 后端软件设计

### 6.1 后端技术栈

后端主要技术栈：

- NestJS `11.x`
- TypeScript
- Node.js
- `tsx` 开发运行
- Node test runner + `tsx` 测试
- 当前以 `createMockDatabase()` 提供原型阶段内存数据源

智能检索服务技术栈：

- FastAPI
- Pydantic
- Python

### 6.2 后端分层原则

后端按三层理解：

| 层次 | 职责 | 当前代码落点 |
| --- | --- | --- |
| 领域服务层 | 维护资源、请求、审批、治理等业务事实 | `resources`、`requests`、`approvals`、`governance` |
| 聚合与运行时服务层 | 提供工作台、治理页、资源工作区和页面运行时聚合 | `workspace`、`page-config`、部分 `governance` |
| 基础支撑服务层 | 提供契约输出、健康检查、模拟数据和运行时清单 | `contracts`、`health`、`store` |

设计约束：

- Controller 只负责 HTTP 入参、路由和调用服务。
- Service 负责业务查询、状态变更、聚合和原型阶段模拟数据操作。
- Store 只作为当前阶段数据事实源，不应把业务规则散落在前端。
- 后续真实持久化应替换 Store，但不改变服务边界。

### 6.3 后端模块总览

当前 `apps/api-server/src/app.module.ts` 注册以下控制器与服务：

| 模块 | Controller | Service | 职责 |
| --- | --- | --- | --- |
| 健康检查 | `HealthController` | - | 返回 API 服务健康状态。 |
| 契约输出 | `ContractsController` | - | 输出资源类型、交付方式、页面类型和流程枚举。 |
| 资源 | `ResourcesController` | `ResourcesService` | 资源列表、详情、图谱。 |
| 请求 | `RequestsController` | `RequestsService` | 申请列表和申请创建。 |
| 审批 | `ApprovalsController` | `ApprovalsService` | 审批列表和审批决策。 |
| 页面配置 | `PageConfigController` | `PageConfigService` | 页面配置查询、解析、草稿保存、发布。 |
| 治理 | `GovernanceController` | `GovernanceService` | 治理摘要和异常治理聚合。 |
| 工作台 | `WorkspaceController` | `WorkspaceService` | 工作台、消费者资源中心、生产者门户聚合。 |

#### 6.3.1 模块权威状态矩阵

| 模块 | 权威对象 | 可写动作 | 不负责 |
| --- | --- | --- | --- |
| `resources` | `Resource`、资源关系、资源图谱 | 当前主要只读 | 审批决策、页面配置。 |
| `requests` | `ResourceRequest` | 创建申请 | 审批职责判断的完整生产级规则。 |
| `approvals` | `ApprovalTask` | 审批决策 | 资源对象维护、页面布局。 |
| `workspace` | 工作台 ViewModel、资源实例摘要、生产者聚合 | 当前主要聚合 | 直接替代领域事实。 |
| `governance` | 治理摘要、异常治理聚合 | 当前主要聚合 | 普通审批主入口替代。 |
| `page-config` | `PageConfig`、`PageResolveResult` | 保存草稿、发布配置 | 资源对象或流程对象定义。 |
| `contracts` | 枚举和契约摘要 | 只读 | 业务状态变更。 |
| `health` | 服务健康状态 | 只读 | 业务数据。 |

#### 6.3.2 模块间调用规则

- `requests` 创建申请后可生成或影响审批任务，但不应直接生成资源实例。
- `approvals` 决策可改变审批任务和申请状态，但不应承担资源交付完整逻辑。
- `workspace` 可聚合资源、申请、审批、实例和交付摘要，但不应成为所有领域事实的写入口。
- `page-config` 可解析页面结构，但不应定义资源或治理对象。
- `governance` 可聚合异常和审计信息，但不应吞并普通审批主流程。

### 6.4 资源服务模块

#### 6.4.1 模块定位、职责与核心概念

资源服务负责资源目录、资源详情和资源图谱。核心接口包括：

- `GET /resources`
- `GET /resources/:resourceId`
- `GET /resources/graph`

资源服务输入包括资源类型、领域和关键词筛选；输出包括资源摘要、资源详情和图谱快照。

#### 6.4.2 状态机设计

资源对象状态至少包括草稿、已发布、已上线、已下线、冻结或归档等语义。当前代码可能以简化状态表达，但设计应保留生命周期扩展空间。

#### 6.4.3 模块运行编排设计

资源列表流程：

```text
HTTP 查询参数 -> ResourcesController -> ResourcesService -> Store 查询与过滤 -> ResourceSummary[]
```

资源详情流程：

```text
resourceId + user -> ResourcesController -> ResourcesService -> 资源详情聚合 -> ResourceDetailView
```

资源图谱流程：

```text
ResourcesController -> ResourcesService -> ResourceGraphSnapshot
```

#### 6.4.4 模块接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/resources` | `GET` | 查询资源列表，支持 `kind`、`domain`、`q`。 |
| `/resources/graph` | `GET` | 获取资源图谱节点和关系。 |
| `/resources/:resourceId` | `GET` | 获取资源详情，可带 `user` 上下文。 |

### 6.5 请求服务模块

#### 6.5.1 模块定位、职责与核心概念

请求服务负责消费者资源申请的创建和查询。请求服务的权威对象是 `ResourceRequest`，其输入来自消费者申请表单或资源篮。

#### 6.5.2 状态机设计

申请状态使用 `pending`、`approved`、`rejected`、`cancelled` 等基础状态表达。退回补充在当前共享类型中尚未独立列为状态，可在后续设计中扩展为 `returned` 或以审批意见和补充要求表达。

#### 6.5.3 模块运行编排设计

```text
消费者提交申请 -> RequestsController.createRequest -> RequestsService.createRequest -> 写入申请事实 -> 生成或关联审批任务 -> 返回申请摘要
```

#### 6.5.4 模块接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/requests` | `GET` | 查询申请，可按 `requester` 过滤。 |
| `/requests` | `POST` | 创建申请，输入资源、申请类型、申请人、用途、目标实例名称等。 |

### 6.6 审批服务模块

#### 6.6.1 模块定位、职责与核心概念

审批服务负责审批任务查询和审批决策。审批服务权威对象是 `ApprovalTask`，不把审批者建模为第四类总体角色。

#### 6.6.2 状态机设计

审批状态包括：

- `pending`
- `approved`
- `rejected`
- `cancelled`

审批决策动作包括批准和拒绝。退回补充可作为后续扩展动作。

#### 6.6.3 模块运行编排设计

```text
审批人查看任务 -> ApprovalsController.listApprovals -> ApprovalsService.listApprovals
审批人提交决策 -> ApprovalsController.decideApproval -> ApprovalsService.decideApproval -> 更新审批与申请状态 -> 返回审批结果
```

#### 6.6.4 模块接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/approvals` | `GET` | 查询审批任务，支持 `approver`、`status`。 |
| `/approvals/:approvalId/decision` | `POST` | 提交审批决策，输入 `approved` 或 `rejected` 及意见。 |

### 6.7 工作台与治理聚合模块

#### 6.7.1 模块定位、职责与核心概念

工作台模块负责按用户和角色上下文输出聚合视图；治理模块负责输出管理者治理摘要和异常治理聚合。

工作台不是新的领域事实源，而是资源、申请、审批、实例和交付对象的视图聚合。

#### 6.7.2 模块运行编排设计

消费者资源中心：

```text
user -> /workspace/consumer -> WorkspaceService -> drafts + requests + instances + canRequest
```

生产者门户聚合：

```text
user -> /workspace/producer -> WorkspaceService -> produced resources + approvals + deliveries + summary
```

治理聚合：

```text
/ governance -> GovernanceService -> resource distribution + user analysis + risk summary + audit summary
```

#### 6.7.3 模块接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/workspace` | `GET` | 工作台兼容总览。 |
| `/workspace/consumer` | `GET` | 消费者资源中心聚合。 |
| `/workspace/producer` | `GET` | 生产者门户聚合。 |
| `/governance` | `GET` | 管理者治理摘要。 |

### 6.8 页面配置与运行时解析模块

#### 6.8.1 模块定位、职责与核心概念

页面配置模块负责 `PageConfig` 和 `PageResolve` 能力。它不定义业务对象，只负责页面配置版本、作用域、草稿、发布和运行时解析。

#### 6.8.2 状态机设计

页面配置状态：

- `draft`
- `published`

页面配置作用域：

- `public`
- `personal`
- `resource`

解析来源：

- `public`
- `personal`
- `resource`

#### 6.8.3 模块运行编排设计

```text
页面请求 -> PageConfigController.resolvePage -> PageConfigService.resolvePage -> 根据 pageId/user/resourceId 选择配置 -> PageResolveResult
```

草稿与发布流程：

```text
保存草稿 -> PageConfigService.saveDraft -> 生成 draft 版本
发布配置 -> PageConfigService.publishConfig -> 切换为 published 版本
```

#### 6.8.4 模块接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/page-configs/:pageId/resolve` | `GET` | 按页面、用户、资源解析生效页面。 |
| `/page-configs/:pageId` | `GET` | 获取页面配置摘要。 |
| `/page-configs/drafts` | `POST` | 保存页面配置草稿。 |
| `/page-configs/:configId/publish` | `POST` | 发布页面配置。 |

### 6.9 智能检索服务模块

#### 6.9.1 模块定位、职责与核心概念

智能检索服务位于 `apps/ai-search-service`，用于把自然语言查询解析为资源检索意图和过滤条件。当前实现采用规则化关键词识别，输出资源类型、领域和交付方式过滤条件。

#### 6.9.2 当前接口设计

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/health` | `GET` | 返回智能检索服务健康状态。 |
| `/query` | `POST` | 输入自然语言文本，输出标准化查询、意图、过滤条件和候选结果。 |

#### 6.9.3 设计边界

- 当前服务不直接决定资源权限。
- 当前服务不直接返回正式资源详情。
- 查询结果应交由资源目录或检索聚合链路进行权限过滤和结果补全。
- 后续可替换为向量检索、RAG 或大模型服务，但不改变“意图解析 -> 过滤条件 -> 资源检索”的边界。

## 7. 核心对象模型

### 7.1 持久化对象

当前原型阶段对象存放在内存模拟数据库中，生产化后应转为数据库表或文档集合。核心对象包括：

| 对象 | 说明 |
| --- | --- |
| `Resource` | 资源对象本体。 |
| `ResourceVersion` | 资源版本和发布状态。 |
| `ResourceRelationship` | 资源之间的关系。 |
| `ResourceNeighborEdge` | 图谱邻近关系。 |
| `ResourceInstanceDraft` | 资源申请前草稿。 |
| `ResourceRequest` | 资源申请事实。 |
| `ApprovalTask` | 审批任务事实。 |
| `ProvisioningOrder` | 交付开通过程事实。 |
| `ResourceInstance` | 用户获得后的资源实例。 |
| `PageConfig` | 页面配置版本。 |
| `PageSchema` | 页面结构和模块 schema。 |
| `ResourceAuditEvent` | 审计事件。 |

### 7.2 对象与模块映射

| 对象 | 权威模块 | 主要消费者 |
| --- | --- | --- |
| `Resource` | `resources` | 资源列表、详情、生产者资源工作区、治理页。 |
| `ResourceRequest` | `requests` | 我的申请、审批任务、治理页。 |
| `ApprovalTask` | `approvals` | 审批页、生产者首页、治理页。 |
| `ProvisioningOrder` | `workspace` 聚合或后续交付模块 | 交付处理页、我的资源实例。 |
| `ResourceInstance` | `workspace` 聚合或后续实例模块 | 消费者资源中心、治理页。 |
| `PageConfig` | `page-config` | 门户运行时、工作台运行时。 |
| `PageSchema` | `packages/page-schema` | 前端页面渲染器、后端 PageResolve。 |

### 7.3 资源类型模型

共享类型定义资源类型：

- `dataset`
- `model`
- `toolPackage`
- `toolService`

交付方式：

- `online`
- `download`
- `api`

资源详情应根据类型展示不同能力产物，例如数据字段、模型输入输出、工具包安装说明、工具服务接口定义。

### 7.4 流程状态模型

申请类型：

- `trial`
- `formal`
- `cooperation`

审批状态：

- `pending`
- `approved`
- `rejected`
- `cancelled`

交付状态：

- `pendingConfig`
- `provisioning`
- `failed`
- `delivered`

资源实例状态：

- `pendingProvisioning`
- `active`
- `expiringSoon`
- `revoked`

### 7.5 页面配置模型

`PageSchema` 由页面和模块组成。模块至少包含：

- `moduleId`
- `moduleType`
- `slot`
- 坐标与尺寸
- 配置对象
- 数据契约
- 编辑策略

模块插槽包括：

- `anchored`
- `canvas`
- `auxiliary`

页面类型包括：

- `home`
- `channel`
- `list`
- `detail`
- `personal`
- `ai-search`
- `workspace`
- `resourceWorkspace`
- `governance`
- `graph`

## 8. API 设计

### 8.1 API 分组总览

| 分组 | 基础路径 | 职责 |
| --- | --- | --- |
| 健康检查 | `/health` | 服务可用性检查。 |
| 契约输出 | `/contracts` | 枚举和基础契约输出。 |
| 资源 | `/resources` | 资源列表、详情和图谱。 |
| 请求 | `/requests` | 申请查询和创建。 |
| 审批 | `/approvals` | 审批查询和决策。 |
| 工作台 | `/workspace` | 用户工作台、消费者中心、生产者聚合。 |
| 治理 | `/governance` | 管理者治理摘要。 |
| 页面配置 | `/page-configs` | 页面配置摘要、草稿、发布和解析。 |
| 智能检索 | `/query` | 自然语言查询解析，位于 AI 服务。 |

### 8.2 API 设计约束

- API 返回值应以共享类型或稳定 ViewModel 为基础。
- 写接口必须保持对象边界，申请、审批、页面配置不能混用写入口。
- 聚合接口可以组合多个对象，但应明确每个字段来源。
- 页面解析接口只输出页面结构和配置来源，不输出任意业务规则。
- 原型阶段允许 `isMock` 字段标识模拟数据。

### 8.3 关键 API 示例

| 接口 | 示例 |
| --- | --- |
| 健康检查 | `GET /health` |
| 资源列表 | `GET /resources?kind=model&q=任务规划` |
| 资源详情 | `GET /resources/mission-planning-model?user=周工` |
| 资源图谱 | `GET /resources/graph` |
| 创建申请 | `POST /requests` |
| 查询审批 | `GET /approvals?approver=周工&status=pending` |
| 审批决策 | `POST /approvals/{approvalId}/decision` |
| 消费者中心 | `GET /workspace/consumer?user=周工` |
| 生产者聚合 | `GET /workspace/producer?user=周工` |
| 治理摘要 | `GET /governance` |
| 页面解析 | `GET /page-configs/{pageId}/resolve?user=周工&resourceId=mission-planning-model` |

## 9. 关键运行流程

### 9.1 消费者资源发现流程

```text
用户进入首页或列表页
  -> portal-web 读取 SX_API_BASE_URL
  -> 调用 /resources 或 /page-configs/{pageId}/resolve
  -> 后端返回资源摘要和页面结构
  -> 前端渲染搜索区、分类树、资源卡片和频道入口
```

### 9.2 资源详情与申请流程

```text
用户打开资源详情
  -> portal-web 调用 /resources/{resourceId}?user=...
  -> ResourcesService 返回资源详情、能力产物、关系和用户上下文
  -> 用户提交申请
  -> portal-web 调用 /requests
  -> RequestsService 创建 ResourceRequest 并关联审批任务
  -> 用户在 /my/resources?tab=requests 查看申请
```

### 9.3 审批与交付流程

```text
审批人进入 /producer/approvals
  -> admin-web 调用 /approvals
  -> ApprovalsService 返回待审批任务
  -> 审批人提交决策
  -> admin-web 调用 /approvals/{approvalId}/decision
  -> 后端更新审批和申请状态
  -> 交付处理页或工作台聚合展示后续交付状态
```

### 9.4 生产者资源维护流程

```text
生产者进入 /producer/resources
  -> admin-web 调用 /workspace/producer 或 /resources
  -> 展示生产者资源清单
  -> 进入 /producer/resources/{resourceId}
  -> 展示基础信息、版本、能力产物、审批、交付和历史上下文
```

### 9.5 管理者治理流程

```text
管理者进入 /manager
  -> admin-web 调用 /governance
  -> GovernanceService 返回治理摘要、资源分布、用户分析和异常事项
  -> 管理者进入资源列表或用户列表
  -> 对异常对象执行接管、冻结、恢复或审计追踪
```

### 9.6 页面配置运行时流程

```text
页面请求 pageId + user + resourceId
  -> 前端或运行时调用 /page-configs/{pageId}/resolve
  -> PageConfigService 选择 public/personal/resource 生效配置
  -> 返回 PageResolveResult
  -> 前端按 PageSchema 渲染模块
```

### 9.7 智能检索流程

```text
用户输入自然语言查询
  -> ai-search-service /query 解析 normalizedQuery、intent 和 filters
  -> 资源检索链路使用 filters 查询候选资源
  -> 前端展示候选资源和推荐理由
```

## 10. 智能检索与模型调用设计

### 10.1 基础定义

智能检索模块用于辅助资源发现，不替代资源目录和权限过滤。当前服务以规则方式识别资源类型、领域关键词和交付方式，后续可替换为大模型和向量检索。

### 10.2 执行模式

当前执行模式：

1. 接收用户查询文本。
2. 去除首尾空白，生成标准化查询。
3. 按关键词识别资源类型过滤条件。
4. 按领域词识别领域过滤条件。
5. 按交付词识别交付方式过滤条件。
6. 返回 `intent=resource_search`、`filters` 和候选结果占位。

### 10.3 边界约束

- 智能检索只产生候选意图和筛选条件。
- 正式资源结果仍应由资源服务和权限过滤链路输出。
- 检索服务不持有审批、交付、资源实例或页面配置权威事实。
- 大模型输出不得直接作为最终权限判断或最终资源事实。

### 10.4 后续扩展

后续可扩展：

- 资源文档解析。
- 资源能力摘要生成。
- 资源关系推荐。
- 语义检索和向量索引。
- 对话式检索澄清问题。
- 检索解释和推荐理由生成。

## 11. 设计约束与质量门

### 11.1 命名约束

- 资源对象统一使用 `Resource` 语义。
- 用户获得后的使用事实统一使用 `ResourceInstance` 语义。
- 申请统一使用 `ResourceRequest` 语义。
- 审批任务统一使用 `ApprovalTask` 语义。
- 页面配置统一使用 `PageConfig` 和 `PageResolve` 语义。
- 消费者和生产者的“我的资源”必须通过上下文或命名区分。

### 11.2 模块边界约束

- 资源服务不负责审批决策。
- 请求服务不负责页面配置。
- 审批服务不负责资源发布。
- 工作台服务只做聚合，不替代领域写入口。
- 页面配置服务不定义业务对象。
- 智能检索服务不绕过资源权限和可见性规则。

### 11.3 数据源约束

- 当前模拟数据库是原型数据源，不是生产持久化方案。
- 原型数据可用于页面和接口验证，但文档必须标识模拟边界。
- 后续接入真实数据库时，应优先保持 API 和共享类型稳定。

### 11.4 测试约束

- 工作区测试应覆盖前端 presenter、运行时适配、后端 service 和共享 schema。
- 冒烟验证应覆盖 API、消费者门户、生产者/管理者门户关键入口。
- 页面相关验收应结合运行态截图和接口响应。
- 类型检查应覆盖 `packages/types`、`packages/page-schema` 和各应用。

## 12. 目标目录结构

### 12.1 Monorepo 目录结构

```text
SX-DataStore/
  apps/
    api-server/
      src/
        approvals/
        contracts/
        governance/
        health/
        page-config/
        requests/
        resources/
        runtime/
        store/
        workspace/
    portal-web/
      app/
      components/
      lib/
    admin-web/
      app/
      components/
      lib/
      scripts/
    ai-search-service/
      main.py
      test_main.py
  packages/
    page-schema/
      src/
    types/
      src/
  scripts/
    qa/
  DOC/
    CODEX_DOC/
  output/
    qa/
```

### 12.2 后端目录结构

```text
apps/api-server/src/
  app.module.ts
  main.ts
  approvals/
    approvals.controller.ts
    approvals.service.ts
    approvals.service.test.ts
  contracts/
    contracts.controller.ts
  governance/
    governance.controller.ts
    governance.service.ts
    governance.service.test.ts
  health/
    health.controller.ts
  page-config/
    page-config.controller.ts
    page-config.service.ts
    page-config.service.test.ts
  requests/
    requests.controller.ts
    requests.service.ts
    requests.service.test.ts
  resources/
    resources.controller.ts
    resources.service.ts
    resources.service.test.ts
  runtime/
    runtime-api.test.ts
  store/
    mock-database.ts
    resource-runtime-manifests.ts
  workspace/
    workspace.controller.ts
    workspace.service.ts
    workspace.service.test.ts
```

### 12.3 前端目录结构

```text
apps/portal-web/
  app/
    channels/[channel]/page.tsx
    graphs/page.tsx
    my/resources/page.tsx
    requests/create/route.ts
    resources/[resourceId]/page.tsx
    resources/page.tsx
    page.tsx
  components/
  lib/

apps/admin-web/
  app/
    producer/page.tsx
    producer/resources/page.tsx
    producer/resources/[resourceId]/page.tsx
    producer/approvals/page.tsx
    producer/deliveries/page.tsx
    manager/page.tsx
    manager/resources/page.tsx
    manager/users/page.tsx
    manager/users/registry/page.tsx
    workspace/page.tsx
    workspace-v2/page.tsx
  components/
  lib/
```

### 12.4 共享包目录结构

```text
packages/types/src/
  index.ts
  resource.ts
  workflow.ts

packages/page-schema/src/
  index.ts
  options.ts
```

## 13. 验收口径

### 13.1 产品验收

产品验收应覆盖：

- 消费者可从首页、频道、列表和搜索进入资源详情。
- 消费者可提交资源申请并在我的申请中查看状态。
- 审批人可查看审批任务并提交审批决策。
- 生产者可进入资源维护工作区和交付处理页。
- 管理者可进入治理驾驶舱、资源列表和用户分析页。
- 页面配置可保存、发布和运行时解析。
- 资源图谱可展示资源节点和关系。

### 13.2 架构验收

架构验收应覆盖：

- 前端、后端、共享类型和页面 schema 目录职责清晰。
- 后端模块边界与设计说明一致。
- 资源对象、申请、审批、实例和页面配置对象不混淆。
- 页面通过 ViewModel 和接口装配获取业务事实。
- 智能检索与资源目录、权限过滤保持边界。

### 13.3 测试入口

推荐验证命令：

```bash
npm run test
npm run typecheck
npm run build
npm run smoke -- --skip-ai
```

按工作区验证：

```bash
npm test -w apps/api-server
npm test -w apps/portal-web
npm test -w apps/admin-web
npm run typecheck -w apps/api-server
npm run typecheck -w apps/portal-web
npm run typecheck -w apps/admin-web
```

本地访问入口：

| 入口 | 地址 |
| --- | --- |
| 消费者门户 | `http://127.0.0.1:3000/` |
| 生产者门户 | `http://127.0.0.1:3200/producer` |
| 管理者门户 | `http://127.0.0.1:3200/manager` |
| API 健康检查 | `http://127.0.0.1:3001/health` |

## 14. 面向平台展示与验证输出接口

为了支持后续 CodeFactory 生成验证，系统应提供以下可观察输出：

| 输出 | 用途 |
| --- | --- |
| 需求规格说明范本 | 对照 P2 生成结果是否覆盖角色、流程、功能、数据、非功能和验收。 |
| 软件设计说明范本 | 对照 P3 生成结果是否能从需求转为架构、模块、对象、API 和流程。 |
| 运行入口清单 | 验证页面入口是否与设计一致。 |
| API 清单 | 验证后端边界是否与设计一致。 |
| 共享类型清单 | 验证对象模型和状态是否稳定。 |
| 冒烟验证结果 | 验证关键页面与接口是否可运行。 |
| 截图与接口响应证据 | 支持人工验收和回归比对。 |

## 15. 设计结论

`SX-DataStore` 当前最合适的软件设计形态是：

- 以受控资源体系为业务中心。
- 以 monorepo 组织前端、后端、智能检索服务和共享契约。
- 以后端模块化单体承接服务边界，后续可按边界演进为物理拆分。
- 以消费者门户、生产者门户、管理者门户承接三类角色上下文。
- 以 `packages/types` 和 `packages/page-schema` 固化前后端契约。
- 以 PageConfig 和 PageResolve 承接页面运行时装配。
- 以资源申请、审批、交付、实例和治理链路作为核心可验证业务闭环。

该设计能够支撑当前原型系统运行验证，也为后续真实持久化、生产级权限、智能检索增强和资源交付集成保留清晰扩展边界。
