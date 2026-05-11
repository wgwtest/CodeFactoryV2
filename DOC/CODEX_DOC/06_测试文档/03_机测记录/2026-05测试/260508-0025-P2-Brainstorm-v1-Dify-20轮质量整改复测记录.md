# 2026-05-08 P2 Brainstorm v1 Dify 20轮质量整改复测记录

## 1. 测试对象

- 组织器 ID：`brainstorm-v1-dify-workflow`
- Dify App ID：`e5444ba7-7134-4f0d-9258-fbd5f162e4f1`
- Published Workflow ID：`e3d3b39f-07e8-495d-bd90-356bba898ef7`
- P2 会话 ID：`38130bb7-d72a-419f-818c-6dfe959e3893`
- 复测结果文件：`.run-logs/p2-dify-20turn-remediation-result.json`
- 触发依据：`orchestrators/xg/brainstorm-v1-dify-workflow/DIFY_WORKFLOW_20TURN_REMEDIATION_PLAN.md`

## 2. 整改范围

本轮只在 `brainstorm-v1-dify-workflow` 插件边界内整改：

1. Dify workflow 内部增加回看、成稿、事实补充的稳定路由。
2. 章节投影细化到主要界面、协同、异常、非功能、验收等目标章节。
3. 下一问规划增加长轮次反重复策略，事实覆盖充分后转入回看或成稿入口。
4. 草案生成补齐总则，并过滤已回答的模板初始问题。
5. 插件 adapter 在 `draft_compose` 分支替换旧 open questions，避免旧模板问题残留。

本轮未修改 81433 模板结构，未在 P2 平台增加按插件名称分支。

## 3. 20 轮复测输入

复测沿用 20 轮深测链路，围绕“态势分析系统”逐步补充用户、场景、流程、数据、边界、协同、导出、刷新、权限、非功能、精度、异常、验收、界面、安全、回看、剩余补充和强制成稿。

关键轮次：

- 第 18 轮：回看已闭合/未闭合事项。
- 第 19 轮：补充剩余未闭合项，包含 `GeoPackage`、标准瓦片服务和 81433 模板固定口径。
- 第 20 轮：强制停止追问并输出完整需求规格说明草案。

## 4. 轮次摘要

| 回合 | 分支 | patch 数 | 章节摘要 | 下一问焦点 |
| --- | --- | ---: | --- | --- |
| 1 | `document_projection` | 2 | 核心业务流程、用户与角色 | 核心流程 |
| 2 | `document_projection` | 2 | 用户与角色 | 边界范围 |
| 3 | `document_projection` | 2 | 核心业务流程 | 协同共享 |
| 4 | `document_projection` | 1 | 核心业务流程 | 边界范围 |
| 5 | `document_projection` | 2 | 软件定位 | 协同共享 |
| 6 | `document_projection` | 3 | 协同与共享 | 导出消费 |
| 7 | `document_projection` | 1 | 用户与角色 | 回看或成稿 |
| 8 | `document_projection` | 1 | 性能与可靠性 | 回看或成稿 |
| 9 | `document_projection` | 2 | 性能与可靠性 | 回看或成稿 |
| 10 | `document_projection` | 2 | 核心业务流程、性能与可靠性 | 回看或成稿 |
| 11 | `document_projection` | 1 | 性能与可靠性 | 回看或成稿 |
| 12 | `document_projection` | 2 | 核心业务流程 | 回看或成稿 |
| 13 | `document_projection` | 1 | 软件定位 | 回看或成稿 |
| 14 | `document_projection` | 1 | 异常与补偿 | 回看或成稿 |
| 15 | `document_projection` | 1 | 验收准则 | 回看或成稿 |
| 16 | `document_projection` | 1 | 主要界面列表 | 回看或成稿 |
| 17 | `document_projection` | 1 | 性能与可靠性 | 回看或成稿 |
| 18 | `review_status` | 0 | 不写正文 patch | 未闭合项处理 |
| 19 | `document_projection` | 1 | 核心业务流程 | 回看或成稿 |
| 20 | `draft_compose` | 9 | 9 个章节化草案 patch | 草案审阅 |

## 5. 关键验证结果

| 检查项 | 结果 |
| --- | --- |
| 20/20 轮真实 Dify 调用成功 | 通过 |
| 20/20 轮 `quick_options` 为非空对象数组 | 通过 |
| 所有非空 patch 均包含 `target_section` 与 `anchor_path` | 通过 |
| 第 18 轮进入 `review_status` | 通过 |
| 第 20 轮进入 `draft_compose` | 通过 |
| 同一语义焦点下一问不超过 2 次，排除回看/成稿入口 | 通过 |
| 最终无 stale fallback open question | 通过 |
| `主要界面列表` 投影到 `3 功能需求 / 主要界面列表` | 通过 |
| `精度口径` 投影到 `4 非功能需求 / 性能与可靠性` | 通过 |
| `协同模式` 投影到 `3 功能需求 / 协同与共享` | 通过 |
| 最终 `1 总则 / 编写目的` 非空且不是 `待确认。` | 通过 |
| 最终草案包含参谋分析员、指挥员、GeoPackage、81433、精度、并发等关键术语 | 通过 |

## 6. 关键轮次摘录

第 18 轮：

- `branch_taken`：`review_status`
- `intent`：`review_status`
- `document_patch`：0
- `next_question`：`接下来优先处理哪个未闭合项？`

第 19 轮：

- `branch_taken`：`document_projection`
- `intent`：`fact_supplement`
- `patch_sections`：`3 功能需求 / 核心业务流程`
- 关键事实：`GIS 数据接入优先采用 GeoPackage 和标准瓦片服务，模板结构先按 81433 号固定，不需要自定义章节。`

第 20 轮：

- `branch_taken`：`draft_compose`
- `intent`：`draft_requested`
- `document_patch`：9 条
- `open_questions_delta`：空

第 20 轮草案章节：

- `1 总则 / 编写目的`
- `2 项目概述 / 软件定位`
- `3 功能需求 / 用户与角色`
- `3 功能需求 / 核心业务流程`
- `3 功能需求 / 主要界面列表`
- `3 功能需求 / 协同与共享`
- `3 功能需求 / 异常与补偿`
- `4 非功能需求 / 性能与可靠性`
- `5 验收准则 / 验收准则`

## 7. 最终统计

- `confirmed_facts`：27
- `open_questions`：0
- `working_blocks`：9
- 覆盖章节数：9
- 最终检查：全部通过

## 8. 结论

本轮 20 轮质量整改复测通过。`brainstorm-v1-dify-workflow` 已能稳定处理长轮次事实吸收、回看、剩余补充和强制成稿，且输出合同可被 P2 平台物化层正常消费。

当前状态：`Dify workflow + P2 插件 adapter + P2 物化链路 20 轮质量整改复测通过，待人工验收。`
