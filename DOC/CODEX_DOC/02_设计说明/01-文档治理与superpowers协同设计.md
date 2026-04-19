# 文档治理与 superpowers 协同设计

## 1. 目标

本文件定义 `CodeFactoryV2` 后续如何同时使用：

- 全局工程策略
- 项目正式文档根
- `superpowers` 工作文档体系

目标不是废弃 `superpowers`，而是给它一个明确边界，使其与正式文档体系长期兼容。

## 2. 角色划分

### 2.1 正式文档层

路径：

- `DOC/CODEX_DOC/`

职责：

- 作为项目长期稳定的单一权威本地文档根
- 作为用户阅读、审阅、确认和后续追溯的唯一终稿入口
- 保存总体设计、正式 WBS、长期规范、验收和交接文档

### 2.2 superpowers 工作层

路径：

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`
- `docs/superpowers/issues/`
- `.superpowers/brainstorm/`

职责：

- 方案推演
- 草案快速起草
- 局部计划编写
- issue tree mirror 维护
- 为正式文档层提供来源素材与迁移台账

限制：

- 不作为用户默认阅读路径
- 不要求用户按时间命名文件去检索设计结论
- 不能把时间化过程稿直接当成终稿交付

### 2.3 远端协作层

路径载体：

- GitHub Project
- GitHub Issues

职责：

- 排程
- 树结构展示
- 执行契约
- 审查评论

## 3. 协同原则

### 3.1 单一权威原则

`DOC/CODEX_DOC/` 是正式本地文档单一权威源。

含义：

- `superpowers` 可以先产生文档
- 但“正式采用”的方案必须回写 `DOC/CODEX_DOC/`
- 若两边内容不一致，以 `DOC/CODEX_DOC/` 为准

### 3.2 分层不分裂原则

`superpowers` 与正式文档不是两套互不相干的系统。

正确关系是：

- `superpowers` 负责形成工作过程文档
- 正式文档层负责沉淀被采纳的稳定结果

### 3.3 路径稳定原则

GitHub Issue、Project、PR 中涉及正式设计和正式计划时，优先引用：

- `DOC/CODEX_DOC/02_设计说明/...`
- `DOC/CODEX_DOC/03_研制计划/...`

过程性讨论、局部计划和 issue mirror 可引用：

- `docs/superpowers/...`

### 3.4 用户阅读面原则

本项目对用户的文档交付口径明确如下：

- 用户只看 `DOC/CODEX_DOC/` 下整理好的终稿文档
- 不要求用户进入 `docs/superpowers/` 或 `.superpowers/brainstorm/` 检索过程稿
- 若某个结论还只存在于 `superpowers`，则视为尚未完成正式归档
- “已建立映射关系”不等于“用户可直接据此阅读”

原因：

- `superpowers` 文件默认按时间组织
- 时间顺序不等于逻辑顺序
- 过程稿适合工作推进，不适合用户按主题检索和长期阅读

## 4. 后续开发工作流

### 4.1 方案起草

允许在 `docs/superpowers/specs/` 创建设计草案。

适用场景：

- 新模块探索
- 局部方案收敛
- 多方案比选

### 4.2 实施分解

允许在 `docs/superpowers/plans/` 创建实现计划。

适用场景：

- 任务拆分
- 分支实施
- 阶段性执行计划

### 4.3 issue tree mirror

允许在 `docs/superpowers/issues/` 保存 issue 树镜像和执行工单镜像。

### 4.4 正式回写

出现以下任一情况时，必须同步更新 `DOC/CODEX_DOC/`：

- 用户明确确认方案
- WBS 节点结构发生变化
- 局部方案升级为阶段正式方案
- 需要作为后续多轮开发的稳定入口
- 即使用户未单独审阅 `superpowers` 草稿，只要本轮实现已经实际采用其中结论并作为工作依据，也必须回写正式文档

### 4.5 迁移粒度原则

从 `superpowers` 迁移到 `DOC/CODEX_DOC/` 时，不能只做“加链接、加映射、挂入口”。

至少以下核心细节必须按逻辑归档进根目录正式文档：

- 模块职责与边界
- 节点拆解与阶段结构
- 数据模型、对象模型、状态模型
- 输入输出契约与接口约束
- 关键算法、处理策略与质量门
- 页面级验证投影、关键交互规则
- 风险、限制、迁移策略与验收口径

判定标准：

- 只有这些核心细节已经进入 `DOC/CODEX_DOC/` 的逻辑化文档结构，才算“迁移完成”
- 如果只是 `superpowers -> 正式文档` 建了映射表，但正文仍停留在时间稿中，则只能算“已登记来源，未完成正式迁移”

## 5. 对 superpowers 的继续使用口径

可以继续使用 `superpowers`，且迁移正式文档后并不会与其冲突。

前提只有一个：

- 不再让 `superpowers` 独自承担正式规范根职责

这意味着：

- 你仍然可以用 `superpowers` 生成新设计文档
- 你仍然可以用 `superpowers` 生成实施计划
- 你仍然可以维护 issue tree mirror
- 但正式采纳的结果必须同步进 `DOC/CODEX_DOC/`

## 6. 文档创建建议

### 6.1 新增正式阶段节点时

至少同步更新：

- `DOC/CODEX_DOC/03_研制计划/` 下对应节点文档
- 需要时补充 `DOC/CODEX_DOC/02_设计说明/` 下的正式设计

### 6.2 新增局部实现方案时

优先在：

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

中起草。

但起草完成后的处理规则是：

- `superpowers` 保留过程稿
- `DOC/CODEX_DOC/` 负责按主题、按阶段、按节点整理终稿
- 不允许长期让用户可用结论只停留在 `superpowers` 时间稿里

### 6.3 新增测试与过程证据时

统一落到：

- `DOC/CODEX_DOC/05_测试文档/`
- `DOC/CODEX_DOC/06_过程文档/`

## 7. 当前仓库映射结论

当前项目已经形成了较多 `superpowers` 文档资产，因此本轮不做粗暴删除或大规模迁移，而采用：

- 正式文档根补建
- WBS 与设计入口补建
- `superpowers -> 正式文档` 映射表补建

需要明确补充的是：

- 映射表只是迁移台账，不是迁移完成证明
- 后续必须持续把已采纳核心细节按逻辑顺序归并进 `DOC/CODEX_DOC/`
- 不再允许把“用户去看 `superpowers/specs` 时间稿”当成正式阅读路径

后续以“渐进归一化”代替“一次性推倒重来”。
