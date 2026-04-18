# superpowers 工作文档层说明

`docs/superpowers/` 是 `CodeFactoryV2` 的工作文档层，不是正式文档单一权威根。

## 1. 目录职责

- `specs/`：设计草案、局部方案、阶段设计
- `plans/`：实施计划、任务拆分
- `issues/`：issue tree mirror、执行工单镜像

## 2. 与正式文档的关系

正式文档根是：

- `DOC/CODEX_DOC/`

协同规则：

- 可以先在 `docs/superpowers/` 起草文档
- 一旦方案被采纳为正式基线，必须同步回 `DOC/CODEX_DOC/`
- 如果两边表达冲突，以 `DOC/CODEX_DOC/` 为准

## 3. 典型工作流

1. 在 `docs/superpowers/specs/` 起草设计
2. 在 `docs/superpowers/plans/` 拆实施计划
3. 在 `docs/superpowers/issues/` 维护 issue mirror
4. 用户确认后，把正式结论回写到 `DOC/CODEX_DOC/`

## 4. 当前执行口径

后续 `CodeFactoryV2` 的方案开发采用：

- `superpowers` 负责快速推演与工作拆分
- `DOC/CODEX_DOC` 负责正式落版与长期追踪
