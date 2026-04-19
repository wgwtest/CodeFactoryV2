# WBS-P4 工具仓库研制计划

## 1. 节点目标

构建工具、组件、执行器资产的登记、查询、匹配、复用和验证能力，支撑软件工厂后续构建闭环。

## 2. 当前边界

`P4` 负责：

- 工具/组件/执行器资产管理
- 工具需求单与匹配规则
- 统一数据快照
- 工具中台验证能力

不负责：

- 直接替代 `P3` 的软件设计对象生成
- 直接承担最终软件运行装配

## 3. 正式设计入口

- `DOC/CODEX_DOC/02_设计说明/00-软件工厂平台总体设计.md`
- `DOC/CODEX_DOC/02_设计说明/05-P4-工具仓库设计.md`
- `DOC/CODEX_DOC/02_设计说明/06-P4-核心业务循环设计.md`
- `DOC/CODEX_DOC/02_设计说明/07-P4-Runtime协调器与队列设计.md`
- `DOC/CODEX_DOC/02_设计说明/08-P4-Backend服务边界设计.md`
- `DOC/CODEX_DOC/02_设计说明/09-P4-数据与投影模型设计.md`

## 3.1 正式研发映射入口

- `DOC/CODEX_DOC/04_研发文档/01-P4-设计实现映射表.md`

## 4. 当前 superpowers 参考

- `docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md`
- `docs/superpowers/specs/2026-04-16-p4-tool-demand-sheet-lifecycle-design.md`
- `docs/superpowers/specs/2026-04-15-p4-tool-hub-unified-data-snapshot-design.md`
- `docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
- `docs/superpowers/specs/2026-04-17-p4-simulated-manufacture-executor-design.md`
- `docs/superpowers/specs/2026-04-17-p4-tool-registry-reset-and-p3-multi-scenario-generator-design.md`
- `docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md`
- `docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
- `docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md`
- `docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md`
- `docs/superpowers/specs/2026-04-18-p4-evolution-inspection-closed-loop-design.md`
- `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

## 5. 当前状态

- `2026-04-19` 已完成 `P4` 正式设计归档同步
- 已建立独立方案线
- 已存在节点设计与 issue 镜像
- `P4` 后端核心循环相关四份设计文档已归档到正式文档根
- 模拟研制执行器、工具仓测试治理、`P3-sim` 典型工单发生器、自演进巡检闭环等专题已归入正式设计体系
- 已建立 `P4` 设计到模块 / 类 / API / 测试的正式映射表
- 其余工作层文档仍需继续按正式文档根归一化

## 6. 后续约束

- `P4` 与 `P1 / P2 / P3` 通过版本化契约耦合
- 不直接依赖上游内部实现细节
- 工具匹配分析能力作为工具中台的一部分进行设计和表达
- `P4` 允许内部质量修订与自演进，但这不等于接受来自 `P5` 的直接修订回流
- `P5` 的装配不匹配必须先由 `P3` 仲裁；只有 `P3` 重新签发的新供给目标，才进入 `P4` 的外部输入闭环
