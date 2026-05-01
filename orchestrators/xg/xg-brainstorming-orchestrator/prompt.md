# Prompt

该组织器通过 Host 注入的上下文和策略提示，驱动模型生成本轮候选输出。

Host 必须保证：

- 输入为 `xg-orchestrator-contract@1`
- 输出经过 Host 校验
- 不允许模型直接控制正式文档和冻结状态
