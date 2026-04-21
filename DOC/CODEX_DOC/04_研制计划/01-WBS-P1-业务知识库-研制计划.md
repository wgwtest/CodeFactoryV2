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
- 已有运行闭环
- 持续优化中
- 重点问题仍集中在正式抽取质量、长文档处理、关系完整性和知识展示解释性

## 6. 后续约束

- 正式知识抽取继续执行 `Docling + 结构化大模型` 硬约束
- `P1` 的正式成果必须保持为后续 `P2` 的稳定输入，不直接暴露内部脚本和中间态文件
