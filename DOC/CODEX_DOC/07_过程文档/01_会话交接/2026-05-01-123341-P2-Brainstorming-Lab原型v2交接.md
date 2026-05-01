# P2 Brainstorming Lab 原型 v2 交接

**时间：** 2026-05-01 12:33:41

## 1. 本轮目标

根据用户对 v1 的批注，修正 `P2 Brainstorming Lab` 原型。

## 2. 用户批注

1. v1 左侧的 `Lab 会话首页 / 单轮循环运行态 / 组织器替换态` 不像业务对象，像原型图目录。
2. v1 单轮循环运行态左侧没有选中对象。
3. 单轮输入输出应该对应当前输入对象，而不是整个会话。
4. 可插拔组织器在逻辑上应该是更上一级，先配置组织器，再进入下方业务功能。

## 3. 产物

原型包：

- `DOC/CODEX_DOC/08_原型与附图/2026-05-01-123341-CodeFactoryV2-P2-Brainstorming-Lab原型-v2/`

评审图：

- `01-1920x1080-组织器配置入口.png`
- `02-1920x1080-Lab会话工作台.png`
- `03-1920x1080-当前Turn单轮循环.png`

源文件：

- `source/p2-brainstorming-lab-prototype.html`

## 4. 设计修正

1. 将组织器配置前置为第一张图。
2. 左侧改为真实 Lab 对象树：组织器配置、会话、当前 Turn、Provider 调用日志。
3. 会话工作台页选中 `会话 bs-airspace-001`。
4. 单轮循环页选中 `当前 Turn turn-0007`。
5. 单轮页展示 Turn ID、所属会话、回答对象、用户当前输入、规范化解释、本轮结构化输出摘要。

## 5. 自检

自检记录：

- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-01-123341-P2-Brainstorming-Lab原型v2自检记录.md`

已确认：

- 三张截图均为 `1920 x 1080`
- 人工查看三张截图，未发现明显空白、遮挡或状态混入问题

## 6. 后续建议

等待用户评审 v2。

如果用户确认，可进入实现计划：

1. Mock Provider 版本的 `/p2-brainstorm-lab`
2. `RequirementAnalysisOrchestrator` 管理入口
3. `BrainstormSession` 和 `BrainstormTurn` 数据契约
4. 当前 Turn 详情页或详情区域
