# WBS-P2 需求分析系统研制计划

## 1. 节点目标

构建一个面向非技术行业专家可用的交互式需求建模系统，输出结构化 `RequirementSpec`。

## 2. 当前边界

`P2` 负责：

- 提供表单式建模器与选配式建模器
- 从对象出发组织需求，而不是依赖组件
- 消费 `P1` 的业务元素，也允许现场新增临时元素
- 产出结构化需求规格，并可投影为说明文本

不负责：

- 直接做组件命中与复用判断
- 直接产出软件设计说明
- 直接承担工具仓库管理

## 3. 正式设计入口

- `DOC/CODEX_DOC/02_设计说明/00-软件工厂平台总体设计.md`

## 4. 当前 superpowers 参考

- `docs/superpowers/specs/2026-04-13-application-requirement-modeler-design.md`
- `docs/superpowers/specs/2026-04-17-xx-p2-sim-design.md`
- `docs/superpowers/plans/2026-04-17-xx-p2-sim.md`

## 5. 当前状态

- 设计方向已明确
- 已形成模拟输入台方案
- 仍需补齐正式 issue tree mirror 与更完整的节点级执行契约

## 6. 后续约束

- `P2` 的权威输出必须是结构化需求对象
- 说明书只作为投影，不替代结构化对象
- `P2` 与组件/工具资产保持解耦，由 `P3 / P4` 在后续阶段消费
