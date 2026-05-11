# P2 Brainstorming Lab 完成度树实现自检记录

记录时间：2026-05-01 20:01

## 1. 修复背景

实测发现右侧“需求规格问题树”仍然缺少明确目标：它会把模型追问、事实、正文建议混成一棵过程产物树，无法回答“需求规格说明到底补齐到什么程度”。

本轮将主视图改为 `需求规格完成度树`，并把 `提问路径` 单独作为过程视图。

## 2. 实现内容

后端 `BrainstormSession` 新增：

- `spec_tree`
- `active_spec_node_id`
- `turn_path`

组织器推进规则：

1. 会话创建时生成标准需求规格完成度树。
2. 每轮优先推进当前第一个 `open` 叶子节点。
3. 用户回答后关闭当前目标叶子，写入 `answer_summary` 和 `completion_reason`。
4. 将本轮推进记录写入 `turn_path`。
5. `questions / facts / patches` 继续保留为内部材料，但不再作为会话摘要主树。

前端 `会话摘要 / 过程产物` 改为：

- 主视图：`需求规格完成度树`
- 辅助视图：`提问路径`

## 3. 机测命令

```bash
uv run pytest apps/api/tests/test_brainstorm_api.py -q
corepack pnpm --dir apps/web test src/test/BrainstormLabPage.test.tsx
corepack pnpm --dir apps/web build
```

## 4. 机测结果

- API：`3 passed`
- 前端 Lab 测试：`1 passed`
- 前端构建：通过；存在既有 Vite chunk size 警告。

## 5. 验证要点

- 会话创建后返回 `active_spec_node_id=SPEC-1.1`。
- 会话创建后返回五个顶层规格目标：系统概述、用户与使用场景、功能需求、非功能需求、验收与约束。
- 第一轮回答关闭 `SPEC-1.1`，并推进到 `SPEC-1.2`。
- 第二轮回答关闭 `SPEC-1.2`，并推进到 `SPEC-1.3`。
- 前端显示 `需求规格完成度树`，不再把 `F/P` 作为主树节点。
- 前端显示 `提问路径`，用于解释 turn 如何推进目标树。
