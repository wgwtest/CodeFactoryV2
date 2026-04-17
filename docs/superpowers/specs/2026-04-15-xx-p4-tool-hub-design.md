# P4 工具中台 `XX-P4` 设计

**日期：** 2026-04-15

**对应节点：**
- `P4` 工具仓库 / 工具中台
- `P4.1` 第一批最小闭环
- `P4.1.6` 统一数据层与同源快照验证
- `P4.2` 输入工序链闭环探索
- `P4.2.1` 工具需求单生命周期与协议对象

## 1. 设计目标

在不改动当前主线知识仓首页信息架构、知识图谱页、知识库管理页和主导航的前提下，为 `P4` 提供一个独立的“工具中台驾驶舱”页面与最小后端子域，形成以下首批闭环：

- 工具描述模型
- 工具仓库 CRUD
- 分类与标签体系
- 工具匹配规则 MVP
- 工具验证工作台

第一版产品名称采用：`XX-P4`

第一版页面定位采用：**独立驾驶舱页 + 页内工作区切换**

## 2. 产品定位与边界

### 2.1 产品定位

`XX-P4` 不是：

- 当前知识仓首页的一个新增区块
- 完整工具执行编排平台
- 多模块任务调度中心
- 全量资产治理平台
- 自动化自治系统

`XX-P4` 是：

- `P4` 工具中台的独立驾驶舱
- 工具资产、匹配链路、自演进巡检的统一验证入口
- 当前阶段用于“可见、可测、可解释”的最小承载面

### 2.2 并行开发边界

本设计严格遵守当前并行开发约束：

- 不修改当前主线知识图谱页
- 不修改当前知识库管理页
- 不修改主导航与首页信息架构
- 不依赖主工作区未发布内部 JSON、临时脚本输出、治理工作态细节或本地调试文件
- `P4` 只允许通过 `P1` 标准知识出口、只读 API 或冻结快照做联动

### 2.3 第一版非目标

第一版明确不做：

- 自动执行编排
- 多工具依赖图调度
- 权限与审批流细化
- 版本治理体系
- 自动合并或自动重构工具定义
- 基于历史学习的智能排序
- 复杂趋势分析与多时间尺度对比

## 3. 生命周期模型

`P4` 在第一版中承载 2 条典型生命周期与 1 个总览层：

### 3.1 总览层

总览层负责回答：

- 当前一共有多少工具
- 覆盖了哪些业务域与工具形态
- 当前是否存在明显重叠或空白
- 最近工具链任务与巡检任务运行情况如何

### 3.2 生命周期 A：外部输入工具链

该生命周期面向 `P3 -> P4` 或其他外部任务输入。

典型路径：

`P3/P3-sim 发出工具需求单 -> P4 受理并拆叶子项 -> 系统推荐 -> 人工逐项审定 -> 直接交付或进入研制 -> P5/P5-sim 查询与获取`

首版目标：

- 把 `工具需求单` 固定为跨 `P3 / P4 / P5` 的主干交付对象
- 让 `P4` 能逐项展示推荐、审定、供给与交付结果
- 让“命中现有工具”和“进入研制”都先经过人工批准
- 让 `P5` 只通过查询接口获取结果，而不是反向改写 `P4`

### 3.3 生命周期 B：自演进巡检链

该生命周期面向 `P4` 工具池自身的持续分析。

典型路径：

`定时/手动触发 -> 当前工具扫描 -> 重叠/缺口/规范性分析 -> 演进建议 -> 待确认项`

首版目标：

- 对现有工具定义做基本质量巡检
- 暴露疑似重复、标签不规范、描述缺失、覆盖空白
- 形成建议项与可人工确认的结果集

### 3.4 工单主干流定位

从 `P4.2` 起，`工具需求单` 不再只是“输入工具链里的一个临时对象”，而是 `P3 -> P4 -> P5` 的主干协议流。

因此必须同时满足：

- 在总设计层能看见它的角色与页面边界
- 在 `P4.2` 设计文档中能看见它的对象模型与闭环流程
- 在 `P4.2.1` 设计文档中能看见它的生命周期、撤销/驳回边界与完成判定
- 在本地 issue 树镜像中能追溯到对应设计文档和执行文档

## 4. 页面方案

### 4.1 路由与承载方式

第一版新增独立路由：

- `/xx-p4`

承载规则：

- 不并入当前顶部导航菜单
- 不替换当前首页
- 与现有知识仓页面同属于同一个前端应用，但使用独立页面壳层

### 4.2 页面结构

页面从上到下分为 4 层：

#### 4.2.1 顶部总览区

包含：

- 页面标题：`XX-P4`
- 页面副标题：`工具中台 / Tool Hub`
- 当前运行上下文：当前知识库、最近巡检时间、任务状态摘要

视觉原则：

- 参考现有站点的深色顶栏气质
- 但形成独立驾驶舱感，不复用当前主导航结构

#### 4.2.2 核心指标区

第一版至少展示：

- 工具总数
- 已验证工具数
- 活跃工具链数
- 重叠候选数
- 待演进建议数
- 最近 24h 任务成功率

#### 4.2.3 覆盖与健康区

这一层是 `XX-P4` 的标志性信息区。

必须包含：

- 一个类似 GitHub 年度贡献图风格的热力矩阵
- 一个风险与健康摘要区

第一版矩阵定义：

- 横轴：工具形态
- 纵轴：业务能力域
- 单元格值：当前激活工具在“业务域 × 工具形态”上的覆盖数量

第一版健康摘要至少解释：

- 空白覆盖区
- 高重叠区
- 低验证覆盖区
- 当前风险摘要

#### 4.2.4 工作区切换区

首版不跳转子页，而是在页内切换 4 个工作区：

- `总览`
- `输入工具链`
- `自演进巡检`
- `工具仓库`

### 4.3 工作区定义

#### 4.3.1 `总览`

目标：

- 展示 `P4` 当前整体状态

首版必须包括：

- 核心指标卡
- 覆盖热力矩阵
- 最近输入链任务列表
- 最近巡检任务列表
- 风险摘要

#### 4.3.2 `输入工具链`

目标：

- 承载“工单受理 -> 推荐 -> 审定 -> 交付”最小闭环

首版必须包括：

- 工序单受理区
- 工具需求列表
- 需求审批与处置面板
- 审定结论与供给结果展示
- 与 `/xx-p3-sim`、`/xx-p5-sim` 的页面边界说明

#### 4.3.3 `自演进巡检`

目标：

- 承载“扫描 -> 分析 -> 建议 -> 待确认项”闭环

首版只巡检以下 4 类问题：

- 工具描述缺失
- 标签/域模型不规范
- 工具能力疑似重叠
- 业务域覆盖不足

首版必须包括：

- 巡检任务列表
- 本轮发现摘要
- 建议项列表
- 人工确认状态

#### 4.3.4 `工具仓库`

目标：

- 承载首版工具资产的 CRUD 与验证状态管理

首版必须包括：

- 工具列表
- 创建/编辑/归档
- 业务域、形态、平台与标签维护
- 验证状态查看
- 样例记录关联

## 5. 工具描述模型

第一版核心对象为：`ToolDefinition`

建议字段如下：

```yaml
tool_id: tool_xxx
name: 审批规则校验器
slug: approval-rule-validator
status: active
summary: 针对审批路径和规则集生成结构化校验结论
problem_statement: 降低审批方案设计阶段的人工比对成本
primary_domain_id: workflow_approval
tool_form_id: skill
runtime_platform_ids:
  - agent_runtime
  - backend_service
tags:
  - domain:workflow_approval
  - form:skill
  - runtime:agent_runtime
  - lifecycle:solution_design
  - input:process_list
  - output:validation_report
  - risk:manual-review-required
lifecycle_stage_ids:
  - solution_design
  - verification_release
input_types:
  - process_list
  - rule_set
output_types:
  - validation_report
  - structured_json
supported_sources:
  - frozen_snapshot
  - manual_input
usage_notes: 优先用于审批链路设计前后的快速规则校验
keywords:
  - 审批
  - 规则
verification:
  status: verified
  last_verified_at: 2026-04-15T08:00:00Z
  last_verified_result: 通过基线样例验证
  sample_case_ids:
    - sample-approval-validation
```

### 5.1 核心字段语义

第一版把以下字段视为核心结构化字段，而不是只靠自由标签表达：

- `primary_domain_id`：工具主要服务的业务能力域
- `tool_form_id`：工具交付形态，例如 `skill / template / service_endpoint / static_library / dynamic_library`
- `runtime_platform_ids`：工具运行平台或宿主环境
- `lifecycle_stage_ids`：工具适用的项目/方案生命周期环节

### 5.2 状态定义

第一版工具状态固定为：

- `draft`
- `active`
- `archived`

### 5.3 验证状态定义

第一版验证状态固定为：

- `unverified`
- `verified`
- `warning`
- `failed`

## 6. 分类与标签体系

### 6.1 业务域与目录

第一版不再把“资料接入 / 知识处理 / 知识治理”之类的平台建设能力当成工具仓库主分类。

目录负责稳定导航和统计，不承担全部语义表达。第一版固定目录至少包括：

- 业务域：`case_management / workflow_approval / scheduling_dispatch / alert_response / reporting_audit / master_data / cross_domain_shared`
- 生命周期环节：`domain_discovery / solution_design / build_integration / verification_release / operation_optimization`
- 工具形态：`skill / template / service_endpoint / package_bundle / static_library / dynamic_library`
- 运行平台：`browser / backend_service / agent_runtime / container / local_cli / embedded_sdk`

### 6.2 标签

标签负责灵活表达匹配语义，第一版采用命名空间前缀：

- `domain:*`
- `lifecycle:*`
- `form:*`
- `runtime:*`
- `input:*`
- `output:*`
- `risk:*`

示例：

- `domain:workflow_approval`
- `lifecycle:solution_design`
- `form:skill`
- `runtime:agent_runtime`
- `input:process_list`
- `output:validation_report`
- `risk:manual-review-required`

## 7. 匹配规则 MVP

### 7.1 请求对象

第一版匹配请求对象：`ToolMatchRequest`

```yaml
scenario_text: 需要针对审批流设计场景快速判断哪些工具适合做规则校验
target_domain_ids:
  - workflow_approval
lifecycle_stage_ids:
  - solution_design
required_input_types:
  - process_list
expected_output_types:
  - validation_report
preferred_tool_forms:
  - skill
preferred_runtime_platforms:
  - agent_runtime
preferred_tags:
  - domain:workflow_approval
knowledge_context:
  archive_id: 20161116-nas
  entity_ids: []
  process_ids:
    - process-collaboration
  snapshot_version: v1
```

### 7.2 匹配维度

第一版匹配只做可解释规则打分：

- 业务域命中：25
- 生命周期环节命中：20
- 输入类型命中：15
- 输出类型命中：10
- 工具形态命中：10
- 运行平台命中：10
- 标签命中：5
- 场景关键词命中：5

总分上限 100。

### 7.3 返回对象

第一版返回对象：`ToolMatchRun`

每个候选项必须包含：

- `tool_id`
- `name`
- `match_score`
- `matched_dimensions`
- `reasons`
- `gaps`
- `verification_status`

## 8. 自演进巡检模型

第一版巡检结果对象：`EvolutionRun`

至少包含：

- `run_id`
- `status`
- `created_at`
- `summary`
- `findings`

第一版 `findings` 类型固定为：

- `missing_description`
- `taxonomy_issue`
- `overlap_risk`
- `coverage_gap`

## 9. 后端设计

### 9.1 模块边界

新增后端子域：`tool_hub`

建议目录：

- `apps/api/app/tool_hub/models.py`
- `apps/api/app/tool_hub/repository.py`
- `apps/api/app/tool_hub/service.py`
- `apps/api/app/tool_hub/fixtures.py`
- `apps/api/app/api/routes/tool_hub.py`

该子域对外只暴露标准 API，不允许前端直接依赖文件结构。

### 9.2 API 分组

第一版 API 固定为 4 组：

- `GET /api/tool-hub/overview`
- `GET /api/tool-hub/tools`
- `POST /api/tool-hub/tools`
- `GET /api/tool-hub/tools/{tool_id}`
- `PUT /api/tool-hub/tools/{tool_id}`
- `POST /api/tool-hub/match-runs`
- `GET /api/tool-hub/evolution-runs`
- `POST /api/tool-hub/evolution-runs`

`overview` 返回：

- 指标
- 覆盖矩阵
- 风险摘要
- 最近运行记录
- 分类与标签目录

### 9.3 存储方式

第一版采用文件型仓储，不入数据库。

建议目录：

- `.data/tool_hub/tools/`
- `.data/tool_hub/runs/match/`
- `.data/tool_hub/runs/evolution/`
- `.data/tool_hub/catalogs/`

目标：

- 保持验证优先
- 为未来迁移到 DB 保留 API 层稳定性

## 10. 前端设计

### 10.1 页面与组件结构

建议新增：

- `apps/web/src/pages/XXP4Page.tsx`
- `apps/web/src/components/p4/P4Hero.tsx`
- `apps/web/src/components/p4/P4MetricsPanel.tsx`
- `apps/web/src/components/p4/P4CoverageMatrix.tsx`
- `apps/web/src/components/p4/P4WorkspaceTabs.tsx`
- `apps/web/src/components/p4/P4InputChainWorkspace.tsx`
- `apps/web/src/components/p4/P4EvolutionWorkspace.tsx`
- `apps/web/src/components/p4/P4RegistryWorkspace.tsx`
- `apps/web/src/components/p4/P4RunList.tsx`
- `apps/web/src/components/p4/P4RiskSummary.tsx`
- `apps/web/src/lib/toolHub.ts`

### 10.2 视觉方向

`XX-P4` 的视觉方向必须：

- 参考当前站点的深色标题带与浅色工作区气质
- 保持独立驾驶舱辨识度
- 避免普通表单页或普通管理页的平铺结构
- 让热力矩阵成为页面记忆点

第一版应强调：

- 深色英雄区
- 强信息密度指标卡
- GitHub 风格热力矩阵
- 分段清晰的工作区

## 11. 与 `P1` 的联动边界

`P4` 只允许消费 `P1` 的标准知识上下文：

- `archive_id`
- `entity_ids`
- `process_ids`
- `snapshot_version`

首版联动原则：

- 不读取治理工作态
- 不读取内部中间文件
- 不依赖临时脚本输出
- 只通过标准知识出口或冻结快照消费上下文

## 12. 验收标准

第一版达到完成状态，至少满足：

1. 存在独立路由 `/xx-p4`，且不改变当前主导航与首页信息架构
2. 页面具备“总览 + 输入工具链 + 自演进巡检 + 工具仓库”4 个页内工作区
3. 工具仓库支持文件型 CRUD
4. 工具分类与标签可维护、可展示、可用于匹配
5. 输入工具链支持工单受理、逐项审定、供给结果输出与完成状态判定
6. 自演进巡检支持输出基础发现项与建议项
7. 驾驶舱页能展示覆盖热力矩阵与风险摘要
8. 前后端均有自动化测试覆盖最小主路径

## 13. 实施建议

第一版按以下顺序实施：

1. 定义后端模型与测试
2. 实现文件型仓储、匹配与巡检 API
3. 实现独立 `XX-P4` 页面与工作区切换
4. 接通工具仓库 CRUD、匹配运行、巡检运行
5. 完成前后端验证与回归

## 14. 后续子节点建议

在 `P4.1` 第一批最小闭环形成基础页面和 API 后，建议继续拆出以下收口节点：

- `P4.1.6` 统一数据层与同源快照验证

该节点目标不是继续扩页面，而是把当前 `tools / overview / evolution-runs` 的分散消费方式收敛为统一状态快照投影，确保：

- 总览、输入工具链、自演进巡检、工具仓库消费同一份 `P4` 事实源
- 指标、风险摘要、覆盖矩阵、运行监视等状态明确为派生层，不再由页面各自隐式定义
- 页面能够显式验证当前多路数据是否属于同一个 `snapshot_id`
