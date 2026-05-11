# P-Test analysis.json 数据规范

> 归档说明：本文件作为 `P-Test` 测试分析数据集的跨阶段共享规范。凡涉及 P1、P2、P3、P4、P5、P6 或后续阶段的测试分析可视化，若需要交给 P-Test HTML 模板展示，均应输出符合本规范的 `analysis.json`。
>
> 维护规则：新增或调整 P-Test 展示能力时，必须先判断是否影响本共享数据契约。若影响根字段、指标字段、序列点、证据索引或展示枚举，必须先回写本文件，再同步更新 `tools/ptest/schemas/analysis.schema.json`、P-Test 设计说明和相关测试计划。

**日期：** 2026-05-11

**适用范围：**

- P-Test 测试分析与可视化
- P1 ~ P6 各阶段测试计划、机测记录、人测记录和验收结论
- 由 Codex 或人工辅助生成的测试分析数据集
- `tools/ptest/` 静态 HTML 报告模板

## 1. 规范定位

本规范回答的是“任意阶段的测试分析结果要交给 P-Test 展示时，`analysis.json` 最小必须长什么样、字段语义如何统一、哪些信息必须可追溯”。

固定边界如下：

- `analysis.json` 是 P-Test 展示层的唯一数据输入。
- 指标定义必须来自对应测试计划、测试指南或指标补充说明。
- Codex 或人工辅助分析阶段负责提取、归一化、评分和证据化判断。
- P-Test HTML 模板只负责渲染 `analysis.json`，不得在线调用模型、读取数据库、启动被测系统或临时发明指标。
- 各阶段可以在 `analysis.json` 中保留阶段差异字段，但不得改变本规范公共字段含义。

## 2. 生成链路

标准链路如下：

```text
测试计划中的指标定义
  -> 测试记录、交互证据、日志、整改说明、最终成果
  -> Codex 或人工辅助分析
  -> analysis.json
  -> P-Test HTML 模板展示
```

若某次测试没有明确指标定义，不应直接生成正式 `analysis.json`。应先补充测试计划或形成指标补充说明，再进入 P-Test 展示链路。

## 3. 根对象 AnalysisDataset

`analysis.json` 根对象为 `AnalysisDataset`。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `schema_version` | 是 | string | 固定为 `ptest.analysis.v1` |
| `title` | 是 | string | 本次测试分析标题 |
| `plan_ref` | 是 | string | 指标来源测试计划或补充说明路径 |
| `generated_at` | 是 | string | 分析数据生成时间，推荐 ISO 8601 |
| `analysis_method` | 是 | object | 分析执行方式、执行者和说明 |
| `test_objects` | 是 | array | 被测对象列表 |
| `iterations` | 是 | array | 测试轮次或批次列表 |
| `metrics` | 是 | array | 指标定义列表 |
| `series` | 是 | array | 指标序列数据 |
| `timeline` | 是 | array | 测试、问题、整改和结论时间线 |
| `evidence_index` | 是 | array | 原始证据入口索引 |
| `conclusions` | 是 | array | 总体结论摘要 |

最小结构示例：

```json
{
  "schema_version": "ptest.analysis.v1",
  "title": "P2 组织器多轮整改测试分析",
  "plan_ref": "DOC/CODEX_DOC/04_研制计划/02.06-WBS-P2-组织器多轮自测整改闭环-研制计划.md",
  "generated_at": "2026-05-11T10:00:00+08:00",
  "analysis_method": {
    "executor": "codex",
    "mode": "plan_driven_manual_assisted",
    "notes": []
  },
  "test_objects": [],
  "iterations": [],
  "metrics": [],
  "series": [],
  "timeline": [],
  "evidence_index": [],
  "conclusions": []
}
```

## 4. analysis_method

`analysis_method` 说明本次数据如何产生。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `executor` | 是 | string | 执行者，例如 `codex`、`human`、`script` |
| `mode` | 是 | string | 分析模式，例如 `plan_driven_manual_assisted` |
| `notes` | 是 | array | 数据口径、限制、未覆盖证据等说明 |

推荐 `mode`：

| 枚举 | 含义 |
| --- | --- |
| `plan_driven_manual_assisted` | 按测试计划指标，由 Codex 或人工辅助读取证据后生成 |
| `plan_driven_script_assisted` | 按测试计划指标，由脚本提取基础数据并人工复核 |
| `sample_only` | 样例数据，只用于模板联调，不作为正式测试结论 |

## 5. test_objects

`test_objects` 表示被测对象。一个分析数据集可以包含一个或多个被测对象。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `object_id` | 是 | string | 被测对象稳定标识 |
| `display_name` | 是 | string | 展示名称 |
| `type` | 是 | string | 对象类型，例如 `p2_orchestrator`、`api_service`、`frontend_page` |

约束：

- 同一 `analysis.json` 内 `object_id` 必须唯一。
- `series[].object_id` 必须引用 `test_objects[].object_id`。
- 对象类型用于解释对象身份，不用于让 P-Test 模板写业务判断分支。

## 6. iterations

`iterations` 表示测试轮次、批次或整改闭环节点。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `iteration` | 是 | integer | 轮次编号，从 1 开始 |
| `scope` | 是 | string | 本轮测试范围 |
| `changes_summary` | 是 | string | 本轮整改或执行摘要 |
| `evidence_links` | 是 | array | 本轮证据入口 |
| `started_at` | 否 | string | 本轮开始时间 |
| `ended_at` | 否 | string | 本轮结束时间 |

约束：

- 同一数据集内 `iteration` 应唯一。
- `series[].points[].iteration` 必须引用 `iterations[].iteration`。
- 若不是整改轮次，也应使用连续编号表达批次顺序，并在 `scope` 中说明真实含义。

## 7. metrics

`metrics` 是 P-Test 的核心定义区。每个被展示指标必须在这里声明。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `metric_id` | 是 | string | 指标稳定标识 |
| `name` | 是 | string | 指标显示名称 |
| `type` | 是 | string | 指标类型 |
| `unit` | 是 | string | 单位，无单位时填空字符串 |
| `source` | 是 | string | 数据来源 |
| `calculation` | 是 | string | 计算或判定口径 |
| `visualization` | 是 | string | 推荐展示形式 |
| `limitations` | 是 | string | 指标局限 |
| `purpose` | 否 | string | 指标回答的问题 |

### 7.1 type 枚举

| 枚举 | 含义 |
| --- | --- |
| `count` | 计数型指标 |
| `ratio` | 比率或百分比 |
| `boolean` | 是/否状态 |
| `score` | 评分型指标 |
| `category` | 分类分布 |
| `text` | 文本型说明 |

### 7.2 visualization 枚举

| 枚举 | 推荐展示 | 适用指标 |
| --- | --- | --- |
| `trend` | 折线趋势图 | `count`、`ratio`、`score` |
| `bar` | 柱状对比图 | 错误数、批次对比等 |
| `status_matrix` | 状态矩阵 | `boolean` |
| `stacked_bar` | 分布图或堆叠条 | `category` |
| `table` | 数据表 | 文本、混合值或不适合图形化的指标 |

模板可以基于 `type` 和 `visualization` 选择实际图表，但不得改变指标语义。

## 8. series

`series` 承载指标在不同被测对象、不同轮次上的取值。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `metric_id` | 是 | string | 引用 `metrics[].metric_id` |
| `object_id` | 是 | string | 引用 `test_objects[].object_id` |
| `points` | 是 | array | 按轮次排列的数据点 |

`points` 字段如下：

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `iteration` | 是 | integer | 引用 `iterations[].iteration` |
| `value` | 是 | number / boolean / string / object / null | 指标值 |
| `note` | 否 | string | 该点的口径说明、异常说明或人工判定说明 |
| `evidence_refs` | 否 | array | 引用 `evidence_index[].evidence_id` 或证据路径 |

约束：

- 一个 `metric_id + object_id` 推荐只有一条 series。
- 缺失值使用 `null`，不要用 `0` 代替未知。
- 人工评分、主观判断或证据不足的数据点必须补充 `note` 或 `evidence_refs`。
- `category` 指标的 `value` 推荐使用对象，例如 `{"answer": 15, "small_guidance": 3}`。

## 9. timeline

`timeline` 用于解释每轮测试、问题、整改和结论，不能替代指标序列。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `iteration` | 是 | integer | 对应轮次 |
| `title` | 是 | string | 时间线标题 |
| `problem` | 是 | string | 本轮主要问题 |
| `change` | 是 | string | 本轮主要整改或测试变化 |
| `result` | 是 | string | 本轮结果或结论 |
| `evidence_refs` | 否 | array | 本轮证据引用 |

约束：

- 时间线只做辅助解释。
- 不应把完整测试报告复制进 `timeline`。
- 原始证据必须保留在正式测试文档或附件中。

## 10. evidence_index

`evidence_index` 是 P-Test 下钻入口。

| 字段 | 必填 | 类型 | 含义 |
| --- | --- | --- | --- |
| `label` | 是 | string | 证据显示名称 |
| `path` | 是 | string | 证据路径或 URL |
| `type` | 是 | string | 证据类型 |
| `evidence_id` | 否 | string | 证据稳定标识，供 series/timeline 引用 |
| `iteration` | 否 | integer | 所属轮次 |
| `object_id` | 否 | string | 所属被测对象 |

推荐 `type`：

| 枚举 | 含义 |
| --- | --- |
| `plan` | 测试计划或指标定义 |
| `test_record` | 单轮或总体测试记录 |
| `interaction_appendix` | 交互证据附件 |
| `rectification_note` | 问题与整改说明 |
| `final_artifact` | 最终成果或草案 |
| `log` | 运行日志、调用日志、错误响应 |
| `screenshot` | 截图 |
| `design` | 设计说明 |

## 11. conclusions

`conclusions` 用于承载总体结论摘要。

约束：

- 结论应可追溯到 `metrics`、`series`、`timeline` 或 `evidence_index`。
- 不应把指标值直接等同于最终质量。
- 若存在外部服务故障、样例数据、缺失证据或不可比数据，必须在结论或 `analysis_method.notes` 中说明。

## 12. 分阶段测试编写要求

P1 ~ P6 或后续阶段编写测试计划时，若计划进入 P-Test 展示链路，应满足：

1. 测试计划中明确列出指标 ID、名称、类型、单位、来源、口径、展示形式和局限。
2. 测试记录中保留能够计算或判定指标的原始字段。
3. 交互附件、日志、截图、最终成果等证据必须有稳定路径。
4. 主观指标必须有评分口径、证据入口和判定说明。
5. 生成 `analysis.json` 时不得新增未在计划或补充说明中定义的正式指标。
6. P-Test HTML 模板不得为某个阶段写专用指标解释逻辑。

## 13. 与工程 schema 的关系

本文件是人工可读规范。机器可校验版本位于：

```text
tools/ptest/schemas/analysis.schema.json
```

二者维护关系：

- 本文件定义字段语义、边界和生成要求。
- JSON Schema 校验必填字段、类型、枚举和基本引用关系。
- 若两者冲突，以本规范为准，并应立即修正 schema。

## 14. 版本维护

当前 schema 版本固定为：

```text
ptest.analysis.v1
```

兼容性规则：

- 新增可选字段不改变 `schema_version`。
- 改变必填字段、字段语义或枚举含义时，必须升级 schema 版本。
- 旧版本分析数据需要继续可读时，模板应提供兼容适配或明确拒绝并给出错误信息。
