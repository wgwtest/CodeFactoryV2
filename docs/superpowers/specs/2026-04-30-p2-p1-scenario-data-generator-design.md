# P2/P1 场景数据发生器与 Brainstorming 接入设计

**日期：** 2026-04-30  
**适用范围：** `P2` 需求分析系统，兼顾 `P1 -> P2` 输入模拟  
**首版目标：** B. 支撑完整 P2 闭环：从模拟 P1 发布态知识进入 P2，经问答/表单补齐、缺口检查，冻结为 P3 可消费包。

## 1. 背景

`P2` 专家需求规格编写工作台已经形成首版可用界面：左侧问答/表单输入，右侧持续生成标准需求规格说明，支持模板选择、缺口检查和冻结。下一阶段的关键不再是主界面布局，而是为这个工作台提供稳定、可信、可复现的数据来源。

当前系统存在三个事实：

1. 需求规格模板本身可以视为真实对象。`81433`、`82259` 等模板是规格正文的权威骨架，不需要造假。
2. `P1` 知识读侧接口是真接口，但当前本地 worktree 不一定具备对应的发布态知识 JSON。缺少真实知识文件时，`P1` 接口会无法稳定支撑 P2 演示和验收。
3. `P2` 问答当前是规则桩：能响应“可以 / 更正式 / 加超时 / 重拟”等短输入，但还不是真正的大模型 brainstorming 编排。

因此需要建设一套面向 P2 的场景数据发生器：既能在没有真实 P1 数据时提供假知识，又能保持数据形态接近未来真实 P1 发布态出口，并为后续 LLM 接入保留同一套结构化 contract。

## 2. 设计目标

首版发生器必须满足以下目标：

- 能一键生成一个完整业务场景，并注入到 P2 工作台。
- 能生成模拟 P1 发布态知识，而不是零散的随机字段。
- 能生成 P2 authoring 文档、表单字段、问答脚本和预期条款。
- 能完成缺口检查并冻结为 P3 可消费结构化包。
- 能在无大模型、无真实 P1 数据时稳定运行和测试。
- 后续接入真实 P1 或 LLM 时，不改 P2 主流程，只替换数据源或决策引擎。

首版不做以下事情：

- 不把 P6 门户状态联动纳入本轮闭环。
- 不做随机数据生成。首版采用确定性场景包，保证验收和测试可复现。
- 不让 LLM 直接自由改写数据库正文。LLM 只能返回受 schema 约束的补丁，由后端校验后写入。
- 不把 P3/P4/P5 的实现细节提前混入 P2 需求规格正文。

## 3. 真数据、假数据、可替换数据边界

| 数据对象 | 首版来源 | 性质 | 说明 |
| --- | --- | --- | --- |
| 规格模板 `81433` / `82259` | 本地内置模板或配置台 | 真 | 作为标准规格正文骨架，不造假。 |
| P2 工作台页面与 API | 现有实现 | 真 | `RequirementAuthoringPage`、`RequirementAuthoringService` 继续作为主流程。 |
| P2 配置台 | 现有实现 | 真 | 管理模板、表单、字段映射、问答策略、缺口规则。 |
| P1 发布态知识 | 场景包生成 | 假但按真形态造 | 生成 `documents/entities/processes/events/relations/evidence/publication`。 |
| P1 -> P2 知识出口 | 场景包投影 | 假但按接口契约造 | 提供 P2 可引用的领域对象、流程、规则、证据。 |
| 专家问答输入 | 场景包脚本 + 用户输入 | 假/真混合 | 发生器提供脚本，用户仍可真实交互。 |
| Brainstorming 决策 | 首版 `mock_rule` | 假实现 | 规则型、确定性，后续可替换为 LLM。 |
| LLM 输出 | 后续 `llm_assisted` | 真推理但受限 | 走同一结构化 response contract。 |
| P2 冻结包 | P2 主流程生成 | 真 | 来源可以是假知识，但冻结包结构和检查逻辑必须真实。 |

## 4. 总体架构

首版新增一个“P2 场景数据发生器”能力，建议拆为五个模块：

1. `Scenario Pack Registry`
   管理可选择的确定性场景包。每个场景包是一个可版本化的业务主题。

2. `P1 Mock Knowledge Projector`
   把场景包中的业务知识种子投影为模拟 P1 发布态知识对象，使现有 P1 读侧接口或 P2 知识选择逻辑能消费。

3. `P2 Authoring Seed Injector`
   基于场景包创建 P2 authoring 文档，并预填部分字段、知识绑定、问答策略和初始对话。

4. `Brainstorming Orchestrator`
   首版使用 `mock_rule` 引擎，根据当前缺口、用户输入和场景脚本生成字段补丁、条款补丁和下一轮提示。后续可以切换到 `llm_assisted`。

5. `Freeze Path Verifier`
   对场景生成的 P2 文档执行缺口检查和冻结，确认输出的 `frozen_package.p3_consumable = true`，并校验结构化包可被 P3 消费。

数据流如下：

```text
Scenario Pack
  -> P1 Mock Knowledge Projector
  -> P2 Authoring Seed Injector
  -> P2 Workbench
  -> Brainstorming Orchestrator
  -> Gap Check
  -> Freeze Package
  -> P3 Consumable Structured Spec
```

## 5. 场景包模型

场景包是发生器的核心，不是随机模板。建议采用后端 Python fixture 或 JSON/YAML 形式存放，字段稳定后可迁移到数据库配置。

一个场景包包含：

```json
{
  "scenario_id": "airspace-collaboration",
  "scenario_name": "空域协同规划软件",
  "version": "1.0.0",
  "domain": "空域协同规划",
  "default_template_code": "81433",
  "p1_knowledge_seed": {},
  "p2_authoring_seed": {},
  "conversation_seed": {},
  "expected_output": {},
  "p3_contract_seed": {}
}
```

### 5.1 `p1_knowledge_seed`

用于生成模拟 P1 发布态知识。首版必须包含：

- `archive_id`
- `archive_name`
- `publication`
- `documents`
- `entities`
- `processes`
- `events`
- `relations`
- `evidence`

示例语义：

- 文档：空域协同规划业务规则、任务规划流程、异常处置要求。
- 实体：协同任务、空域申请、冲突窗口、规划方案、审批记录。
- 流程：任务创建、冲突校核、方案会签、结果发布、异常回退。
- 规则：超时提醒、冲突不可发布、关键节点留痕。
- 证据：每个知识项要能回溯到模拟文档和片段。

### 5.2 `p2_authoring_seed`

用于初始化 P2 文档。首版字段包括：

- `title`
- `template_code`
- `layout_ratio`
- `archive_ids`
- `initial_fields`
- `knowledge_bindings`
- `gap_rules_override`
- `questionnaire_policy_override`

其中 `initial_fields` 不应一次性填满全部字段。为了体现问答补齐价值，首版建议预填：

- `application_name`
- `domain_scope`
- `target_users`
- `main_process`

保留待问答补齐：

- `normal_flow`
- `exception_flow`
- `non_functional`
- `acceptance_criteria`

### 5.3 `conversation_seed`

用于驱动 deterministic brainstorming。字段包括：

- `assistant_opening`
- `scripted_turns`
- `quick_inputs`
- `choice_sets`
- `field_patch_rules`
- `clause_patch_rules`

脚本示例：

- 用户输入“可以”：系统补齐正常流程草稿。
- 用户输入“加超时”：系统补齐异常流程与超时提醒。
- 用户输入“更正式”：系统把当前条款转为标准规格表达。
- 用户输入“A/B/C”：系统按当前问题的选项选择修补方向。
- 用户输入自由句：系统将其归入当前最相关条款，并标注待确认。

### 5.4 `expected_output`

用于测试和验收。字段包括：

- 必须生成的章节标题。
- 必须出现的核心条款内容片段。
- 必须通过的缺口字段。
- 冻结包中必须出现的结构化路径。

该部分不展示给最终专家用户，主要用于自动化验证。

## 6. Brainstorming Contract

无论使用规则引擎还是大模型，P2 后端只接受一种结构化结果：

```json
{
  "assistant_message": "我已补入超时提醒，并保持补偿策略克制。",
  "field_patches": {
    "exception_flow": "系统应在规划会签超时后提醒责任人，并允许人工确认后继续。"
  },
  "clause_patches": [
    {
      "clause_id": "REQ-3.3",
      "content": "系统应支持规划会签超时提醒..."
    }
  ],
  "next_questions": [
    {
      "question_id": "q-acceptance-criteria",
      "prompt": "是否按可追溯、可校核、可冻结作为验收重点继续？",
      "suggested_replies": ["可以", "更严格", "重拟"]
    }
  ],
  "source_refs": [
    {
      "archive_id": "mock-airspace",
      "item_id": "process-conflict-check",
      "evidence_id": "ev-conflict-001"
    }
  ],
  "confidence": 0.86,
  "blocking_risks": []
}
```

后端写入规则：

- `field_patches` 只能写入当前模板允许的字段。
- `clause_patches` 只能写入当前模板存在的条款。
- 任何无法映射的自由内容进入批注，不直接覆盖标准字段。
- `source_refs` 必须能对应 P1 mock 或真实 P1 知识项。
- 如果 `confidence` 低于阈值，系统只生成建议，不自动改正文。
- 冻结前仍以缺口检查为准，大模型不能绕过缺口规则。

## 7. LLM 接入设计

项目已有 `app.integrations.llm` 和 `KW_LLM_*` / `KW_OPENAI_*` 配置能力。P2 不需要另起一套供应商配置，应该复用现有 OpenAI-compatible 适配方式。

推荐新增 `P2BrainstormingService`，支持三种模式：

| 模式 | 行为 | 用途 |
| --- | --- | --- |
| `mock_rule` | 使用场景包规则生成结构化补丁 | 默认模式，测试和离线演示 |
| `llm_assisted` | 调用结构化 LLM，返回同一 contract | 真正 brainstorming |
| `disabled` | 只记录用户输入，不自动修补 | 故障降级 |

LLM Prompt 的职责：

- 读取当前标准规格模板、已填字段、当前文档正文、P1 知识引用、对话历史。
- 判断当前最关键缺口。
- 生成一段面向专家的下一轮回答或问题。
- 输出字段补丁和条款补丁。
- 避免输出实现细节、组件资产、工具匹配结果。

LLM Prompt 的硬约束：

- 只返回 JSON。
- 不得新增模板不存在的条款编号。
- 不得把 P4/P5 工具、构建、运行装配内容写入 P2 需求正文。
- 不确定内容必须进入 `blocking_risks` 或 `next_questions`。
- 来源证据不足时，允许生成“待确认”建议，但不能伪造来源引用。

## 8. API 与页面入口

首版建议新增后端接口：

- `GET /api/requirement-authoring/scenarios`
  返回可用场景包列表。

- `POST /api/requirement-authoring/scenarios/{scenario_id}/materialize`
  生成 P1 mock 知识源并创建 P2 authoring 文档。

- `POST /api/requirement-authoring/documents/{document_id}/scenario-turns`
  使用当前场景包的 deterministic brainstorming 规则推进一轮问答。

- `POST /api/requirement-authoring/documents/{document_id}/auto-complete`
  按场景包把剩余字段补齐到可冻结状态，用于验收和演示。

- `POST /api/requirement-authoring/documents/{document_id}/freeze`
  复用现有冻结接口，不为模拟链路开后门。

前端入口建议放在 P2 工作台，而不是另建重页面：

- 顶部设置 Popover 增加“场景数据”入口。
- 选择场景后点击“生成模拟闭环”。
- 左侧问答区显示该场景的脚本上下文。
- 右侧标准文档仍由正式 P2 document 渲染。
- 页面明显标记“模拟 P1 知识源”，避免和真实知识混淆。

`/xx-p2-sim` 可以保留为旧联调入口，但它不应承担新发生器主入口。新发生器面向正式 P2 authoring 工作台，目标是证明正式工作台可闭环。

## 9. 数据持久化策略

首版建议：

- 场景包定义放代码 fixture，保证版本可控。
- 物化后的 mock P1 archive 写入 `.data/knowledge_output/{archive_id}-knowledge.json` 或等价的临时发布态文件。
- P2 authoring 文档继续写数据库。
- 冻结包继续写 `RequirementAuthoringDocument.frozen_package`。

这样做的好处：

- 不污染真实 P1 抽取链。
- 可以复用现有 P1 知识读侧接口。
- 可以让 P2 的知识绑定看起来接近真实用户选择。
- 自动化测试可以用临时目录隔离 `.data`。

## 10. 验收路径

首版必须通过以下验收：

1. 打开 P2 工作台。
2. 从场景数据入口选择“空域协同规划软件”。
3. 系统创建模拟 P1 发布态知识源。
4. 系统创建 P2 authoring 文档，并绑定该模拟知识源。
5. 右侧文档出现标准规格说明草稿。
6. 左侧问答输入“可以”“加超时”“更正式”等短指令后，右侧条款持续更新。
7. 表单模式能看到同一批字段状态。
8. 缺口检查能定位剩余缺口。
9. 自动补齐或人工短答后，缺口检查通过。
10. 冻结版本成功，`frozen_package.p3_consumable = true`。
11. 冻结包中的 `structured_spec` 包含应用、流程、规则、指标和非功能约束。
12. 测试证明不依赖外部 LLM 也能完成闭环。

## 11. 测试策略

后端测试：

- 场景列表返回稳定场景。
- 物化场景会创建 mock P1 archive。
- 物化场景会创建 P2 authoring document。
- 问答推进返回结构化补丁，并更新文档。
- 不允许写入模板不存在的字段或条款。
- 缺口检查和冻结走现有正式逻辑。
- 冻结包可被 P3 结构化读取。

前端测试：

- P2 工作台能打开场景入口。
- 选择场景后创建文档。
- 问答短指令会更新右侧标准文档。
- 表单和问答共享同一 semantic state。
- 缺口检查、自动补齐、冻结流程可达。

LLM 接入测试：

- 默认测试不要求真实 LLM key。
- 使用 fake LLM client 校验 JSON contract。
- LLM 返回非法字段时，后端拒绝写入。
- LLM 低置信度时，只生成建议和待确认批注。

## 12. 分阶段实施建议

第一阶段：确定性发生器闭环

- 新增场景包 registry。
- 新增 P1 mock knowledge projector。
- 新增 materialize 接口。
- P2 工作台接入场景选择。
- 使用 `mock_rule` 推进问答。
- 完成冻结验收。

第二阶段：LLM-assisted brainstorming

- 新增 `P2BrainstormingService`。
- 复用现有 LLM 配置。
- 增加结构化 JSON 输出校验。
- 增加降级和失败回退。

第三阶段：真实 P1 替换

- 支持 `mock_p1` 与 `live_p1` 源模式。
- 当真实 P1 archive 可用时，跳过 mock projector。
- 保持 P2 authoring seed 和 brainstorming contract 不变。

## 13. 设计结论

首版应建设的是“场景包驱动的完整 P2 闭环发生器”，而不是孤立的假表单或随机 mock 数据。

它的关键价值是：

- 让 P2 工作台在没有真实 P1 数据和没有 LLM 的情况下可验收。
- 让假数据按未来真实 P1 发布态出口建模，降低后续替换成本。
- 让 brainstorming 从一开始就被约束为结构化补丁，而不是不可控的自由聊天。
- 让 P2 冻结包继续走真实检查和真实冻结逻辑，保证 P3 消费路径可信。
