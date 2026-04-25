# `docs/superpowers/issues` 文件头统一自测

## 1. 自测目标

验证当前 `docs/superpowers/issues/` 下的历史快照类文件与执行工单类文件，是否都已经补充统一的防误读文件头。

## 2. 本轮变更

本轮已更新文件：

- `docs/superpowers/issues/2026-04-15-p4-tool-hub-issue-tree-mirror.md`
- `docs/superpowers/issues/2026-04-17-p3-software-design-system-issue-tree-mirror.md`
- `docs/superpowers/issues/2026-04-17-p6-platform-entry-issue-tree-mirror.md`
- `docs/superpowers/issues/P4.1.6-tool-hub-unified-data-snapshot-execution.md`
- `docs/superpowers/issues/P4.2.1-tool-demand-sheet-lifecycle-execution.md`
- `docs/superpowers/issues/P4.2.6-simulated-manufacture-executor-execution.md`

## 3. 自测项

1. `issue tree mirror` 类文件是否都已声明“历史快照，不是当前 WBS 树事实源”。
2. `execution` 类文件是否都已声明“执行工单镜像，不替代正式设计 / 正式计划 / 远端 issue 正文”。
3. 上述文件是否都已写明：
   - 当前 WBS 事实源是 GitHub `Issues + sub-issues`
   - 远端不可访问时回退到仓库主工作树中的 `DOC/CODEX_DOC/`

## 4. 自测结果

检查结果：

- 三个 `issue tree mirror` 文件已统一补充历史快照文件头。
- 三个 `execution` 文件已统一补充执行工单镜像文件头。
- 六个文件均已补充 GitHub 与 `DOC/CODEX_DOC/` 的优先级说明。

## 5. 结论

本轮自测通过。

当前状态：

- 文件头统一：已完成
- 人工验收状态：待用户确认
