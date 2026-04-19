# superpowers 文档映射表

本文件用于把当前 `docs/superpowers/` 中已经存在的主要文档资产，映射到 `DOC/CODEX_DOC/` 正式文档体系中。

## 1. 映射原则

- `specs/`：优先映射到 `DOC/CODEX_DOC/02_设计说明/`
- `plans/`：优先映射到 `DOC/CODEX_DOC/03_研制计划/` 或过程文档
- `issues/`：视为远端执行契约镜像，正式节点说明仍以 `03_研制计划/` 为准
- `.superpowers/brainstorm/`：视为临时过程产物，不直接映射为正式权威文档

补充硬规则：

- 本表是“来源映射台账”，不是用户阅读入口
- 用户应只阅读 `DOC/CODEX_DOC/` 下按逻辑整理的终稿文档
- 某份 `superpowers` 文档即使已在本表登记来源，如果其核心正文尚未写入 `DOC/CODEX_DOC/`，仍视为“未完成正式迁移”
- 尤其是 `specs/` 中的核心设计细节，不能长期只挂到 `03_研制计划/` 入口文档而不进入 `02_设计说明/` 正文

## 1.1 迁移完成判定

只有同时满足以下条件，才算一份 `superpowers` 文档完成正式迁移：

- 已在本表登记来源关系
- 已在 `DOC/CODEX_DOC/` 中找到对应的逻辑归档位置
- 核心细节正文已经进入正式文档，而不是只保留引用或入口

这里的“核心细节”至少包括：

- 节点拆解与模块边界
- 数据模型、对象模型、状态模型
- 输入输出契约与接口规则
- 关键策略、质量门、迁移口径
- 页面级关键交互与验证要求

## 2. 总体类文档

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md` | `DOC/CODEX_DOC/02_设计说明/00-软件工厂平台总体设计.md` | 总体蓝图的正式归一入口 |
| `docs/superpowers/specs/2026-04-17-portal-home-design.md` | `DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | `P6.1` 门户蓝图专项设计的工作层来源 |
| `docs/superpowers/specs/2026-04-19-p6-stage-reframing-design.md` | `DOC/CODEX_DOC/02_设计说明/10-P6-门户与平台入口设计.md`<br/>`DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | `P6` 阶段定位重排与双层结构收敛来源 |

## 3. P1 业务知识库

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-11-archive-document-drilldown-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | 文档钻取能力已写入 `P1` 正式设计正文 |
| `docs/superpowers/specs/2026-04-11-archive-knowledge-review-editing-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | `P1` 治理工作台正式归档 |
| `docs/superpowers/specs/2026-04-12-openai-compatible-llm-adapter-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | `P1` 抽取基础设施已纳入正式设计 |
| `docs/superpowers/specs/2026-04-14-formal-archive-extraction-hard-gate-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | 正式抽取硬门禁已归入 `P1` 正式设计 |
| `docs/superpowers/specs/2026-04-14-long-document-formal-extraction-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | 长文档正式抽取策略已归入 `P1` 正式设计 |
| `docs/superpowers/specs/2026-04-15-document-incremental-knowledge-rebuild-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | 文档级增量重建已归入 `P1` 正式设计 |
| `docs/superpowers/specs/2026-04-16-bilingual-knowledge-projection-design.md` | `DOC/CODEX_DOC/02_设计说明/02-P1-业务知识库设计.md` | 双语投影增强已归入 `P1` 正式设计 |

## 4. P2 需求分析系统

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-13-application-requirement-modeler-design.md` | `DOC/CODEX_DOC/02_设计说明/03-P2-需求分析系统设计.md` | `P2` 需求建模主入口已正式归档 |
| `docs/superpowers/specs/2026-04-17-xx-p2-sim-design.md` | `DOC/CODEX_DOC/02_设计说明/03-P2-需求分析系统设计.md` | `P2-Sim` 已并入 `P2` 正式设计 |
| `docs/superpowers/plans/2026-04-17-xx-p2-sim.md` | `DOC/CODEX_DOC/03_研制计划/02-WBS-P2-需求分析系统-研制计划.md` | 当前实施计划参考 |

## 5. P3 软件设计系统

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-17-xx-p3-software-design-system-design.md` | `DOC/CODEX_DOC/02_设计说明/04-P3-软件设计系统设计.md` | `P3` 正式设计归档入口 |
| `docs/superpowers/plans/2026-04-17-xx-p3-software-design-system.md` | `DOC/CODEX_DOC/03_研制计划/03-WBS-P3-软件设计系统-研制计划.md` | `P3` 实施计划参考 |
| `docs/superpowers/issues/2026-04-17-p3-software-design-system-issue-tree-mirror.md` | `DOC/CODEX_DOC/03_研制计划/03-WBS-P3-软件设计系统-研制计划.md` | `P3` issue tree mirror 的正式映射 |

## 6. P4 工具仓库

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md` | `P4` 总体设计已正式归档 |
| `docs/superpowers/specs/2026-04-16-p4-tool-demand-sheet-lifecycle-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md` | 工具需求单生命周期已归入 `P4` 总体设计与输入链闭环正文 |
| `docs/superpowers/specs/2026-04-15-p4-tool-hub-unified-data-snapshot-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/09-P4-数据与投影模型设计.md` | 统一数据快照已归入总体设计与投影模型正文 |
| `docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md` | 输入链闭环已归入 `P4` 正式设计正文 |
| `docs/superpowers/specs/2026-04-17-p4-simulated-manufacture-executor-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/07-P4-Runtime协调器与队列设计.md` | 模拟研制执行器已归入 `P4` 总体设计与运行时设计 |
| `docs/superpowers/specs/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md` | 工具仓测试治理与 `P3-sim` 联调输入台已归入 `P4` 正式设计 |
| `docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md` | `DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md` | `P4` 后端核心业务循环正式归档 |
| `docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md` | `DOC/CODEX_DOC/02_设计说明/07-P4-Runtime协调器与队列设计.md` | `P4` 运行时协调器、Worker、Queue 正式归档 |
| `docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md` | `DOC/CODEX_DOC/02_设计说明/08-P4-Backend服务边界设计.md` | `P4 backend service` 分域与边界正式归档 |
| `docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md` | `DOC/CODEX_DOC/02_设计说明/09-P4-数据与投影模型设计.md` | `P4` 数据模型与投影模型正式归档 |
| `docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md` | `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/08-P4-Backend服务边界设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/09-P4-数据与投影模型设计.md` | 自演进巡检闭环已拆分归入 `P4` 总体、循环、边界和投影设计 |
| `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md` | `DOC/CODEX_DOC/03_研制计划/04-WBS-P4-工具仓库-研制计划.md` | `P4` issue tree mirror 的正式映射 |

## 7. P6 平台门户、观察与前端展示实验层

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-17-portal-home-design.md` | `DOC/CODEX_DOC/02_设计说明/10-P6-门户与平台入口设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/11-P6.1-首屏观察门户设计.md` | `P6.1` 首屏观察门户与蓝图画布专项设计来源 |
| `docs/superpowers/specs/2026-04-19-p6-stage-reframing-design.md` | `DOC/CODEX_DOC/02_设计说明/10-P6-门户与平台入口设计.md`<br/>`DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | `P6` 已从“登录 / 权限优先”重排为“首屏观察 + 只读集成 + 语言统一 + 展示实验”的双层结构 |
| `docs/superpowers/specs/2026-04-19-p6-detailed-subsystem-design.md` | `DOC/CODEX_DOC/02_设计说明/11-P6.1-首屏观察门户设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/12-P6.2-跨阶段只读集成与状态投影设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/13-P6.3-设计语言与前端展示基线设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/14-P6.4-前端展示工具化实验场设计.md`<br/>`DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | `P6.1 ~ P6.4` 正式专项设计的过程稿来源 |
| `docs/superpowers/plans/2026-04-17-portal-home.md` | `DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | 门户实施计划 |
| `docs/superpowers/issues/2026-04-17-p6-platform-entry-issue-tree-mirror.md` | `DOC/CODEX_DOC/03_研制计划/06-WBS-P6-门户与平台入口-研制计划.md` | 门户 issue tree mirror |

## 8. P5 软件构建系统

| superpowers 文档 | 正式文档 | 说明 |
| --- | --- | --- |
| `docs/superpowers/specs/2026-04-19-xx-p5-software-construction-system-design.md` | `DOC/CODEX_DOC/04_研发文档/03-P5详细设计前置分析-临时.md`<br/>`DOC/CODEX_DOC/03_研制计划/05-WBS-P5-软件构建系统-研制计划.md`<br/>`DOC/CODEX_DOC/02_设计说明/04-P3-软件设计系统设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`<br/>`DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md` | `P5` 过程稿已启动；当前其回流边界、唯一仲裁和 `P4` 非直接修订语义，已先回写到前置分析、阶段计划和 `P3/P4` 正式设计，后续再迁入 `P5` 正式详细设计 |

## 9. 后续维护规则

- 新增 `superpowers` 文档时，若其成为正式基线，必须同步补充本映射表
- 新增正式文档时，应反向补充其来源的 `superpowers` 参考文档
- 不做“文档删除式重整”，只做“角色清晰化 + 正式入口归一化”
