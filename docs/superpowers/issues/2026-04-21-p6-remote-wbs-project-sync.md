# P6 远端 WBS 树与 Project 投影同步快照

> 历史快照说明：本文件属于 `docs/superpowers/issues/` 下的历史 WBS 快照与过程证据，不是当前 WBS 树事实源。
>
> 当前 WBS 唯一事实源：GitHub `Issues + sub-issues`。
>
> 若远端暂时不可访问，应优先回退到仓库主工作树中的 `DOC/CODEX_DOC/` 正式文档根，不使用当前隔离目录中的 mirror 文件反推当前远端状态。

> 本快照记录 2026-04-21 对 GitHub `wgwtest/CodeFactoryV2` 中 `P6` 远端 WBS 树与 `Project 7` 投影的同步结果。
>
> 本快照覆盖 2026-04-17 旧版 `P6` 本地镜像口径；若两者不一致，以本快照和远端当前状态为准。

## 1. 本轮同步范围

- GitHub Issue `#59` `WBS L1: P6 门户与平台入口`
- GitHub Issue `#60` `WBS L2: P6.1 首屏门户`
- GitHub Issue `#61` `WBS L2: P6.2 跨阶段状态集成`
- GitHub Issue `#62` `WBS L2: P6.3 前端展示基线`
- GitHub Issue `#63` `WBS L2: P6.4 前端展示实验`
- GitHub Issue `#64 ~ #67`、`#77 ~ #88`
- GitHub Project `#7` `CodeFactoryV2 Delivery Roadmap`

本轮采用“保号重构”方式处理 `P6`：

- 复用既有节点 `#59 ~ #67`
- 新增 `L3` 节点 `#77 ~ #88`
- 不重新另起第二棵 `P6` 树

## 2. 当前有效 Issue Tree

- `#59` `P6 门户与平台入口` `[开发中]`
  - `#60` `P6.1 首屏门户` `[已完成]`
    - `#64` `P6.1.1 节点定义` `[已完成]`
    - `#65` `P6.1.2 连线定义` `[已完成]`
    - `#66` `P6.1.3 布局与交互` `[已完成]`
    - `#67` `P6.1.4 门户数据接口` `[已完成]`
  - `#61` `P6.2 跨阶段状态集成` `[待开发]`
    - `#77` `P6.2.1 阶段查询接口` `[待开发]`
    - `#78` `P6.2.2 状态快照模型` `[待开发]`
    - `#79` `P6.2.3 缓存与降级` `[待开发]`
    - `#80` `P6.2.4 页面接口` `[待开发]`
  - `#62` `P6.3 前端展示基线` `[待开发]`
    - `#81` `P6.3.1 Token 与主题` `[待开发]`
    - `#82` `P6.3.2 命名与状态文案` `[待开发]`
    - `#83` `P6.3.3 共享组件` `[待开发]`
    - `#84` `P6.3.4 基线校验` `[待开发]`
  - `#63` `P6.4 前端展示实验` `[待开发]`
    - `#85` `P6.4.1 模板与绑定` `[待开发]`
    - `#86` `P6.4.2 布局与预设` `[待开发]`
    - `#87` `P6.4.3 实验记录` `[待开发]`
    - `#88` `P6.4.4 实验页验证` `[待开发]`

## 3. Project 7 投影结果

`Project 7` 当前已为 `P6` 扩展并使用以下字段选项：

- `Layer` 新增 `L3`
- `Phase` 新增 `6`
- `Contributes To` 新增 `M6`

`P6` 相关项目项当前投影如下：

- `#59`：`In Progress / L1 / 6 / M6 / Phase / P6 / parent=CodeFactoryV2`
- `#60`：`Done / L2 / 6 / M6 / Package / P6.1 / parent=P6`
- `#61`：`Todo / L2 / 6 / M6 / Package / P6.2 / parent=P6`
- `#62`：`Todo / L2 / 6 / M6 / Package / P6.3 / parent=P6`
- `#63`：`Todo / L2 / 6 / M6 / Package / P6.4 / parent=P6`
- `#64 ~ #67`：`Done / L3 / 6 / M6 / Package / parent=P6.1`
- `#77 ~ #80`：`Todo / L3 / 6 / M6 / Package / parent=P6.2`
- `#81 ~ #84`：`Todo / L3 / 6 / M6 / Package / parent=P6.3`
- `#85 ~ #88`：`Todo / L3 / 6 / M6 / Package / parent=P6.4`

## 4. 节点与正式文档映射

- `P6`
  - 研制计划：`DOC/CODEX_DOC/04_研制计划/06-WBS-P6-门户与平台入口-研制计划.md`
  - 总体设计：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6-门户与平台入口设计.md`
- `P6.1`
  - 专项设计：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6.1-首屏观察门户设计.md`
- `P6.2`
  - 专项设计：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6.2-跨阶段只读集成与状态投影设计.md`
- `P6.3`
  - 专项设计：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6.3-设计语言与前端展示基线设计.md`
- `P6.4`
  - 专项设计：`DOC/CODEX_DOC/02_设计说明/P6_门户与平台入口/P6.4-前端展示工具化实验场设计.md`

## 5. 本轮校验方式

本快照基于以下远端校验命令生成：

- `gh api graphql` 查询 `#59` 的 `subIssues -> subIssues`
- `gh project field-list 7 --owner @me --format json`
- `gh project item-list 7 --owner @me --limit 200 --format json | jq ...`

本文件只记录 2026-04-21 当前轮次结果；后续若远端再次调整，应新增后续历史快照，不倒改本文件的事实时间点。
