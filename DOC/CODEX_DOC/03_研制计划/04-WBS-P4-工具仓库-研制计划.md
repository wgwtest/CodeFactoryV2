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
- `DOC/CODEX_DOC/02_设计说明/02-P4-核心业务循环设计.md`
- `DOC/CODEX_DOC/02_设计说明/03-P4-Runtime协调器与队列设计.md`
- `DOC/CODEX_DOC/02_设计说明/04-P4-Backend服务边界设计.md`
- `DOC/CODEX_DOC/02_设计说明/05-P4-数据与投影模型设计.md`

## 4. 当前 superpowers 参考

- `docs/superpowers/specs/2026-04-15-xx-p4-tool-hub-design.md`
- `docs/superpowers/specs/2026-04-16-p4-tool-demand-sheet-lifecycle-design.md`
- `docs/superpowers/specs/2026-04-15-p4-tool-hub-unified-data-snapshot-design.md`
- `docs/superpowers/specs/2026-04-16-p4-input-chain-closed-loop-design.md`
- `docs/superpowers/specs/2026-04-18-p4-core-business-cycle-design.md`
- `docs/superpowers/specs/2026-04-18-p4-runtime-coordinator-worker-queue-design.md`
- `docs/superpowers/specs/2026-04-18-p4-backend-service-boundary-design.md`
- `docs/superpowers/specs/2026-04-18-p4-data-and-projection-model-design.md`
- `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`

## 5. 当前状态

- 已建立独立方案线
- 已存在节点设计与 issue 镜像
- `P4` 后端核心循环相关四份设计文档已归档到正式文档根
- 其余工作层文档仍需继续按正式文档根归一化

## 6. 后续约束

- `P4` 与 `P1 / P2 / P3` 通过版本化契约耦合
- 不直接依赖上游内部实现细节
- 工具匹配分析能力作为工具中台的一部分进行设计和表达
