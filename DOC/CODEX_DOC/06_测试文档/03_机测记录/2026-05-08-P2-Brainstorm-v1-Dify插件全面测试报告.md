# 2026-05-08 P2 Brainstorm v1 Dify 插件全面测试报告

## 1. 测试背景

本次测试针对 `brainstorm-v1-dify-workflow` 组织器插件进行一次面向真实 Dify workflow 的全面联调验证。

触发原因有两类：

1. 用户在人测中发现 P2 页面会显示若干快捷选项，但选项文本为空。
2. 需要按照既有《P2 组织器插件与 Codex Brainstorming 对照测试指南》的口径，对该 Dify 插件做不少于单轮“能返回”的更完整验证，确认其合同输出、选项结构、多轮推进、提前收束和正文承载行为。

## 2. 测试对象

- 组织器 ID：`brainstorm-v1-dify-workflow`
- 插件类型：`dify_workflow`
- Provider：`deepseek`
- 运行入口：
  - `POST /api/requirement-analysis/sessions`
  - `POST /api/requirement-analysis/sessions/{session_id}/turns`
- 相关代码：
  - `orchestrators/xg/brainstorm-v1-dify-workflow/adapter.py`
  - `apps/api/app/orchestrators/plugin_result_normalizer.py`
  - `apps/web/src/pages/RequirementAnalysisLabPage.tsx`

## 3. 测试环境

- 工作树：`/home/wgw/CodexProject/CodeFactoryV2/.worktrees/p2-validation-workflow`
- Git 提交：`9ab3acb` 为测试起点；测试过程中定位并修复了快捷选项合同问题
- 前端地址：`http://127.0.0.1:5174/`
- 后端地址：`http://127.0.0.1:8020/`
- Dify：真实 workflow，阻塞调用
- 本地数据库：`.data/codefactoryv2-dev.sqlite3`

## 4. 测试输入链路

本次实际执行 6 轮：

1. 模糊起始需求：态势分析系统，包含态势展示、GIS 分析、通视量算、坡度分析、部署分析，用户与使用模式未明确。
2. 选择快捷选项 A：军事态势分析系统。
3. 补充事实：主要用户为参谋分析员，下游查看者为指挥员；主场景为实时态势展示兼顾事前研判。
4. 补充事实：数据接入采用混合模式，实时 + 导入并存。
5. 补充边界：部署分析不做自动最优推荐，只做覆盖、冲突、影响分析。
6. 强制收束：停止追问，要求输出草案并保留未闭合问题。

## 5. 关键问题复现与定位

### 5.1 空快捷选项问题

用户反馈“P2 页面会出现 4 个选项，但选项文本为空”。

实际定位结果如下：

1. 真实 Dify workflow 返回的 `quick_options` 在部分场景下是字符串数组，而不是 `{key,label}` 对象数组。
2. `brainstorm-v1-dify-workflow` adapter 将这组字符串原样放入 `interaction_output.quick_options`。
3. `apps/api/app/orchestrators/plugin_result_normalizer.py` 在归一化时直接 `list(...)` 透传。
4. 前端 `RequirementAnalysisLabPage.tsx` 在渲染时假定每个选项都具备 `option.key` 和 `option.label`。
5. 因此前端收到字符串数组时，`option.key` 和 `option.label` 都是空值，页面就表现为“有按钮但没有文案”。

### 5.2 结论

这是 **P2 服务端合同归一化缺陷**，不是 Dify workflow 本身“没有给出选项”，也不是纯前端样式问题。

### 5.3 修复

已在：

`apps/api/app/orchestrators/plugin_result_normalizer.py`

加入 `quick_options` 归一化逻辑：

- 若插件返回对象数组，则保留 `key/label/recommended`。
- 若插件返回字符串数组，则自动转换为：
  - `A/B/C/D/E`
  - `label=原字符串`
  - 第一项 `recommended=true`

并补充回归测试：

`apps/api/tests/test_orchestrator_plugin_contracts.py`

## 6. 全面测试结果

### 6.1 轮次摘要

| 回合 | 用时 | 选项数 | 选项合同是否正确 | patch 数 | 现象 |
| --- | ---: | ---: | --- | ---: | --- |
| 1 | 35.31s | 4 | 是 | 1 | 正常提出软件名称/领域/目的问题 |
| 2 | 18.15s | 4 | 是 | 1 | 选择 A 后正常继续追问“编写目的” |
| 3 | 26.16s | 4 | 是 | 1 | 已补充用户与场景，但仍重复追问“编写目的” |
| 4 | 25.00s | 4 | 是 | 1 | 话题跳到数据接入触发条件 |
| 5 | 20.68s | 3 | 是 | 1 | 正常识别“不做自动最优部署推荐”边界 |
| 6 | 14.05s | 4 | 是 | 1 | 可响应“停止追问并生成草案” |

### 6.2 快捷选项合同验证

修复后，真实 API 返回的 `next_interaction.options` 结构如下：

```json
[
  { "key": "A", "label": "名称：态势分析系统V1.0，领域：军事指挥，目的：明确功能边界", "recommended": true },
  { "key": "B", "label": "名称：应急态势分析平台，领域：应急管理，目的：指导开发", "recommended": false },
  { "key": "C", "label": "名称：通用态势分析工具，领域：地理空间决策，目的：统一需求理解", "recommended": false },
  { "key": "D", "label": "名称：XXX，领域：XXX，目的：XXX（自定义）", "recommended": false }
]
```

本轮验证中已确认：

- 选项均为对象，而非字符串
- `key` 非空
- `label` 非空
- 页面可按对象方式渲染，不再出现空按钮

### 6.3 多轮推进质量观察

虽然“空选项”问题已经修复，但 Dify workflow 的决策质量仍存在明显不足：

1. **重复追问问题**
   - 第 3 轮用户已补充“主要用户”和“主场景”，系统仍继续聚焦“编写目的”，说明它对多事实组合输入的吸收和焦点迁移不够稳定。

2. **章节投影过窄**
   - 持久化后的 `working_document` 只有 1 个 block。
   - 6 轮之后临时正文仍几乎都被投影到 `1 总则 / 编写目的`，没有形成更合理的章节分布。

3. **收束后草案不是真正成稿**
   - 第 6 轮虽然响应了“停止追问并输出草案”，但工作文档本质上仍是单块累计确认语句，而不是结构化需求规格说明草案。

4. **问题树与正文推进不同步**
   - `confirmed_facts` 有增长，但正文承载仍然偏单点堆积。
   - `open_questions` 到第 6 轮仍有 11 个，收束能力偏弱。

## 7. 数据摘录

### 7.1 会话级统计

- 会话 ID：`c585eed5-f98e-4ad2-9b7b-0c46d29b6b23`
- 总轮次：6
- 最终会话状态：`waiting_user`
- `working_document.blocks`：1

### 7.2 最终临时正文摘录

```text
围绕“1 总则 / 编写目的”，本轮已确认：用户希望创建一个态势分析系统。
围绕“1 总则 / 编写目的”，本轮已确认：软件名称为'军事态势分析系统'。
围绕“1 总则 / 编写目的”，本轮已确认：主要用户是参谋分析员。
围绕“1 总则 / 编写目的”，本轮已确认：数据接入采用混合模式：实时接入态势与告警，同时导入底图、任务区、DEM、部署点位和标注。
围绕“1 总则 / 编写目的”，本轮已确认：系统不做自动最优部署推荐。
围绕“1 总则 / 编写目的”，本轮已确认：先停止追问，基于已确认信息输出一版需求规格说明草案，并保留未闭合问题。
```

该摘录说明：

- 系统确实在持续写入
- 但尚未把不同事实投影到更合理的章节节点

## 8. 结论

### 8.1 已确认通过

1. `brainstorm-v1-dify-workflow` 可通过真实 Dify API 跑通。
2. 当前 worktree 已可持久化保存 P2 会话。
3. “快捷选项为空”问题已定位并修复。
4. 修复后，真实接口返回的快捷选项合同稳定正确。

### 8.2 尚未通过

以下项仍不能判定为“完全可验收通过”：

1. 长轮次决策焦点迁移质量
2. 多事实组合输入的稳定吸收
3. 章节级正文投影质量
4. 强制收束后的真实成稿能力

## 9. 整改建议

1. **先修 Dify workflow 输出口径**
   - 明确要求 workflow 输出章节级 `document_patch`，而不是反复将所有事实投影到 `1 总则 / 编写目的`。

2. **增强 next interaction planning**
   - 当用户补充了与当前主问题不同但有效的新事实时，workflow 应先决定：
     - 是继续追当前问题
     - 还是切换到更高价值问题
     - 还是把当前问题标为暂挂

3. **把“停止追问并成稿”做成显式分支**
   - 不能只把用户这句话当普通 confirmed fact 追加到正文中。
   - 应单独触发“草案编排 / gaps 保留 / 下一章节建议”分支。

4. **继续用本测试指南扩展 10~20 轮对比**
   - 当前 6 轮已经足以暴露结构性问题，但还不足以完成与真实 Codex brainstorming 的正式对照结论。

## 10. 附录

- 原始测试摘要：`/tmp/p2-dify-comprehensive-test.json`
- 测试指南：
  - `DOC/CODEX_DOC/06_测试文档/00_测试指南/01-P2-组织器插件与Codex-Brainstorming对照测试指南.md`
