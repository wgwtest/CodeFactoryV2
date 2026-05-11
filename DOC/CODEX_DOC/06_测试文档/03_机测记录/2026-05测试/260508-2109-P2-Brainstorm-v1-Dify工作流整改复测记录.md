# 2026-05-08 P2 Brainstorm v1 Dify 工作流整改复测记录

## 1. 测试对象

- 组织器 ID：`brainstorm-v1-dify-workflow`
- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- Published Workflow ID：`3e6c884d-fb5e-4977-a5b2-fb01bd5f3367`
- Provider：`deepseek-chat`
- 触发依据：`orchestrators/xg/brainstorm-v1-dify-workflow/DIFY_WORKFLOW_REFACTOR_PLAN.md`

## 2. 整改内容

本轮只整改 Dify workflow 行为，不修改 P2 通用插件合同。

已完成：

1. `normalize_input` 派生上一问、上一组选项、已知事实、未闭合问题摘要和 `draft_requested`。
2. `document_projection` 改为按事实语义投影章节，不再全部写入 `1 总则 / 编写目的`。
3. `document_patch` 每条补齐 `target_section` 与 `anchor_path`。
4. `quick_options` 由最终节点保证为 `{key,label,recommended}` 对象数组。
5. “停止追问 / 输出草案 / 先成稿 / 不要继续问”进入草案分支。
6. 草案分支生成章节化正文，并把未闭合问题压缩为保留缺口。

## 3. 复测链路

使用 6 轮真实 Dify 调用：

1. 模糊起始需求：态势分析系统，包含态势展示、GIS 分析、通视量算、坡度分析、部署分析。
2. 选择快捷选项 `A`。
3. 补充角色和场景：主要用户为参谋分析员，下游查看者为指挥员，主场景为实时态势展示兼顾事前研判。
4. 补充数据接入：实时接入态势与告警，同时导入底图、任务区、DEM、部署点位和标注。
5. 补充边界：不做自动最优部署推荐，只做覆盖、冲突和影响分析。
6. 强制收束：停止追问，输出需求规格说明草案并保留未闭合问题。

## 4. 轮次摘要

| 回合 | 状态 | patch 数 | 章节 | 下一问摘要 |
| --- | --- | ---: | --- | --- |
| 1 | succeeded | 1 | `3 功能需求 / 用户与角色` | 核心数据接入和主要分析流程是什么？ |
| 2 | succeeded | 1 | `3 功能需求 / 核心业务流程` | 明确不做范围、异常处理或验收口径 |
| 3 | succeeded | 3 | `3 功能需求 / 用户与角色`、`3 功能需求 / 核心业务流程` | 核心数据接入和主要分析流程是什么？ |
| 4 | succeeded | 1 | `3 功能需求 / 核心业务流程` | 明确不做范围、异常处理或验收口径 |
| 5 | succeeded | 2 | `2 项目概述 / 软件定位` | 继续补充核心流程、边界、非功能或验收准则 |
| 6 | succeeded | 7 | `1 总则`、`2 项目概述`、`3 功能需求`、`4 非功能需求`、`5 验收准则` | 接受草案或继续细化缺口 |

## 5. 验收检查

| 检查项 | 结果 |
| --- | --- |
| 6 轮真实 Dify 调用均成功 | 通过 |
| 每轮 `quick_options` 都是对象数组 | 通过 |
| 每轮 `document_patch` 都包含 `target_section` 与 `anchor_path` | 通过 |
| 第 3 轮不再机械重复“编写目的”旧问题 | 通过 |
| 事实投影分散到至少 3 个章节 | 通过，实际覆盖 7 类章节 |
| 第 6 轮进入草案分支 | 通过，`branch_taken=draft_compose` |
| `open_questions` 未无限增长 | 通过，最终为 2 个保留缺口 |

## 6. 最终统计

- `confirmed_facts`：8
- `open_questions`：2
- `working_blocks`：15
- 覆盖章节：
  - `1 总则 / 编写目的`
  - `2 项目概述 / 软件定位`
  - `3 功能需求 / 用户与角色`
  - `3 功能需求 / 核心业务流程`
  - `3 功能需求 / 异常与补偿`
  - `4 非功能需求 / 性能与可靠性`
  - `5 验收准则 / 验收准则`

## 7. 结论

本轮整改已解决系统端测试建议中指出的核心 workflow 行为问题：

- 多事实输入可以拆分吸收。
- 章节投影不再集中堆到 `1 总则 / 编写目的`。
- 快捷选项和正文补丁合同稳定。
- 强制收束会生成章节化草案，而不是把“停止追问”写成正文事实。

当前状态：`Dify workflow 已自测通过，但当时 P2 平台物化层仍未完整消费多章节 document_patch。`

## 8. 平台物化层修复后复测

### 8.1 复测背景

后续真实联调发现，上述 Dify workflow 虽然已经返回多章节 `document_patch`，但 `P2` 平台在 `PluginTurnResultMaterializer` 中仍将其压扁为单条 `AP-PLUGIN-001` 合成 patch，导致：

- `turn.spec_execution.document_patch` 只剩 1 条；
- `session.working_document.blocks` 只有 1 个块；
- 最终草案被错误堆入 `1 总则 / 编写目的`。

因此本轮追加复测同时覆盖：

1. Dify workflow 输出是否仍正确；
2. P2 平台物化层修复后，是否能保留章节级 patch 并生成多 block working document。

### 8.2 复测环境

- 工作树：`/home/wgw/CodexProject/CodeFactoryV2/.worktrees/p2-validation-workflow`
- 后端地址：`http://127.0.0.1:8020/`
- 复测摘要文件：`/tmp/p2-dify-after-materializer-fix.json`

### 8.3 复测输入链路

本轮使用 6 轮真实 Dify 调用：

1. 这个系统叫空域运算软件，主要解决空域计算分析需求。
2. 软件主要面向空域规划人员和算法分析人员，重点是计算分析，不先做协同规划平台。
3. 核心流程是导入空域基础数据和任务约束，执行空域可用性、冲突和容量评估，然后输出分析结果报告。
4. 异常情况包括数据缺失、坐标系不一致、约束冲突和计算失败，需要提示原因并允许修正后重算。
5. 性能上希望常规区域计算在三分钟内完成，结果要可追溯，至少保存输入版本、算法版本和计算日志。
6. 先停止追问，基于现有信息输出需求规格草案。

### 8.4 关键结果

| 回合 | Dify 原始 patch 数 | P2 物化 patch 数 | working block 数 | 关键观察 |
| --- | ---: | ---: | ---: | --- |
| 1 | 2 | 2 | 1 | 两条 patch 都落在 `1 总则 / 编写目的`，block 数保持 1，符合章节语义 |
| 2 | 1 | 1 | 1 | 仍落在 `1 总则 / 编写目的` |
| 3 | 1 | 1 | 2 | 新增 `3 功能需求 / 核心业务流程` block |
| 4 | 1 | 1 | 3 | 新增 `3 功能需求 / 异常与补偿` block |
| 5 | 1 | 1 | 4 | 新增 `4 非功能需求 / 性能与可靠性` block |
| 6 | 7 | 7 | 7 | `draft_compose` 分支成功，章节化草案完整落入 7 个 block |

### 8.5 最终草案轮检查

- 会话 ID：`1575459a-1aae-487e-9dea-941990196cb4`
- `branch_taken`：`draft_compose`
- Dify 原始 `document_patch`：7 条
- P2 物化后 `document_patch`：7 条
- `working_document.blocks`：7 个

最终覆盖章节：

- `1 总则 / 编写目的`
- `2 项目概述 / 软件定位`
- `3 功能需求 / 用户与角色`
- `3 功能需求 / 核心业务流程`
- `3 功能需求 / 异常与补偿`
- `4 非功能需求 / 性能与可靠性`
- `5 验收准则 / 验收准则`

### 8.6 结论更新

平台物化层修复后，本组织器链路满足以下条件：

1. Dify workflow 保持章节化 `document_patch` 输出能力；
2. P2 平台不再把多章节 patch 压扁成单条合成 patch；
3. `working_document.blocks` 可按章节增长；
4. “停止追问并输出草案”可在 Dify 草案分支和 P2 working document 两侧同时成立。

当前状态更新为：`Dify workflow + P2 平台物化层联调通过，待人工验收。`
