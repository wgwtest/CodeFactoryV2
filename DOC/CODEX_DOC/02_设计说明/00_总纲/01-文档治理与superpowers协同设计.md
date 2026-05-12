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
- 历史过程证据与执行工单镜像留存

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

GitHub Issue、Project、PR 中涉及正式设计、共享规范和正式计划时，优先引用：

- `DOC/CODEX_DOC/02_设计说明/...`
- `DOC/CODEX_DOC/03_规范与流程/...`
- `DOC/CODEX_DOC/04_研制计划/...`

过程性讨论、局部计划和 issue mirror 可引用：

- `docs/superpowers/...`

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

当前口径调整为：

- 不再把 `docs/superpowers/issues/` 作为当前 WBS 树的默认读取入口
- GitHub `Issues + sub-issues` 是 WBS 树唯一事实源
- `docs/superpowers/issues/` 如继续保留文件，只作为历史快照、执行工单镜像和过程证据
- 若远端暂时不可访问，应优先读取仓库主工作树中的 `DOC/CODEX_DOC/` 正式文档，而不是当前隔离目录中的镜像文件

### 4.4 正式回写

出现以下任一情况时，必须同步更新 `DOC/CODEX_DOC/`：

- 用户明确确认方案
- WBS 节点结构发生变化
- 局部方案升级为阶段正式方案
- 需要作为后续多轮开发的稳定入口

节点合同、验收大纲、人测记录与验收结论的正式文种边界，后续统一以：

- `DOC/CODEX_DOC/02_设计说明/00_总纲/02-节点合同与验收文种体系设计.md`

为准。

### 4.5 设计说明补充稿命名

当某个阶段主设计文档已经存在，但本轮工作只需要沉淀阶段性深化设计、专项论证、重构依据或待评审方案时，不直接改名或复制主设计文档，而是在对应阶段目录下新增补充稿。

补充稿命名规则为：

```text
P阶段-中文标题-YYMMDD-HHMM-补充主题.md
```

其中 `P阶段-中文标题` 必须与被补充的主设计文档标题保持一致，`YYMMDD-HHMM` 表示补充稿版本时间。主设计文档本身保持稳定入口，不在文件名中追加日期时间。补充稿中的稳定结论被采纳后，应按需要回写到主设计文档；补充稿继续作为设计演进和评审依据保留。

## 5. 对 superpowers 的继续使用口径

可以继续使用 `superpowers`，且迁移正式文档后并不会与其冲突。

前提只有一个：

- 不再让 `superpowers` 独自承担正式规范根职责

这意味着：

- 你仍然可以用 `superpowers` 生成新设计文档
- 你仍然可以用 `superpowers` 生成实施计划
- 你可以在 `docs/superpowers/issues/` 保留历史快照或执行工单镜像
- 但正式采纳的结果必须同步进 `DOC/CODEX_DOC/`

## 6. 文档创建建议

### 6.1 新增正式阶段节点时

至少同步更新：

- `DOC/CODEX_DOC/04_研制计划/` 下对应节点文档
- 需要时补充 `DOC/CODEX_DOC/02_设计说明/` 下的正式设计
- 涉及共享接口、状态输出、关键流程时补充 `DOC/CODEX_DOC/03_规范与流程/`
- 涉及单节点执行边界时补充 `DOC/CODEX_DOC/05_节点合同/`

### 6.2 新增局部实现方案时

优先在：

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

中起草。

### 6.3 新增测试与过程证据时

统一落到：

- `DOC/CODEX_DOC/06_测试文档/`
- `DOC/CODEX_DOC/07_过程文档/`

## 7. 当前仓库映射结论

当前项目已经形成了较多 `superpowers` 文档资产，因此本轮采用“正式目录重构 + 旧引用回收 + 工作层继续保留”的方式：

- 正式文档根维持为 `DOC/CODEX_DOC/`
- 正式目录按 `01_需求分析 / 02_设计说明 / 03_规范与流程 / 04_研制计划 / 05_节点合同 / 06_测试文档 / 07_过程文档` 固化
- `superpowers -> 正式文档` 映射表持续维护
- `docs/superpowers/` 保留为工作层，不再承载正式目录职责

后续以“渐进归一化”代替“一次性推倒重来”。
