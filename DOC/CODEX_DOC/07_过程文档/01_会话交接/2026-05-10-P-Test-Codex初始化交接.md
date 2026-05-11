# P-Test Codex 初始化交接

时间：2026-05-10

用途：本文件用于在开启新的 Codex 会话时直接拖入，帮助新会话快速恢复 P-Test 的设计边界、事实源、当前任务模式和禁止误解。

## 1. 新会话启动目标

如果用户在新会话中继续推进 P-Test，Codex 首先要理解：P-Test 当前不是一个在线智能测试平台，而是一套跨阶段测试分析与可视化产物机制。

当前 P-Test v1 的核心目标是：

1. 从测试计划中读取指标定义。
2. 从测试记录、交互证据、整改说明和最终成果中读取测试执行产物。
3. 由 Codex 或执行者完成分析、归一化和结构化统计。
4. 生成 `analysis.json`。
5. 使用固定 HTML/JS 模板稳定展示 `analysis.json`。

前三步属于 Codex 分析生成工作，第四步是结构化输出，第五步才是 P-Test HTML 展示。

## 2. 必读事实源

新会话开始后，优先阅读以下文件，不要只依赖本交接文件：

```text
DOC/CODEX_DOC/02_设计说明/P-Test_测试分析与可视化/P-Test-测试分析与可视化设计.md
DOC/CODEX_DOC/04_研制计划/02.06-WBS-P2-组织器多轮自测整改闭环-研制计划.md
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-10-P2-组织器多轮整改6轮总体测试分析报告.md
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-10-P2-组织器多轮整改交互证据附录/README.md
```

如果要继续生成 P2 组织器整改测试的可视化样例，还需要读取 6 轮交互证据附件：

```text
DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-10-P2-组织器多轮整改交互证据附录/
```

## 3. 当前设计结论

### 3.1 P-Test 是跨阶段能力

P-Test 不能写成 P2 专用工具。P2 组织器 6 轮整改测试只是第一个样例，后续 P3、P4 或其他阶段也可能复用。

设计文档放在：

```text
DOC/CODEX_DOC/02_设计说明/P-Test_测试分析与可视化/
```

如果进入代码实现，建议独立目录为：

```text
tools/ptest/
```

不要把 P-Test 实现写进 P2 前端页面或 P2 后端服务内部，除非用户明确要求做 P2 专用集成。

### 3.2 指标来自测试计划

P-Test 展示层不得自行发明指标。指标当前优先写在对应测试计划文档中。

以当前 P2 组织器多轮整改测试为例，指标定义已经补充在：

```text
DOC/CODEX_DOC/04_研制计划/02.06-WBS-P2-组织器多轮自测整改闭环-研制计划.md
```

该计划中定义了基础质量指标、当前批次可视化指标、可选主观评估指标和 P-Test 可视化使用方式。

后续如果多个计划稳定复用同一组指标，再考虑抽取独立 `metric_profile`。当前不要提前抽取。

### 3.3 HTML 只做稳定展示

HTML/JS 模板只读取 `analysis.json` 并展示，不做以下事情：

1. 不在线调用大模型。
2. 不在线调用 Dify。
3. 不读取数据库。
4. 不启动被测系统。
5. 不临时发明指标。
6. 不在浏览器中重新做复杂智能判断。
7. 不替代 Codex 或人工对测试现象的分析。

固定 HTML 模板的价值是：同一类测试的展示形态稳定，不因为每次 Codex 的分析措辞、数据漂移或运算漂移而变化。

## 4. 推荐执行模式

当用户要求“生成测试分析”“做 P-Test 可视化”“把这轮测试做成分析页面”时，按以下顺序执行：

### 4.1 读取指标定义

先找到本次测试对应的测试计划，读取其中的指标定义、指标口径、数据来源和展示要求。

如果测试计划没有定义指标，不要直接在页面里编指标。应先补测试计划或形成指标补充说明，让指标有据可依。

### 4.2 读取测试执行产物

再读取本次测试的实际产物：

1. 总体测试报告。
2. 单轮测试记录。
3. 交互证据附件。
4. 最终工作正文或最终草案。
5. 整改说明。
6. 运行日志、调用日志或错误响应。

### 4.3 生成 `analysis.json`

由 Codex 按计划指标完成统计和分析，生成结构化数据。

`analysis.json` 至少应包含：

1. `schema_version`
2. `title`
3. `plan_ref`
4. `generated_at`
5. `analysis_method`
6. `test_objects`
7. `iterations`
8. `metrics`
9. `series`
10. `timeline`
11. `evidence_index`
12. `conclusions`

主观指标可以存在，但必须有证据入口和判定说明。

### 4.4 使用固定 HTML 模板展示

HTML 页面按指标组织，不按组织器单独堆大章节。

推荐页面结构：

1. 批次概览：少量背景信息。
2. 指标趋势：每个指标一张图，横轴为轮次，同图叠加多个被测对象。
3. 整改时间线：简述每轮主要问题、整改和结论。
4. 证据下钻：链接到测试记录、交互附件、最终成果和日志。

## 5. 当前 P2 样例指标

当前 P2 6 轮组织器整改测试可优先展示以下指标：

1. `completed_turns`
2. `error_count`
3. `draft_delivery_success`
4. `final_working_document_text_chars`
5. `final_working_document_block_count`
6. `confirmed_facts_count`
7. `confirmed_decisions_count`
8. `open_questions_remaining`
9. `tentative_assumptions_count`
10. `rejected_directions_count`
11. `chapter_projection_count`
12. `examiner_action_distribution`
13. `observability_log_count`

可选主观指标：

1. `topic_depth_score`
2. `decision_progress_score`
3. `draft_richness_score`
4. `next_question_quality_score`

这些指标的含义、来源、口径、推荐展示和局限以 P2 研制计划第 5 节为准。

## 6. 禁止误解

新会话必须避免以下误解：

1. 不要把 P-Test 做成 P2 专用页面。
2. 不要把 P-Test v1 做成在线平台、后端 API 或数据库系统。
3. 不要让 HTML 页面执行智能判断。
4. 不要在展示代码里写死 P2 组织器业务规则。
5. 不要把“正文有效字数”“开放问题数”等指标直接等同于最终质量。
6. 不要把测试报告替代为图表页面；原始证据仍然要保留。
7. 不要把用户要求的“智能化”理解为页面智能化；当前智能化是 Codex 读取计划和证据后生成 `analysis.json`。

## 7. 可能的下一步任务

后续用户可能会要求以下任一工作：

1. 基于 P2 6 轮测试证据生成第一份 `analysis.json`。
2. 创建 `tools/ptest/` 的静态 HTML 报告模板。
3. 用 P2 6 轮测试作为样例生成一个可打开的 HTML 报告。
4. 补充 `analysis.schema.json`。
5. 将 P-Test 从 v1 手工/Codex 分析模式升级为本地 CLI 模式。

如果用户只要求“继续设计”，不要直接编码。先补充设计文档或测试计划。

如果用户要求“实现”，优先实现最小闭环：

```text
analysis.json 样例
  -> 固定 HTML 模板读取
  -> 指标趋势展示
  -> 整改时间线展示
  -> 证据链接展示
```

## 8. 工作树与提交提醒

当前相关设计提交为：

```text
78ae3e1 docs: 设计 P-Test 测试分析可视化
```

继续工作前必须先检查：

```bash
pwd
git status --short
git log --oneline -5
```

当前用户此前多次要求 P2 相关工作在 P2 worktree 中进行。若新会话不在正确 worktree，应先确认工作目录，不要直接在主分支或其他 worktree 修改。

当前 P2 worktree 参考路径：

```text
/home/wgw/CodexProject/CodeFactoryV2/.worktrees/p2-requirement-analysis-system
```

但新会话不能只凭本路径假设环境正确，必须实际检查。

## 9. 验证要求

文档类修改至少执行：

```bash
git diff --check
```

如果实现 HTML 报告模板，至少执行：

1. 打开生成的 HTML 或使用本地静态服务查看。
2. 检查 `analysis.json` 能被加载。
3. 检查每个指标图表均来自 `analysis.json`。
4. 检查证据链接可达或路径清晰。
5. 检查页面没有写死 P2 专有判断。

提交前只暂存本轮相关文件，不要把工作树中无关历史改动带入提交。
