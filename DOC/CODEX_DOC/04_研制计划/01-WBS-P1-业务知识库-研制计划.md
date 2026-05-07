# WBS-P1 业务知识库研制计划

## 1. 节点目标

完成从业务资料到已发布知识仓的最小闭环，并为后续 `P2` 输出可消费的业务元素与知识查询能力。

## 2. 当前边界

`P1` 负责：

- 文档接入
- 结构化解析
- 正式知识抽取
- 治理审核与发布
- 知识检索与图谱展示

不负责：

- 需求交互式建模
- 软件设计对象生成
- 工具匹配与软件装配

## 3. 正式设计入口

- `DOC/CODEX_DOC/02_设计说明/00_总纲/00-软件工厂平台总体设计.md`
- `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`

## 4. 当前 superpowers 参考

- `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- `docs/superpowers/specs/2026-04-11-archive-document-drilldown-design.md`
- `docs/superpowers/specs/2026-04-11-archive-knowledge-review-editing-design.md`
- `docs/superpowers/specs/2026-04-12-openai-compatible-llm-adapter-design.md`
- `docs/superpowers/specs/2026-04-14-formal-archive-extraction-hard-gate-design.md`
- `docs/superpowers/specs/2026-04-14-long-document-formal-extraction-design.md`
- `docs/superpowers/specs/2026-04-15-document-incremental-knowledge-rebuild-design.md`
- `docs/superpowers/specs/2026-04-16-bilingual-knowledge-projection-design.md`

## 5. 当前状态

- `2026-04-19` 已完成 `P1` 正式设计归档同步
- 文档钻取、治理工作台、正式抽取硬门禁、长文档抽取、增量重建、双语投影已并入 `DOC/CODEX_DOC/02_设计说明/P1_业务知识库/P1-业务知识库设计.md`
- `2026-05-05` 补充知识生成阶段解耦合同、规则输入输出合同、规则变更后的动态影响面重算与知识调整设计
- `2026-05-05` 补充可复用策略资产库设计，要求抽取启动时可选择既有策略包、复制改造或创建新策略包
- 已有运行闭环
- 持续优化中
- 重点问题仍集中在正式抽取质量、长文档处理、关系完整性、策略资产复用、规则可解释性、规则变更后的增量重算和知识展示解释性

## 6. 后续约束

- 正式知识抽取继续执行 `Docling + 结构化大模型` 硬约束
- `P1` 的正式成果必须保持为后续 `P2` 的稳定输入，不直接暴露内部脚本和中间态文件
- 知识生成阶段必须按阶段处理器合同解耦，阶段之间只通过声明的输入/输出产物传递信息
- 每条规则必须具备可追溯的输入输出合同和执行记录，规则命中结果不得只停留在代码隐式判断中
- 规则调整后必须计算影响面并触发受影响知识的增量重算；已正式入库知识不得被规则变更静默覆盖
- 阶段策略与规则必须沉淀为可复用策略包资产；抽取任务必须绑定明确的策略包版本和运行快照，不能只读取当前页面配置
