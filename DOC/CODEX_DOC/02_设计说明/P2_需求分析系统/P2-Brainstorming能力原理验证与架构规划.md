# P2 Brainstorming 能力原理验证与架构规划

**日期：** 2026-05-01

**对应节点：**
- `P2` 需求分析系统
- `P2.1` 专家需求规格编写工作台
- `P2 Brainstorming Service` 原理验证能力

**关联正式文档：**
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-可配置需求规格说明编写系统设计.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求规格编写系统原型设计.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-XX-P1-Sim上游知识服务模拟器设计.md`

## 1. 设计背景

`P2` 当前已经形成面向专家的需求规格编写工作台原型，核心形态是：

- 左侧 `问答模式 / 表单模式` 同源输入
- 右侧标准需求规格说明正文
- 文档模板、领域知识、草稿保存、缺口检查和冻结版本

但现有实现仍主要停留在前端业务层和少量草稿保存服务。真正支撑 `P2` 的后台需求分析能力尚未成形，尤其是问答模式所需的引导式分析、持续追问、轻量选项、正文自动修补、注记生成和知识上下文调度，不能继续仅作为页面逻辑处理。

因此，`Brainstorming` 应被定义为 `P2` 的核心后台能力之一，而不是某个按钮或页面局部交互。

## 2. 核心结论

本阶段采用“先独立原理验证，后并入正式工作台”的策略。

原因如下：

- `Brainstorming` 会影响 `P2` 的服务边界、数据模型、模型调用方式和文档生成协议。
- 直接改造当前专家工作台容易把模型调用、需求分析过程和正式文档编辑器过早耦合。
- 独立验证页可以更快暴露模型输出稳定性、结构化协议、会话状态和知识注入问题。
- 验证完成后再接入正式工作台，可以避免破坏当前已经可用的需求规格编写界面。

本阶段不把 `Brainstorming` 直接嵌入当前 `RequirementAuthoringPage`，而是先建立独立的 `P2 Brainstorming Lab`。

## 3. Brainstorming 的能力定义

`Brainstorming` 不是展示模型内部思维链，也不是传统问卷。

它是 `P2` 内部的需求分析会话引擎，负责把用户的自然输入、短答、选择、方向判断、领域知识和规格模板，持续转化为：

- 面向用户的下一轮自然语言回应
- 轻量可选项
- 下一步追问
- 已确认事实
- 待确认问题
- 需求规格草稿片段
- 标准正文结构化修补建议
- 注记、假设、风险和来源说明

产品上应展示的是“可审计的分析过程”，而不是模型底层推理链。

### 3.1 直观解释

可以把 `Brainstorming Service` 理解为一个“有记忆、有目标、有工具的需求分析主持人”。

它本身不是大模型。大模型只是它调用的一个生成能力。

它在产品中的职责更接近以下角色组合：

- 需求分析会议主持人
- 会议纪要员
- 标准规格文档助理
- 知识库检索员
- 下一步问题规划器

每轮交互中，它都要完成三件事：

1. 理解用户刚刚表达了什么。
2. 判断当前需求规格还缺什么。
3. 给出下一步推进和文档修补建议。

因此，`Brainstorming Service` 不是“聊天机器人”，而是围绕“会话状态”运行的需求分析循环。模型调用只是循环中的一个环节。

### 3.2 基本工作循环

一次 Brainstorming 不是简单的“用户发一句，模型回一句”。

每一轮都应按以下循环运行：

```text
用户输入
  -> Brainstorming Service 读取当前会话状态
  -> Brainstorming Service 读取模板、知识包和历史消息
  -> Brainstorming Service 组装模型上下文
  -> Model Provider 调用 DeepSeek / OpenAI / Mock
  -> Brainstorming Service 解析结构化输出
  -> Brainstorming Service 校验输出是否合法
  -> Brainstorming Service 更新会话状态
  -> 前端展示本轮结果
  -> 等待下一轮用户输入
```

用户输入可以是一段自然语言，也可以只是 `A`、`继续`、`可以`、`重拟` 等短指令。

服务需要结合上一轮问题、当前已确认事实、待确认项、模板章节和知识上下文，判断用户输入的含义，而不是孤立处理一句话。

### 3.3 服务依赖

最小可行的 `Brainstorming Service` 依赖如下：

```text
Brainstorming Service
  - 会话存储
  - 模型 Provider
  - 模板读取
  - 知识包读取
  - 输出结构校验
  - 调用日志
```

它不依赖 `Codex` 运行环境，也不依赖某个固定大模型厂商。

`Codex` 对本系统的价值是提供交互范式参考，即持续理解上下文、主动分解问题、让用户做轻量判断、再继续推进。这个范式在 `P2` 中应由后台服务和前端页面共同实现。

### 3.4 为什么必须是后台服务

`Brainstorming` 不应直接做成纯前端逻辑。

原因如下：

- API Key 不能暴露在浏览器侧。
- 会话状态需要稳定保存和恢复。
- 模型提示词和结构化输出协议需要统一管理。
- 模型返回不能完全信任，必须经过结构校验和业务校验。
- 后续需要接入 `P1` 知识服务、模板服务、草稿服务和调用日志。
- 多文档、多会话、多用户和后续审计都依赖后台状态。

前端负责呈现交互体验，后台服务负责主持循环、调用模型、维护状态和产出结构化结果。

### 3.5 模型在系统中的角色

模型不是 `P2` 的系统本体。

模型在循环中承担“候选内容生成器”的职责。`Brainstorming Service` 会告诉模型：

- 当前你是 `P2` 需求分析助手。
- 当前目标是帮助专家形成标准需求规格说明。
- 当前模板、知识包、会话状态是什么。
- 你必须返回指定 JSON 字段。
- 你不能把实现细节提前混入需求规格。

模型返回后，服务需要继续校验：

- JSON 是否合法。
- 字段是否齐全。
- `document_patch` 是否指向合理章节。
- `quick_options` 是否过多或过重。
- 是否生成了不该出现的实现细节。
- 是否存在空内容、重复内容或与已确认事实冲突的内容。

因此，模型负责生成，`Brainstorming Service` 负责组织、约束、校验和落状态。

## 4. 架构定位

### 4.1 P2 后台能力分层

`P2` 后续应按以下结构规划：

```text
P2 前端工作台
  - 专家需求规格编写工作台
  - P2 Brainstorming Lab
  - 配置与模板管理台

P2 应用服务层
  - Requirement Authoring Service
  - Brainstorming Service
  - Template Service
  - Knowledge Binding Service
  - Document Draft Service

P2 适配层
  - Model Provider Adapter
    - OpenAI
    - DeepSeek
    - Mock Provider
  - P1 Knowledge Adapter
    - XX-P1-Sim
    - 未来真实 P1

P2 存储层
  - Brainstorming 会话
  - 草稿文档
  - 模板配置
  - 知识绑定
  - 模型调用日志
```

### 4.2 与正式需求规格编辑器的关系

`Brainstorming Service` 不直接等同于正式需求规格编辑器。

二者关系如下：

- `Brainstorming Service` 负责分析、追问、建议和生成结构化修补意图。
- `Requirement Authoring Service` 负责维护正式草稿、模板实例、正文状态、保存、检查和冻结。
- 专家工作台是二者的前端组合视图。
- `P2 Brainstorming Lab` 只消费 `Brainstorming Service`，用于验证原理，不写入正式需求规格文档。

## 5. P2 Brainstorming Lab

### 5.1 页面目的

`P2 Brainstorming Lab` 是独立的原理验证页面，用于测试 `Brainstorming` 能力本身。

它不替代当前专家工作台，不承担正式需求规格编写任务，也不进入专家主路径。

建议入口：

```text
/p2-brainstorm-lab
```

### 5.2 页面结构

页面采用左右分区。

左侧为交互输入区：

- 课题输入
- 模型供应商选择
- 模型名称选择
- 知识包选择
- 对话流
- 轻量选项
- CLI 式输入框

右侧为过程浮现区：

- 当前已确认事实
- 待确认问题
- 规格草稿片段
- 本轮 `document_patch`
- 注记、假设、风险
- 来源知识引用
- 原始结构化返回调试区

### 5.3 页面边界

Lab 页面首版不做以下事项：

- 不改造当前正式专家工作台
- 不写入正式需求规格文档
- 不触发冻结版本
- 不接入 `P3`
- 不实现完整模板配置台
- 不要求真实 `P1` 服务可用

Lab 页面可以使用假知识包、假模板和假领域课题，但模型调用链路与结构化返回协议应尽量真实。

## 6. Brainstorming 会话对象

建议定义 `BrainstormSession` 作为后台会话对象。

核心字段包括：

- `session_id`
- `topic`
- `provider`
- `model`
- `template_id`
- `knowledge_package_id`
- `messages`
- `confirmed_facts`
- `open_questions`
- `draft_fragments`
- `annotations`
- `risks`
- `last_document_patch`
- `raw_model_response`
- `created_at`
- `updated_at`

会话对象的重点是保存分析过程，而不是保存正式文档。

### 6.1 生命周期

`BrainstormSession` 应是可恢复的长生命周期对象，而不是一次请求结束即销毁的临时对象。

建议状态如下：

```text
created
  已创建，只有课题或初始配置

running
  正在多轮问答

waiting_user
  系统已提出问题，等待用户回答

patch_ready
  已产生文档修补建议

completed
  当前分析段落结束，可进入正式草稿转换

archived
  会话归档，只读查看
```

首版 Lab 可以简化状态实现，但文档层应保留完整生命周期概念。

### 6.2 状态保存原则

会话至少要保存：

- 用户和助手的历史消息
- 当前课题
- 模型供应商和模型名称
- 模板选择
- 知识包选择
- 已确认事实
- 待确认问题
- 草稿片段
- 注记、假设和风险
- 最近一次结构化输出

这样用户即使中断页面或第二天继续，也能恢复到同一个分析上下文。

### 6.3 触发机制

首版 Lab 只需要支持“用户输入触发一轮循环”。

后续可扩展触发包括：

- 用户输入自然语言。
- 用户输入 `A/B/C` 等轻量选项。
- 用户点击轻量选项按钮。
- 用户输入 `继续`、`下一步`、`你来判断` 等推进指令。
- 用户切换课题、模板或知识包。
- 正式工作台中正文草稿发生变化后，触发缺口分析。

无论触发来源是什么，后台都应统一转化为一次 `BrainstormTurn`。

## 7. 单轮交互协议

每一轮用户输入应形成 `BrainstormTurn`。

### 7.1 输入

```json
{
  "session_id": "bs-001",
  "user_input": "我选A，这个系统主要给专家用",
  "context": {
    "topic": "空域运算软件需求规格",
    "template_id": "81433号",
    "knowledge_package_id": "airspace-domain-demo"
  }
}
```

### 7.2 输出

```json
{
  "assistant_message": "已确认主要用户是专业领域专家。我会先把用户角色收敛到需求规格的使用者章节。",
  "next_question": "这个软件更偏向计算分析工具，还是偏向协同规划平台？",
  "quick_options": [
    {
      "key": "A",
      "label": "计算分析工具"
    },
    {
      "key": "B",
      "label": "协同规划平台"
    },
    {
      "key": "C",
      "label": "二者都有"
    }
  ],
  "confirmed_facts_delta": [
    "系统主要用户为专业领域专家。"
  ],
  "open_questions_delta": [
    "需确认系统定位是计算分析工具还是协同规划平台。"
  ],
  "document_patch": [
    {
      "section": "1.2 用户角色",
      "operation": "append_or_update",
      "content": "本系统主要面向专业领域专家，支持其开展需求分析、判断和规格确认工作。"
    }
  ],
  "annotations": [
    "用户角色已确认，但具体使用职责尚需补充。"
  ],
  "risks": [],
  "confidence": "medium"
}
```

### 7.3 关键要求

- 输出必须结构化，不能只返回自然语言。
- `assistant_message` 用于左侧对话区。
- `quick_options` 必须轻量，可为空。
- `document_patch` 是修补意图，不等同于正式写入。
- `annotations` 是系统解读层，不进入标准正文。
- `confidence` 用于判断是否需要用户确认。

### 7.4 单轮内部处理步骤

`Brainstorming Service` 每处理一轮输入，应执行以下步骤：

```text
1. 接收用户输入
2. 读取 BrainstormSession
3. 读取历史 messages
4. 读取 confirmed_facts
5. 读取 open_questions
6. 读取模板和知识包
7. 构造模型请求
8. 调用 DeepSeek / OpenAI / Mock Provider
9. 要求模型返回结构化 JSON
10. 校验 JSON
11. 必要时执行一次修复或降级
12. 更新 BrainstormSession
13. 返回 BrainstormTurn 给前端
```

这里的关键是第 7 步和第 10 步。

第 7 步决定模型是否能理解当前业务目标、模板约束和上下文。第 10 步决定模型输出能否被系统稳定消费。

### 7.5 最小 API 形态

原理验证阶段可以先设计最小 API：

```text
POST /brainstorm/sessions
创建 Brainstorming 会话

GET /brainstorm/sessions/{session_id}
读取并恢复会话

POST /brainstorm/sessions/{session_id}/turns
提交一轮用户输入，返回结构化 BrainstormTurn
```

首版不需要直接提供正式文档写入接口。

`document_patch` 在 Lab 中只作为修补建议展示。正式并入专家工作台后，再由 `Requirement Authoring Service` 决定如何转换为正式草稿变更。

### 7.6 前端展示职责

前端不负责决定模型怎么分析，也不负责直接拼装模型上下文。

前端只负责展示和收集：

- 当前课题
- 模型和知识包选择
- 用户输入
- 助手回复
- 轻量选项
- 已确认事实
- 待确认问题
- 草稿片段
- `document_patch`
- 注记、假设和风险
- 错误状态

这能避免把 Brainstorming 逻辑重新散落到页面组件中。

## 8. 模型调用策略

### 8.1 Provider 抽象

`Brainstorming Service` 不直接绑定某个大模型厂商。

首版至少抽象：

- `OpenAIProvider`
- `DeepSeekProvider`
- `MockProvider`

Provider 统一提供：

- 普通调用
- 流式调用
- 结构化输出
- 调用日志
- 错误归一化

### 8.2 DeepSeek 与 OpenAI 的差异处理

DeepSeek 可按 OpenAI-compatible API 方式接入，但多轮状态需要 `P2` 自己维护。

OpenAI 可使用支持状态化、流式和工具调用的接口形态。即使 OpenAI 侧支持状态引用，`P2` 仍应保存自己的 `BrainstormSession`，避免业务状态被模型供应商绑定。

### 8.3 不展示底层思维链

无论模型是否提供 thinking 或 reasoning 字段，`P2` 产品界面不应直接展示模型底层思维链。

应展示经过结构化整理的分析结果：

- 已确认事实
- 判断依据摘要
- 待确认问题
- 风险与假设
- 来源引用

## 9. 知识注入策略

Lab 首版使用假知识包验证接口形态。

知识包至少包含：

- 领域术语
- 业务对象
- 典型行为
- 约束规则
- 来源片段

正式并入时，知识来源应通过 `P1 Knowledge Adapter` 获取，可以接入：

- `XX-P1-Sim`
- 未来真实 `P1` 发布态知识服务

`Brainstorming Service` 只知道“当前会话绑定了哪个知识包”，不应直接关心知识是真实 `P1` 还是模拟器生成。

## 10. 与 P2 统一架构的关系

完成 Lab 验证后，再把结论回写到 `P2` 正式架构：

1. 明确 `Brainstorming Service` 的后台服务边界。
2. 明确 `BrainstormTurn` 与正式草稿保存之间的转换协议。
3. 明确 `document_patch` 如何进入 `Requirement Authoring Service`。
4. 明确用户确认、自动应用和待确认映射三类状态。
5. 明确 `Brainstorming` 与表单模式的同源关系。
6. 明确模型调用日志、成本、错误重试和审计要求。

只有完成上述回写后，才把 `Brainstorming Service` 接入正式专家工作台。

## 11. 原理验证验收口径

独立验证阶段至少通过以下验收：

- 可以创建一个 Brainstorming 会话。
- 可以输入课题并启动引导。
- 可以选择模型供应商和模型。
- 可以使用假知识包作为上下文。
- 模型返回结构化 `BrainstormTurn`。
- 页面能显示助手回复、轻量选项、已确认事实、待确认问题、草稿片段、注记和风险。
- 用户可以用 `A/B/C`、短句或自然语言继续推进。
- 连续多轮后，会话状态可以恢复。
- `document_patch` 只显示为修补建议，不写入正式需求规格文档。
- 模型调用失败时，页面能显示可理解的错误状态。

## 12. 实施分期建议

### 12.1 第一期：Mock Provider

目标是验证页面和协议。

- 后端提供假模型返回。
- 前端显示完整 Lab 页面。
- 验证 `BrainstormTurn` 数据结构。
- 不接真实大模型。

### 12.2 第二期：真实模型 Provider

目标是验证真实模型调用。

- 接入 DeepSeek 或 OpenAI 之一。
- 支持 API Key 配置。
- 支持结构化输出解析。
- 支持调用失败与超时处理。

### 12.3 第三期：知识注入

目标是验证 `P1` 上游知识使用方式。

- 先接假知识包。
- 再接 `XX-P1-Sim`。
- 验证知识引用是否能影响追问和草稿片段。

### 12.4 第四期：并入正式 P2 架构

目标是把验证成功的能力接入正式专家工作台。

- 定义 `document_patch` 到正式草稿的转换规则。
- 定义自动应用和待确认映射策略。
- 把问答模式从前端业务逻辑升级为 `Brainstorming Service` 消费端。

## 13. 当前决策

本阶段确认：

- `Brainstorming` 是 `P2` 的核心后台能力。
- 先建立独立 `P2 Brainstorming Lab`，不直接改造当前专家工作台。
- Lab 使用假知识包和独立会话对象验证原理。
- Lab 的结构化协议稳定后，再统一规划并改造 `P2` 后台架构。
- 正式工作台未来消费 `Brainstorming Service`，但文档保存、检查、冻结仍归 `Requirement Authoring Service` 管理。
