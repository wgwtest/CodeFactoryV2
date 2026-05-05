# P2 Brainstorming Lab 原型 v1 交接

**时间：** 2026-05-01 12:08:54

## 1. 本轮目标

根据用户确认，制作 `P2 Brainstorming Lab` 独立原型图。

核心要求：

- `Brainstorming` 是独立模块，不是正式需求规格编辑器内嵌功能。
- `Brainstorming` 必须体现可插拔、可替换边界。
- 原型需要帮助理解 Brainstorming 的工作循环、生命周期和服务职责。

## 2. 产物

原型包：

- `DOC/CODEX_DOC/08_原型与附图/2026-05-01-120854-CodeFactoryV2-P2-Brainstorming-Lab原型-v1/`

评审图：

- `01-1920x1080-独立BrainstormingLab首页.png`
- `02-1920x1080-单轮循环运行态.png`
- `03-1920x1080-可插拔组织器替换态.png`

源文件：

- `source/p2-brainstorming-lab-prototype.html`

## 3. 设计要点

1. 首页表达独立 Lab、会话配置、CLI 式问答和过程浮现。
2. 单轮循环态表达 `Brainstorming Service` 的后台循环。
3. 组织器替换态表达 `RequirementAnalysisOrchestrator` 插槽。
4. `document_patch` 只作为建议显示，不写入正式规格。
5. 替换组织器时，正式需求规格文档、模板、知识绑定、草稿保存、检查冻结和 `P2 -> P3` 输出保持稳定。

## 4. 自检

自检记录：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-01-120854-P2-Brainstorming-Lab原型v1自检记录.md`

已确认：

- 三张截图均为 `1920 x 1080`
- `git diff --check` 通过
- 人工查看三张截图，未发现明显空白、遮挡或状态混入问题

## 5. 后续建议

等待用户评审 v1。

如果用户确认，可进入实现计划：

1. Mock Provider 版本的 `/p2-brainstorm-lab`
2. `BrainstormSession` / `BrainstormTurn` 数据契约
3. `RequirementAnalysisOrchestrator` 抽象边界
4. 后续再接真实 DeepSeek / OpenAI Provider
