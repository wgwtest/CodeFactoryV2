# P2 XG-Orchestrator 组织器包规范设计

**日期：** 2026-05-02

**基础包壳规范：** `DOC/CODEX_DOC/02_设计说明/00_总纲/04-Orchestrator基础包壳与注册机制设计.md`

## 1. 设计结论

`XG-Orchestrator` 是面向需求规格说明的组织器，不是通用文档组织器。

当前组织器体系采用两层设计：

- `Orchestrator Package Shell`：通用包壳，规定一个组织器包如何声明、注册和被 Host 装载。
- `XG-Orchestrator Contract`：P2 需求规格说明专用运行契约，规定输入、输出、Turn 生命周期和审计字段。

其中，`Orchestrator Package Shell` 已上移为总纲级基础规范，本文不再承担基础父类设计职责。本文只定义 `XG-Orchestrator Contract` 这一层。

因此，当前不把 `XG-Orchestrator` 抽象成“任意文档转换父类”。后续 P3 从需求规格到软件设计说明，应定义自己的设计阶段组织器契约，但可以复用总纲中定义的基础包壳结构。

## 2. 包壳结构

XG 组织器包复用基础包壳规范，并以 `xg` 契约族目录存在：

```text
orchestrators/xg/<orchestrator-id>/
  manifest.json
  ORCHESTRATOR.md
  contract.schema.json
  policy.md
  prompt.md
  artifact_rules.json
  spec_strategy.json
  examples/
  tests/
  runner.py
```

其中，基础文件职责由总纲级 `Orchestrator Package Shell` 规定；XG 专用解释如下：

- `manifest.json` 是机器可读身份、版本、契约、运行模式和能力声明。
- `ORCHESTRATOR.md` 是面向人审查的 XG 组织器说明。
- `contract.schema.json` 是 `xg-orchestrator-contract@1` 的契约声明。
- `policy.md` 是面向需求规格说明的组织规则。
- `prompt.md` 是 XG 模型提示策略，`local_runner` 模式下可作为说明文件。
- `artifact_rules.json` 是面向规格节点的事实模板、正文 patch 模板和轻量选项规则。
- `spec_strategy.json` 是面向规格完成度树的节点问题、章节问题模板和默认叶子问题策略。
- `examples/` 和 `tests/` 用于 XG 包级样例与契约验证。
- `runner.py` 只在 `local_runner` 模式下强制存在，并由 P2 Host 受控调用。

## 3. 首版运行模式

首版支持两种模式：

- `policy_interpreted`：Host 读取组织器策略，结合 Provider 生成候选输出。
- `local_runner`：Host 调用受控本地规则路径生成候选输出。

远程组织器服务暂不实现，但保留未来 `remote_service` 扩展位。

## 4. 首版实例

首版必须提供两个实例：

```text
xg-heuristic-orchestrator
xg-strong-rule-orchestrator
```

`xg-heuristic-orchestrator`：

- `mode = policy_interpreted`
- 偏启发式、开放输入、轻量选项、用户输入驱动。
- 可以调用 `mock / deepseek / openai` Provider。
- 规格节点的事实模板、patch 模板与快捷选项由包内 `artifact_rules.json` 提供。
- 完成度树节点问题由包内 `spec_strategy.json` 提供。

`xg-strong-rule-orchestrator`：

- `mode = local_runner`
- 偏规则优先、强审计链、强闭环。
- 模型只作为未来候选文本来源，首版由 Host 受控规则路径执行。
- 本地 runner 仍遵守同一 `artifact_rules.json`，不在 Host 服务层重复写一套章节模板。
- 强规则节点问题由包内 `spec_strategy.json` 提供，Host 只负责按模板生成树结构并挂载问题文本。

两者都必须遵守 `xg-orchestrator-contract@1`，并输出同一套 Turn 协议。

## 5. Host 边界

P2/XG Host 在基础 Host 责任之外，额外负责：

- 发现 `orchestrators/xg/*/manifest.json`
- 提供模板、知识绑定、草稿状态和历史过程产物
- 校验组织器输出是否满足 `xg-orchestrator-contract@1`
- 将候选输出落入 P2 会话、过程产物、草稿建议和审计视图
- 保证正式需求规格文档仍由 P2 Host 控制写入

XG 组织器负责：

- 理解用户输入
- 判断与上一轮交互对象的关系
- 组织需求规格补充
- 生成正文 patch 建议
- 判断本轮闭环
- 设计下一轮交互对象

XG 组织器不允许：

- 直接写正式需求规格文档
- 直接冻结版本
- 直接修改模板或知识库
- 直接触发 P3
- 绕过 Host 保存状态

## 6. 当前落地状态

当前后端已落地 `OrchestratorPackageLoader`、`OrchestratorContractValidator` 与 `OrchestratorRunnerHost`，从 `orchestrators/xg/` 读取包信息，并通过 `/api/requirement-analysis/orchestrators` 暴露注册结果。

需要注意：当前基础注册与执行运行时位于 `apps/api/app/orchestrators/`，属于 P2/XG 首版实现；跨阶段基础注册层的长期目标形态见总纲级 `Orchestrator基础包壳与注册机制设计`。

当前 `XG 需求分析组织器 Lab` 仍使用既有 Turn 输出协议：

```text
previous_interaction
input_relation
spec_execution
post_update_review
closure_decision
next_interaction
decision_trace
```

其中 `xg-heuristic-orchestrator` 继承现有 XG 需求分析组织器 Lab 能力；`xg-strong-rule-orchestrator` 通过本地规则路径产出符合相同协议的 Turn。

当前首版的进一步压实约束是：

- `policy_interpreted` 组织器必须提供 `artifact_rules.json`，供 mock 路径和服务端 fallback 使用。
- `local_runner` 组织器也必须提供 `artifact_rules.json`，由 runner 自己读取；Host 不再额外硬编码章节事实与 patch 文案。
- 所有 XG 组织器都必须提供 `spec_strategy.json`，Host 不再维护后端条款问题库。
- 所有 XG 组织器执行结果必须进入 Provider 调用审计链。审计链至少保留 `provider_request`、`provider_response`、`provider_normalized_output` 和 Turn 引擎生成的 `service_output`，用于判断问题来自组织器提示词、模型输出、Provider 适配还是服务端后处理。
