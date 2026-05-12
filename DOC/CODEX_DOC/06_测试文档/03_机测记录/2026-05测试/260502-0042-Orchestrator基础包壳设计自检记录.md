# Orchestrator 基础包壳设计自检记录

**时间：** 2026-05-02 00:42

**范围：**

- `DOC/CODEX_DOC/02_设计说明/00_总纲/04-Orchestrator基础包壳与注册机制设计.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-需求分析系统设计-260502-0022-XG-Orchestrator组织器包规范设计.md`
- `DOC/CODEX_DOC/02_设计说明/README.md`
- `DOC/CODEX_DOC/README.md`

## 1. 本轮目标

补齐 `XG-Orchestrator` 之上的基础组织器设计，明确：

- 基础层是 `Orchestrator Package Shell`。
- XG 层是需求规格说明专用契约，不是通用父类。
- 后续 P3 可以复用基础包壳，但必须定义自己的阶段契约。
- 当前代码中的 `app.brainstorm.orchestrators` 只是 P2/XG 首版实现，还不是跨阶段基础注册层。

## 2. 自检项

| 检查项 | 结果 |
| --- | --- |
| 是否新增总纲级基础设计文档 | 通过 |
| 是否避免把 XG 写成通用文档组织器父类 | 通过 |
| 是否在 XG 文档中引用基础包壳规范 | 通过 |
| 是否说明当前代码实现与目标架构差距 | 通过 |
| 是否同步 `02_设计说明/README.md` 阅读顺序 | 通过 |
| 是否同步 `DOC/CODEX_DOC/README.md` 阅读顺序 | 通过 |
| 是否执行 `git diff --check` | 通过 |

## 3. 验证命令

```bash
rg -n "任意文档转换父类|基础包壳通用|运行契约专用|app\\.brainstorm|orchestrators/xg|xg-orchestrator-contract@1" DOC/CODEX_DOC/02_设计说明 DOC/CODEX_DOC/README.md
git diff --check
```

## 4. 结论

本轮为文档与架构设计落版，不涉及运行代码修改。

当前已经可以明确回答：

- 基础组织器设计位于总纲文档 `04-Orchestrator基础包壳与注册机制设计.md`。
- `P2-需求分析系统设计-260502-0022-XG-Orchestrator组织器包规范设计.md` 只负责 XG 专用契约。
- 代码层基础注册器的中性化迁移仍是后续任务，不在本轮完成。
