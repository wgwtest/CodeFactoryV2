# P2 XG-Orchestrator 组织器包规范设计

**日期：** 2026-05-02

## 1. 设计结论

`XG-Orchestrator` 是面向需求规格说明的组织器，不是通用文档组织器。

本轮采用两层设计：

- `Orchestrator Package Shell`：通用包壳，规定一个组织器包如何声明、注册和被 Host 装载。
- `XG-Orchestrator Contract`：P2 需求规格说明专用运行契约，规定输入、输出、Turn 生命周期和审计字段。

因此，当前不把组织器抽象成“任意文档转换父类”。后续 P3 从需求规格到软件设计说明，应定义自己的设计阶段组织器契约，但可以复用包壳结构。

## 2. 包壳结构

组织器包以 skill-like 目录形态存在：

```text
orchestrators/xg/<orchestrator-id>/
  manifest.json
  ORCHESTRATOR.md
  contract.schema.json
  policy.md
  prompt.md
  examples/
  tests/
  runner.py
```

其中：

- `manifest.json` 是机器可读身份、版本、契约、运行模式和能力声明。
- `ORCHESTRATOR.md` 是面向人审查的组织器说明。
- `contract.schema.json` 是契约声明。
- `policy.md` 是组织规则。
- `prompt.md` 是模型提示策略，`local_runner` 模式下可作为说明文件。
- `examples/` 和 `tests/` 用于包级样例与契约验证。
- `runner.py` 只在 `local_runner` 模式下强制存在。

## 3. 首版运行模式

首版支持两种模式：

- `policy_interpreted`：Host 读取组织器策略，结合 Provider 生成候选输出。
- `local_runner`：Host 调用受控本地规则路径生成候选输出。

远程组织器服务暂不实现，但保留未来 `remote_service` 扩展位。

## 4. 首版实例

首版必须提供两个实例：

```text
xg-brainstorming-orchestrator
xg-strong-rule-orchestrator
```

`xg-brainstorming-orchestrator`：

- `mode = policy_interpreted`
- 偏启发式、开放输入、轻量选项、用户输入驱动。
- 可以调用 `mock / deepseek / openai` Provider。

`xg-strong-rule-orchestrator`：

- `mode = local_runner`
- 偏规则优先、强审计链、强闭环。
- 模型只作为未来候选文本来源，首版由 Host 受控规则路径执行。

两者都必须遵守 `xg-orchestrator-contract@1`，并输出同一套 Turn 协议。

## 5. Host 边界

P2 Host 负责：

- 发现 `orchestrators/xg/*/manifest.json`
- 校验包结构
- 注册组织器
- 提供模板、知识绑定、草稿状态和历史过程产物
- 调用组织器
- 校验输出
- 落库、展示、审计

组织器负责：

- 理解用户输入
- 判断与上一轮交互对象的关系
- 组织需求规格补充
- 生成正文 patch 建议
- 判断本轮闭环
- 设计下一轮交互对象

组织器不允许：

- 直接写正式需求规格文档
- 直接冻结版本
- 直接修改模板或知识库
- 直接触发 P3
- 绕过 Host 保存状态

## 6. 当前落地状态

当前后端新增 `OrchestratorRegistry`，从 `orchestrators/xg/` 读取包信息，并通过 `/api/brainstorm/orchestrators` 暴露注册结果。

当前 `Brainstorming Lab` 仍使用既有 Turn 输出协议：

```text
previous_interaction
input_relation
spec_execution
post_update_review
closure_decision
next_interaction
decision_trace
```

其中 `xg-brainstorming-orchestrator` 继承现有 Brainstorming Lab 能力；`xg-strong-rule-orchestrator` 通过本地规则路径产出符合相同协议的 Turn。
